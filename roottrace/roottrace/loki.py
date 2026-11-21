"""Thin Loki HTTP API client with pagination."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from .config import LokiConfig

log = logging.getLogger(__name__)


@dataclass
class LogEntry:
    ts_ns: int          # Loki timestamp, nanoseconds since epoch
    labels: dict        # stream labels: namespace, app, pod, container, ...
    line: str           # the raw log line, not yet parsed or masked


class LokiClient:
    def __init__(self, cfg: LokiConfig):
        self.cfg = cfg
        self.s = requests.Session()             # reuse TCP to the port-forward
        if cfg.username:
            self.s.auth = (cfg.username, cfg.password or "")
        if cfg.bearer_token:
            self.s.headers["Authorization"] = f"Bearer {cfg.bearer_token}"
        if cfg.org_id:
            self.s.headers["X-Scope-OrgID"] = cfg.org_id    # required by multi-tenant Loki
        self.s.verify = cfg.verify_tls
        self.truncated = False              # set by query_range when the cap stops the window early

    def _get(self, path: str, params: dict) -> dict:
        """GET a Loki API path and return the `data` object.

        Connection errors, 429, and 5xx are retried with a short backoff. A 4xx is the query,
        and retrying it will not help.
        """
        attempts = max(1, int(self.cfg.retries))
        delay = 0.4
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                r = self.s.get(self.cfg.url.rstrip("/") + path, params=params, timeout=self.cfg.timeout_s)
            except requests.RequestException as e:
                last = e
            else:
                if r.status_code == 429 or r.status_code >= 500:
                    last = RuntimeError(f"Loki {path} -> HTTP {r.status_code}: {r.text[:300]}")
                elif r.status_code >= 400:
                    raise RuntimeError(f"Loki {path} -> HTTP {r.status_code}: {r.text[:500]}")
                else:
                    body = r.json()
                    if body.get("status") != "success":
                        raise RuntimeError(f"Loki {path} error: {body}")
                    return body["data"]
            if attempt + 1 < attempts:
                log.warning("Loki %s failed (%s), retry %d/%d", path, last, attempt + 1, attempts - 1)
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"Loki {path} failed after {attempts} attempts: {last}")

    def label_values(self, label: str, start_ns: int, end_ns: int) -> list[str]:
        r = self.s.get(self.cfg.url.rstrip("/") + f"/loki/api/v1/label/{label}/values",
                       params={"start": start_ns, "end": end_ns}, timeout=self.cfg.timeout_s)
        r.raise_for_status()
        return r.json().get("data", []) or []

    def query_range(self, query: str, start_ns: int, end_ns: int, max_lines: int | None = None) -> list[LogEntry]:
        """Fetch log lines oldest-first, paginating forward until the window ends or the cap is hit.

        Loki returns at most `limit` lines per call and does not give a cursor. The next page starts
        one nanosecond after the newest line we already have, so a line is not fetched twice.
        """
        cap = max_lines or self.cfg.max_lines
        out: list[LogEntry] = []
        cursor = start_ns
        self.truncated = False
        while cursor < end_ns and len(out) < cap:
            data = self._get("/loki/api/v1/query_range", {
                "query": query, "start": cursor, "end": end_ns,
                "limit": min(self.cfg.page_size, cap - len(out)), "direction": "forward",
            })
            batch: list[LogEntry] = []
            for stream in data.get("result", []):
                labels = stream.get("stream", {})              # one label set per stream
                for ts, line in stream.get("values", []):
                    batch.append(LogEntry(int(ts), labels, line))
            if not batch:
                break                                           # nothing left in the window
            batch.sort(key=lambda e: e.ts_ns)                   # streams are not interleaved by time
            out.extend(batch)
            if len(batch) < self.cfg.page_size:
                break                                           # short page means Loki is exhausted
            cursor = batch[-1].ts_ns + 1                        # step past the last line
        if len(out) >= cap:
            self.truncated = True
            log.warning("Hit max_lines cap (%d) — this slice is partial", cap)
        return out

    def instant_vector(self, query: str, at_ns: int) -> list[tuple[dict, float]]:
        """One instant metric query. Used for the 'was logging yesterday, silent now' check."""
        data = self._get("/loki/api/v1/query", {"query": query, "time": at_ns})
        return [(r.get("metric", {}), float(r["value"][1])) for r in data.get("result", [])]

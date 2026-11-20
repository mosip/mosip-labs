"""Scan + trace orchestration (used by the CLI, the HTTP server and the CronJob)."""
from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

from . import k8s as k8smod
from . import report
from .buildinfo import load_sources, repo_for
from .catalog import Catalog
from .deps import DepMap, analyze
from .config import Config
from .loki import LokiClient
from .miner import Miner, keep
from .parser import parse
from .source import attach_snippets
from .traces import SavedTraces, save as save_traces

log = logging.getLogger(__name__)
# Duration suffixes accepted by --since, --baseline and baseline_offset. Values are seconds.
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def dur_ns(s: str) -> int:
    """'30m' / '2h' / '1d' / '1w' -> nanoseconds. Anything else raises; there is no silent default unit."""
    m = re.fullmatch(r"(\d+)([smhdw])", s.strip())
    if not m:
        raise ValueError(f"bad duration '{s}' (use e.g. 30m, 2h, 1d)")
    return int(m.group(1)) * _UNITS[m.group(2)] * 1_000_000_000


def ts_ns(s: str) -> int:
    """ISO-8601 (2026-11-19T10:00:00Z) or epoch seconds/ms/ns.

    A bare integer is disambiguated by magnitude: 10 digits is seconds, 13 is milliseconds, else nanoseconds.
    """
    if s.isdigit():
        n = int(s)
        return n * 10**9 if n < 10**11 else n * 10**6 if n < 10**14 else n
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp() * 1e9)


def window(since: str | None, frm: str | None, to: str | None) -> tuple[int, int]:
    """Resolve --since / --from / --to into [start, end) nanoseconds. End defaults to now, start to end-1h."""
    end = ts_ns(to) if to else time.time_ns()
    start = ts_ns(frm) if frm else end - dur_ns(since or "1h")
    if start >= end:
        raise ValueError("window start must be before end")
    return start, end


def _lq(name: str) -> str:
    """Escape a literal for a regex inside a LogQL double-quoted string.

    LogQL then interprets the result as a regex, and the whole selector is itself a quoted string,
    so each backslash the regex needs is written twice.
    """
    return re.sub(r"([.\\+*?\[\](){}|^$])", r"\\\\\1", name)


def selector(cfg: Config, namespaces: list[str] | None) -> str:
    """LogQL stream selector. An explicit namespace list wins; otherwise every namespace except the platform ones."""
    ns = namespaces or cfg.namespaces
    if ns:
        return '{namespace=~"%s"}' % "|".join(_lq(n) for n in ns)
    return '{namespace=~".+", namespace!~"%s"}' % "|".join(_lq(n) for n in cfg.exclude_namespaces)


def line_filter(cfg: Config) -> str:
    """LogQL line filter. A scan includes WARN lines and Java stack frames.

    The configured error_filter is usually already `(?i)(...)`. WARN and `.java:N` are folded into that
    group so Loki applies one regex. A hand-edited filter that is not in that shape gets wrapped instead.
    """
    f = cfg.error_filter
    extras = []
    if cfg.include_warn and not re.search(r"warn", f, re.I):
        extras.append("warn")
    if not re.search(r"java:", f):
        extras.append(r"\.java:\d")                 # stack frames have no 'error' word of their own
    if not extras:
        return f
    addition = "|".join(extras)
    grouped = re.fullmatch(r"\(\?i\)\((.*)\)", f)
    if grouped:
        return f"(?i)({grouped.group(1)}|{addition})"
    return f"(?i)(?:(?:{f})|{addition})"


# A single query_range across a full day times out. Six hours is the slice that finished on 131ga.
_SLICE_NS = 6 * 3600 * 1_000_000_000
# Below this, a failed slice is reported instead of being split again.
_MIN_NS = 30 * 60 * 1_000_000_000


def _slices(start: int, end: int) -> list[tuple[int, int]]:
    """One range when the window is at most six hours, otherwise six-hour slices in order."""
    if end - start <= _SLICE_NS:
        return [(start, end)]
    out = []
    cursor = start
    while cursor < end:
        nxt = min(end, cursor + _SLICE_NS)
        out.append((cursor, nxt))
        cursor = nxt
    return out


def _pull(loki: LokiClient, query: str, start: int, end: int, cfg: Config, which: str) -> tuple[list, list]:
    """Events in [start, end), plus slices that stopped early or never answered.

    A slice that times out is split in half down to 30 minutes. A slice that hits max_lines is kept
    and marked partial, so the rest of the window still runs.
    """
    pending = _slices(start, end)
    events = []
    partial = []
    i = 0
    while i < len(pending):
        a, b = pending[i]
        i += 1
        try:
            rows = loki.query_range(query, a, b)
        except Exception as e:
            if b - a > _MIN_NS:
                mid = a + (b - a) // 2
                pending[i:i] = [(a, mid), (mid, b)]
                log.warning("Loki %s slice failed (%s); splitting it", which, e)
                continue
            partial.append({"which": which, "from_ns": a, "to_ns": b, "reason": "Loki did not answer"})
            log.warning("Loki %s slice skipped: %s", which, e)
            continue
        events.extend(e for e in parse(rows, cfg.service_label) if keep(e, cfg.include_warn))
        if loki.truncated:
            partial.append({"which": which, "from_ns": a, "to_ns": b, "reason": "stopped at max_lines"})
    return events, partial


def scan(cfg: Config, start: int, end: int, namespaces: list[str] | None = None, *,
         save_dir: str | None = None, loaded: SavedTraces | None = None) -> dict:
    """One health scan. Returns the dict the HTML report, the JSON file and the CLI all print from.

    Steps: pull errors for this window and for the same window one baseline ago, cluster both,
    match the known-issue catalog, find services that went silent, read Kubernetes, then name root causes.

    ``save_dir`` writes the pulled lines under ``<save_dir>/traces`` so a later run can pass them
    back as ``loaded`` and skip Loki.
    """
    off = dur_ns(loaded.baseline_offset if loaded else cfg.baseline_offset)
    span = end - start
    saved_to = None
    if loaded is not None:
        cur, base = list(loaded.current), list(loaded.baseline)
        if namespaces:
            want = set(namespaces)
            cur = [e for e in cur if e.namespace in want]
            base = [e for e in base if e.namespace in want]
        gaps, q = list(loaded.coverage), loaded.query
        loki = None
        log.info("events from disk: current=%d baseline=%d (%s)", len(cur), len(base), loaded.directory)
    else:
        loki = LokiClient(cfg.loki)
        sel = selector(cfg, namespaces)
        q = f'{sel} |~ `{line_filter(cfg)}`'            # |~ is a regex line filter, not a label matcher
        log.info("Loki query: %s", q)
        # keep() drops INFO lines that only matched because a stack frame contains '.java:'.
        cur, gaps = _pull(loki, q, start, end, cfg, "current")
        base, base_gaps = _pull(loki, q, start - off, end - off, cfg, "baseline")
        gaps.extend(base_gaps)
        log.info("events: current=%d baseline=%d partial_slices=%d", len(cur), len(base), len(gaps))
        if save_dir:
            saved_to = str(save_traces(save_dir, start, end, cfg.baseline_offset, q, gaps, cur, base))
            log.info("saved traces to %s", saved_to)

    miner = Miner()
    miner.add_baseline(base)                       # teaches Drain the old templates and records baseline counts
    miner.add_current(cur)
    cat = Catalog(cfg.catalog_paths, cfg.ignore_issue_ids)
    issues = miner.finalize(cfg.spike_factor)      # sets templates first, so the catalog can match them
    cat.apply(issues)
    issues = miner.finalize(cfg.spike_factor)      # rescore with catalog severity now attached
    _decorate(issues, cur)                         # repo of the throw site, and the services on each trace id

    # Services that logged anything in the baseline but nothing now. A count query, not another log pull.
    # A run that reads saved lines skips it: those counts need every log line, not just the saved errors.
    silent = []
    logged_namespaces = None
    if loki is not None:
        try:
            lbl = cfg.service_label
            rng = f"{max(span // 1_000_000_000, 60)}s"  # range at least 60s so a short window still has a bucket
            vq = f"sum by (namespace, {lbl}) (count_over_time({sel}[{rng}]))"
            now_v = {(m.get("namespace"), m.get(lbl)) for m, v in loki.instant_vector(vq, end) if v > 0}
            for m, v in loki.instant_vector(vq, end - off):
                k = (m.get("namespace"), m.get(lbl))
                # Require 10 baseline lines so a service that logged once is not called "silent".
                if v >= 10 and k not in now_v and k[1]:
                    silent.append({"namespace": k[0], "service": k[1], "baseline": int(v)})
        except Exception as e:
            log.warning("silent-service check skipped: %s", e)

        # Every namespace that logged anything, errors or not. A suspect absent from this set is logs-missing.
        try:
            rng = f"{max(span // 1_000_000_000, 60)}s"
            nq = f"sum by (namespace) (count_over_time({sel}[{rng}]))"
            logged_namespaces = sorted({m.get("namespace") for m, v in loki.instant_vector(nq, end)
                                        if v > 0 and m.get("namespace")})
        except Exception as e:
            log.warning("namespace log check skipped: %s", e)

    kube = k8smod.collect(cfg.k8s, namespaces or cfg.namespaces, cfg.exclude_namespaces, start, end)
    cat.apply_k8s(kube["findings"])                # CrashLoop / probe entries from the catalog
    # A pattern that is new and whose first line is at or after the earliest rollout started with that deploy.
    cut = min((r["ts_ns"] for r in kube["rollouts"]), default=0)
    for iss in issues:
        iss.since_deploy = (iss.first_ns >= cut) if cut and iss.is_new else None
    targets = [(iss.namespace, pod, None) for iss in issues for pod in sorted(iss.pods)[:1]]
    targets += [(f["namespace"], f["pod"], f.get("container"))
                for f in kube["findings"] if f["kind"] in ("pod-state", "restart", "not-ready")]
    revisions = k8smod.read_revisions(cfg.k8s, targets)

    raw = {
        "environment": cfg.environment_name,
        "window_from": report.fmt_ts(start), "window_to": report.fmt_ts(end),
        "start_ns": start, "end_ns": end,
        "baseline_offset": loaded.baseline_offset if loaded else cfg.baseline_offset,
        "traces_from": str(loaded.directory) if loaded else None,
        "traces_saved": saved_to,
        "namespaces": ", ".join(namespaces or cfg.namespaces),
        "generated": report.fmt_ts(time.time_ns()), "query": q,
        "issues": [i.to_dict() for i in issues],
        "resolved": [i.to_dict() for i in miner.resolved()[:20]],
        "silent": sorted(silent, key=lambda s: -s["baseline"]),
        "k8s": kube["findings"], "rollouts": kube["rollouts"], "k8s_error": kube["error"],
        "revisions": revisions, "coverage": gaps,
        "grafana_url": cfg.grafana_url, "public_url": cfg.public_url,
        "service_label": cfg.service_label, "report_history": cfg.report_history,
    }
    # Open the file at the commit read from the pod. sources.yaml is not a commit to reuse.
    try:
        attach_snippets(raw["issues"], revisions)
    except Exception as e:
        log.warning("source snippets skipped: %s", e)
    if logged_namespaces is not None:
        raw["logged_namespaces"] = logged_namespaces
    try:
        raw["deps"] = analyze(raw, DepMap(cfg.dependency_map_paths))
    except Exception as e:
        # A bug in the dependency pass must not throw away the log and pod findings already collected.
        log.warning("dependency analysis skipped: %s", e)
        raw["deps"] = {"chains": [], "components": {}, "graph": [], "error": str(e)}
    r = report.build(raw)
    # Exit code 2 when the verdict is already unhealthy, or when any single pattern crosses critical_score.
    r["critical"] = r["unhealthy"] or any(i["score"] >= cfg.critical_score for i in r["issues"])
    return r


def _decorate(issues, events) -> None:
    """Attach the application throw site's repo, and the services that shared a trace id.

    `path` is the order those services first logged the id. It is a request path only when the
    services actually logged the same transaction; it is not taken from the dependency map.
    """
    sources = load_sources()
    by_tid: dict[str, list] = defaultdict(list)
    for ev in events:
        for tid in ev.trace_ids:
            by_tid[tid].append(ev)
    for iss in issues:
        if iss.code and iss.code.get("class"):
            row = repo_for(iss.code["class"], sources)
            if row:
                iss.code["repo"] = row["repo"]
        seen: set[str] = set()
        path: list[str] = []
        # Every event, on any service, that carried one of this issue's trace ids.
        shared = [ev for tid in iss.trace_ids for ev in by_tid.get(tid, [])]
        for ev in sorted(shared, key=lambda e: (e.ts_ns, e.service)):
            if ev.service in seen:
                continue                                # first time this service appears on the id
            seen.add(ev.service)
            path.append(ev.service)
        iss.path = path


def trace(cfg: Config, txn_id: str, start: int, end: int, namespaces: list[str] | None = None,
          events: list | None = None) -> dict:
    """Every log line (any level) mentioning an ID, across all services, in time order.

    This is a substring search (`|=`), not the error filter, so INFO lines on that transaction are included.
    Capped at 5000 lines; a chatty id should be narrowed with --since or -n.

    ``events`` searches lines already saved by a scan. Those are the error and warning lines from that
    window, so an INFO line that never matched the scan filter is not in the result.
    """
    if events is None:
        loki = LokiClient(cfg.loki)
        q = f'{selector(cfg, namespaces)} |= `{txn_id}`'
        events = parse(loki.query_range(q, start, end, max_lines=5000), cfg.service_label)
    else:
        q = f"saved traces |= `{txn_id}`"
        want = set(namespaces) if namespaces else None
        events = [e for e in events
                  if (want is None or e.namespace in want)
                  and (txn_id in (e.raw or "") or txn_id in (e.message or "") or txn_id in (e.trace_ids or []))]
    events.sort(key=lambda e: e.ts_ns)
    errors = [e for e in events if e.level in ("ERROR", "FATAL")]
    first_err = errors[0] if errors else None          # earliest error, which is what the CLI highlights
    return {
        "id": txn_id, "query": q, "count": len(events),
        "services": sorted({e.service for e in events}),
        "first_error": None if not first_err else {
            "service": first_err.service, "message": first_err.message,
            "root_cause": first_err.root_cause or first_err.exception, "error_codes": first_err.error_codes,
            "ts": report.fmt_ts(first_err.ts_ns)},
        "timeline": [{"ts": report.fmt_ts(e.ts_ns), "service": e.service, "pod": e.pod, "level": e.level,
                      "message": e.message, "error_codes": e.error_codes} for e in events],
    }

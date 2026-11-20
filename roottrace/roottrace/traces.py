"""Saved log lines for a scan, so a later run can analyze them without calling Loki again.

A scan writes three files under ``<out>/traces``:

- ``meta.json`` — the window, the query, and any slices that stopped early
- ``current.jsonl`` — one masked event per line for the window
- ``baseline.jsonl`` — the same for the comparison window

The lines are already masked. They stay on disk until the next scan of that output directory replaces them.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .parser import Event

_NAMES = {f.name for f in fields(Event)}


@dataclass
class SavedTraces:
    """What ``load`` hands back. ``directory`` is the folder the files were read from."""
    directory: Path
    start_ns: int
    end_ns: int
    baseline_offset: str
    query: str
    coverage: list
    current: list
    baseline: list


def dir_for(out_dir: str) -> Path:
    return Path(out_dir) / "traces"


def save(out_dir: str, start_ns: int, end_ns: int, baseline_offset: str, query: str,
         coverage: list, current: list, baseline: list) -> Path:
    """Write the window's events. Returns the traces directory."""
    dest = dir_for(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    _write_events(dest / "current.jsonl", current)
    _write_events(dest / "baseline.jsonl", baseline)
    meta = {
        "start_ns": start_ns, "end_ns": end_ns, "baseline_offset": baseline_offset,
        "query": query, "coverage": coverage,
        "current_count": len(current), "baseline_count": len(baseline),
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return dest


def load(out_dir: str) -> SavedTraces:
    """Read a previous scan's events. Raises FileNotFoundError when that scan never saved them."""
    dest = dir_for(out_dir)
    meta_path = dest / "meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(
            f"No saved traces in {dest}. Run a scan first; it downloads the lines. "
            "Use --no-download-traces only after that file exists.")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return SavedTraces(
        directory=dest,
        start_ns=int(meta["start_ns"]), end_ns=int(meta["end_ns"]),
        baseline_offset=meta.get("baseline_offset") or "24h",
        query=meta.get("query") or "",
        coverage=list(meta.get("coverage") or []),
        current=_read_events(dest / "current.jsonl"),
        baseline=_read_events(dest / "baseline.jsonl"),
    )


def _write_events(path: Path, events: list) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(asdict(ev), ensure_ascii=False))
            fh.write("\n")


def _read_events(path: Path) -> list:
    if not path.is_file():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            out.append(Event(**{k: raw[k] for k in _NAMES if k in raw}))
    return out

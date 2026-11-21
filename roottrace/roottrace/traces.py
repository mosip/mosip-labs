"""Saved log lines for a scan, so a later run can analyze them without calling Loki again.

A scan publishes one generation under ``<out>/traces/generations/<stamp>`` and then
points ``LATEST`` at it. A reader follows that pointer, so a save that stops halfway
cannot mix a new current file with an old baseline. A directory written before
generations existed is still read when ``LATEST`` is absent.

The lines are already masked.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
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
    """Write one complete generation, then publish it. Returns the traces directory."""
    dest = dir_for(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    gen = dest / "generations" / stamp
    gen.mkdir(parents=True)
    _write_events(gen / "current.jsonl", current)
    _write_events(gen / "baseline.jsonl", baseline)
    meta = {
        "start_ns": start_ns, "end_ns": end_ns, "baseline_offset": baseline_offset,
        "query": query, "coverage": coverage,
        "current_count": len(current), "baseline_count": len(baseline),
    }
    (gen / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    pointer = dest / "LATEST.tmp"
    pointer.write_text(json.dumps({"generation": stamp}), encoding="utf-8")
    pointer.replace(dest / "LATEST")
    return dest


def load(out_dir: str) -> SavedTraces:
    """Read the published generation. Raises FileNotFoundError when that scan never saved them."""
    dest = dir_for(out_dir)
    gen = _published(dest)
    meta_path = gen / "meta.json"
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
        current=_read_events(gen / "current.jsonl"),
        baseline=_read_events(gen / "baseline.jsonl"),
    )


def _published(dest: Path) -> Path:
    """The generation LATEST names. A directory from before generations is the folder itself."""
    latest = dest / "LATEST"
    if latest.is_file():
        name = json.loads(latest.read_text(encoding="utf-8")).get("generation")
        if name:
            return dest / "generations" / name
    return dest


def _write_events(path: Path, events: list) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(asdict(ev), ensure_ascii=False))
            fh.write("\n")


def _read_events(path: Path) -> list:
    """Read one event file. A missing file raises; an empty file is an empty scan."""
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            out.append(Event(**{k: raw[k] for k in _NAMES if k in raw}))
    return out

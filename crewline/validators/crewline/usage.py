"""Token usage per task, per workflow stage and per step, from the agent's own transcript.

  python -m crewline usage --manifest <task-manifest.json> --mark "<step label>"     # start a step (no transcript needed)
  python -m crewline usage --manifest <task-manifest.json> --transcript <session.jsonl> [--transcript ...] [--out usage.json]

The transcript (Claude Code: ~/.claude/projects/<workspace-slug>/<session-id>.jsonl, plus <session-id>/subagents/*.jsonl,
included automatically) records the API usage of every model call. Calls are assigned to the task by time:
  - stage = the workflow state the manifest was in when the call happened (manifest.started_at + state_history)
  - step  = the latest `usage_marks` label at or before the call
Token kinds: input (uncached), cache_write, cache_read, output. `fresh` = input + cache_write + output, the tokens that
were new to the model in that call; cache_read is the re-read conversation, cheap but often the largest number.
Calls are de-duplicated by message id. The numbers are what the API reported, not estimates.

  USE-001  no transcript records fall inside the task's time window   WARN
  USE-002  manifest has no started_at                                 BLOCK (cannot attribute usage)
"""
from __future__ import annotations

import bisect
import json
from datetime import datetime, timezone
from pathlib import Path

from .result import BLOCK, INFO, WARN, Result

KINDS = ("input", "cache_write", "cache_read", "output")


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def mark(manifest_path: str, label: str) -> Result:
    p = Path(manifest_path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc.setdefault("usage_marks", []).append({"label": label, "at": now_iso(), "state": doc.get("current_state")})
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    res = Result("usage-mark", inputs={"label": label, "state": doc.get("current_state")})
    res.summary = f"step '{label}' started in {doc.get('current_state')}"
    return res.finish()


def calls(transcripts: list[str]) -> list[dict]:
    """[{at, model, input, cache_write, cache_read, output}] de-duplicated by message id, sorted by time."""
    files: list[Path] = []
    for t in transcripts:
        p = Path(t)
        files.append(p)
        sub = p.with_suffix("") / "subagents"
        if sub.is_dir():
            files += sorted(sub.glob("*.jsonl"))
    seen: dict[str, dict] = {}
    for f in files:
        with f.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                msg = d.get("message") if isinstance(d.get("message"), dict) else None
                u = (msg or {}).get("usage")
                if not u or not d.get("timestamp"):
                    continue
                key = msg.get("id") or f"{f.name}:{d.get('uuid')}"
                seen[key] = {"at": _ts(d["timestamp"]), "model": msg.get("model", ""), "subagent": f.parent.name == "subagents",
                             "input": u.get("input_tokens", 0) or 0, "cache_write": u.get("cache_creation_input_tokens", 0) or 0,
                             "cache_read": u.get("cache_read_input_tokens", 0) or 0, "output": u.get("output_tokens", 0) or 0}
    return sorted(seen.values(), key=lambda c: c["at"])


def _bucket() -> dict:
    return {"calls": 0, **{k: 0 for k in KINDS}, "fresh": 0, "total": 0}


def _add(b: dict, c: dict) -> None:
    b["calls"] += 1
    for k in KINDS:
        b[k] += c[k]
    b["fresh"] += c["input"] + c["cache_write"] + c["output"]
    b["total"] += sum(c[k] for k in KINDS)


def report(manifest_path: str, transcripts: list[str], out: str | None = None) -> Result:
    res = Result("usage", inputs={"manifest": manifest_path, "transcripts": transcripts})
    doc = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not doc.get("started_at"):
        res.add("USE-002", BLOCK, "manifest.started_at is missing: set it when the task is created")
        return res.finish()
    # a task can span sessions: transcripts recorded in the manifest are always included
    transcripts = list(dict.fromkeys(doc.get("usage_transcripts", []) + list(transcripts)))
    transcripts = [t for t in transcripts if Path(t).is_file()]
    res.inputs["transcripts"] = transcripts
    start = _ts(doc["started_at"])
    end = _ts(doc["finished_at"]) if doc.get("finished_at") else float("inf")
    hist = doc.get("state_history", [])
    stage_at = [start] + [_ts(h["at"]) for h in hist]
    stage_name = [doc.get("initial_state") or (hist[0]["from"] if hist else doc.get("current_state"))] + [h["to"] for h in hist]
    marks = sorted(doc.get("usage_marks", []), key=lambda m: m["at"])
    mark_at = [_ts(m["at"]) for m in marks]

    overall, by_stage, by_step = _bucket(), {}, {}
    for c in calls(transcripts):
        if not start <= c["at"] <= end:
            continue
        stage = stage_name[bisect.bisect_right(stage_at, c["at"]) - 1]
        i = bisect.bisect_right(mark_at, c["at"]) - 1
        step = marks[i]["label"] if i >= 0 else "(before first step mark)"
        for b in (overall, by_stage.setdefault(stage, _bucket()), by_step.setdefault(step, _bucket())):
            _add(b, c)
    if not overall["calls"]:
        res.add("USE-001", WARN, "no model calls recorded in the task window (wrong transcript?)")
    data = {"task_id": doc.get("task_id"), "generated_at": now_iso(), "window": [doc["started_at"], doc.get("finished_at")],
            "overall": overall, "by_stage": by_stage, "by_step": by_step,
            "note": "fresh = input + cache_write + output; total adds cache_read (re-read context)."}
    target = Path(out) if out else Path(manifest_path).with_name("usage.json")
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    md = target.with_suffix(".md")
    md.write_text(to_markdown(data), encoding="utf-8")
    res.inputs.update(overall=overall, report=str(md))
    res.summary = (f"{overall['calls']} calls, fresh {overall['fresh']:,} / total {overall['total']:,} tokens "
                   f"(output {overall['output']:,}); {md}")
    for stage, b in by_stage.items():
        res.add("USE-STAGE", INFO, f"{stage}: {b['calls']} calls, fresh {b['fresh']:,}, total {b['total']:,}")
    return res.finish()


def to_markdown(data: dict) -> str:
    def table(title: str, rows: dict) -> str:
        lines = [f"### {title}", "", "| | calls | input | cache write | cache read | output | fresh | total |",
                 "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for name, b in rows.items():
            lines.append(f"| {name} | {b['calls']} | {b['input']:,} | {b['cache_write']:,} | {b['cache_read']:,} | "
                         f"{b['output']:,} | {b['fresh']:,} | {b['total']:,} |")
        return "\n".join(lines) + "\n"
    return (f"# Token usage - {data['task_id']}\n\nWindow {data['window'][0]} -> {data['window'][1] or 'now'} "
            f"(generated {data['generated_at']}). {data['note']}\n\n"
            + table("Overall", {"task": data["overall"]}) + "\n" + table("By stage", data["by_stage"]) + "\n"
            + table("By step", data["by_step"]))

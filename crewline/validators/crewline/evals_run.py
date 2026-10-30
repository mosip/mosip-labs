"""Frozen eval pack: scenarios.yaml automated_by tests must exist (and optionally still pass).

  python -m crewline evals                    # every automated_by nodeid exists on disk
  python -m crewline evals --run              # also execute those pytest nodeids
  python -m crewline evals --pack frozen      # the 8-story official pack + expected-outcomes/
  python -m crewline evals --pack frozen --run

  EVAL-001  automated_by names a test that is not in validators/tests                                 BLOCK
  EVAL-002  --run: pytest failed on the frozen nodeids                                                BLOCK
  EVAL-003  a non-manual scenario has no parseable automated_by tests                                 WARN
  EVAL-004  --pack frozen: a story is missing evals/expected-outcomes/<id>.json                       BLOCK
  EVAL-005  --pack frozen: expected-outcomes pytest nodeid is not on disk                             BLOCK

The two-model contract is: Cursor and Claude both keep `--pack frozen --run` green. This layer does
not invoke the LLMs.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

from .result import BLOCK, WARN, Result

CORE = Path(__file__).resolve().parents[2]
SCENARIOS = CORE / "evals" / "task-scenarios" / "scenarios.yaml"
FROZEN = CORE / "evals" / "frozen-pack.yaml"
OUTCOMES = CORE / "evals" / "expected-outcomes"
TESTS = CORE / "validators" / "tests"
FILE_RX = re.compile(r"(?:validators/tests/)?(test_\w+\.py)::(\w+)")
CONT_RX = re.compile(r"^::(\w+)")
NODE_RX = re.compile(r"(?:validators/)?(tests/test_\w+\.py)::(\w+)")


def parse_automated_by(text: str, last_file: str | None) -> tuple[list[tuple[str, str]], str | None]:
    """Return [(file, test), ...] and the last file seen (for ::continuation)."""
    if not text or text.strip().lower().startswith("manual"):
        return [], last_file
    found: list[tuple[str, str]] = []
    file = last_file
    for part in re.split(r"[,;]", text):
        bit = part.strip()
        if not bit or bit.lower().startswith("manual") or "adapter" in bit.lower() and "manual" in bit.lower():
            continue
        m = FILE_RX.search(bit)
        if m:
            file = m.group(1)
            found.append((file, m.group(2)))
            continue
        m = CONT_RX.search(bit)
        if m and file:
            found.append((file, m.group(1)))
    return found, file


def collect() -> tuple[list[dict], list[tuple[str, str, str]]]:
    """scenarios, and (scenario_id, file, test) triples."""
    data = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios") or []
    triples: list[tuple[str, str, str]] = []
    last = None
    for sc in scenarios:
        pairs, last = parse_automated_by(sc.get("automated_by") or "", last)
        for f, t in pairs:
            triples.append((sc.get("id", "?"), f, t))
    return scenarios, triples


def frozen_story_ids() -> list[str]:
    data = yaml.safe_load(FROZEN.read_text(encoding="utf-8"))
    out: list[str] = []
    for s in data.get("stories") or []:
        sid = str(s).split("#", 1)[0].strip().split()[0]
        if sid:
            out.append(sid)
    return out


def _test_exists(file: str, name: str, cache: dict[str, str]) -> bool:
    path = TESTS / file
    if file not in cache:
        cache[file] = path.read_text(encoding="utf-8") if path.is_file() else ""
    return path.is_file() and f"def {name}(" in cache[file]


def run(execute: bool = False, pack: str | None = None) -> Result:
    res = Result("evals", inputs={"scenarios": str(SCENARIOS), "pack": pack or "all"})
    try:
        scenarios, triples = collect()
    except (OSError, yaml.YAMLError) as e:
        return Result.not_run("evals", str(e))
    wanted: set[str] | None = None
    extra_nodeids: list[str] = []
    if pack:
        if pack != "frozen":
            return Result.not_run("evals", f"unknown pack {pack!r}: use frozen")
        try:
            wanted = set(frozen_story_ids())
        except (OSError, yaml.YAMLError) as e:
            return Result.not_run("evals", str(e))
        res.inputs["frozen_stories"] = sorted(wanted)
        scenarios = [sc for sc in scenarios if sc.get("id") in wanted]
        triples = [t for t in triples if t[0] in wanted]
        for sid in sorted(wanted):
            path = OUTCOMES / f"{sid}.json"
            if not path.is_file():
                res.add("EVAL-004", BLOCK, f"{sid}: missing {path.relative_to(CORE).as_posix()}",
                        evidence=sid, remediation="write expected FAIL/PASS after the first observed run")
                continue
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                res.add("EVAL-004", BLOCK, f"{sid}: expected-outcomes is not JSON ({e})", evidence=sid)
                continue
            for node in body.get("pytest") or []:
                m = NODE_RX.search(str(node)) or FILE_RX.search(str(node))
                if not m:
                    res.add("EVAL-005", BLOCK, f"{sid}: unparseable pytest nodeid {node!r}", evidence=sid)
                    continue
                file, name = m.group(1).rsplit("/", 1)[-1], m.group(2)
                extra_nodeids.append(f"tests/{file}::{name}")
                triples.append((sid, file, name))
    res.inputs["scenario_count"] = len(scenarios)
    res.inputs["automated_tests"] = len(triples)
    tests_by_file: dict[str, str] = {}
    extra_set = set(extra_nodeids)
    for sid, file, name in triples:
        if _test_exists(file, name, tests_by_file):
            continue
        rule = "EVAL-005" if f"tests/{file}::{name}" in extra_set else "EVAL-001"
        res.add(rule, BLOCK, f"{sid}: {file}::{name} is not in validators/tests", evidence=f"{file}::{name}")
    for sc in scenarios:
        auto = sc.get("automated_by") or ""
        if auto.strip().lower().startswith("manual"):
            continue
        pairs, _ = parse_automated_by(auto, None)
        if not pairs and "test_" not in auto:
            res.add("EVAL-003", WARN, f"{sc.get('id')}: automated_by has no parseable pytest nodeid")
    if execute and not any(f.severity == BLOCK for f in res.findings):
        nodeids = sorted({f"tests/{f}::{t}" for _, f, t in triples} | set(extra_nodeids))
        if nodeids:
            proc = subprocess.run([sys.executable, "-m", "pytest", "-q", *nodeids], cwd=str(CORE / "validators"),
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")
            res.inputs["pytest_exit"] = proc.returncode
            if proc.returncode != 0:
                res.add("EVAL-002", BLOCK, f"frozen eval pytest failed (exit {proc.returncode})",
                        evidence=(proc.stdout + proc.stderr)[-1500:])
    return res.finish()

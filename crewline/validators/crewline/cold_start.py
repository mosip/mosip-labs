"""New-machine kit for Crewline itself. Not a MOSIP P5 and not a provisioned cluster.

  python -m crewline cold-start

  CS-001  frozen eval pack (expected-outcomes + nodeids) FAIL                                      BLOCK
  CS-002  adapter --sync/--check FAIL for cursor, claude or generic                                BLOCK
  CS-003  synthetic feature --apply sequence does not refuse then accept the rails                 BLOCK
  CS-004  remaining human steps (evals/cold-start.md)                                              INFO

A PASS here means this clone can enforce the rails. A real feature on a stranger's machine is
evals/cold-start.md — that still needs a module clone, a local-stack, and no Crewline author in the chat.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import adapter_check, evals_run, manifest, pack
from .result import BLOCK, INFO, Result
from .task import skeleton

CORE = Path(__file__).resolve().parents[2]
INSTALL = CORE / "adapters" / "install.py"
PLAYBOOK = CORE / "evals" / "cold-start.md"


def _write(dir_path: Path, doc: dict, name: str = "task-manifest.json") -> str:
    p = dir_path / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def _synthetic(res: Result) -> None:
    """Prove --apply refuses IMPACT without clarity and REVIEW without fit, then accepts both."""
    d = skeleton("cold-start-synth", "feature")
    d["current_state"] = "ACCEPTANCE_REVIEW"
    d["gates"] = [{"gate": "input_readiness", "status": "PASS"}]
    d["requirements"] = {
        "source_refs": ["MOSIP-0"],
        "acceptance_criteria": [{"id": "AC-1", "text": "POST /x with a missing name returns 400 and error MOSIP-X"}],
        "open_ambiguities": 0,
    }
    with tempfile.TemporaryDirectory(prefix="crewline-cs-") as raw:
        root = Path(raw)
        path = _write(root, d)
        first = manifest.apply(path, "IMPACT_ANALYSIS")
        if first.status != "FAIL" or "requirement_clarity" not in first.to_text():
            res.add("CS-003", BLOCK, "synthetic IMPACT_ANALYSIS must FAIL until requirement_clarity PASS",
                    evidence=first.to_text()[-800:])
            return
        d["gates"] += [{"gate": "requirement_clarity", "status": "PASS"},
                       {"gate": "acceptance_readiness", "status": "PASS"}]
        path = _write(root, d, "clarity.json")
        second = manifest.apply(path, "IMPACT_ANALYSIS")
        if second.status != "PASS":
            res.add("CS-003", BLOCK, "synthetic IMPACT_ANALYSIS must PASS once clarity gates are recorded",
                    evidence=second.to_text()[-800:])
            return
        d["current_state"] = "UNIT_INTEGRATION_TEST"
        d["gates"] = [{"gate": "deterministic_validation", "status": "PASS"}]
        path = _write(root, d, "review.json")
        third = manifest.apply(path, "IMPLEMENTATION_REVIEW")
        text = third.to_text()
        if third.status != "FAIL" or "requirement_fit" not in text:
            res.add("CS-003", BLOCK, "synthetic IMPLEMENTATION_REVIEW must FAIL until requirement_fit PASS",
                    evidence=text[-800:])
            return
        d["gates"] += [{"gate": "coding_standards", "status": "PASS"},
                       {"gate": "robustness", "status": "PASS"},
                       {"gate": "requirement_fit", "status": "PASS"}]
        path = _write(root, d, "review-ok.json")
        fourth = manifest.apply(path, "IMPLEMENTATION_REVIEW")
        if fourth.status != "PASS":
            res.add("CS-003", BLOCK, "synthetic IMPLEMENTATION_REVIEW must PASS once fit/standards/robustness PASS",
                    evidence=fourth.to_text()[-800:])


def run() -> Result:
    res = Result("cold-start", inputs={"pack": pack.active_id(), "playbook": str(PLAYBOOK)})
    frozen = evals_run.run(execute=False, pack="frozen")
    if frozen.status == "FAIL":
        for f in frozen.findings:
            if f.severity == BLOCK:
                res.add("CS-001", BLOCK, f"frozen pack: {f.rule_id} {f.message}", evidence=f.evidence)
    elif frozen.status == "NOT_RUN":
        res.add("CS-001", BLOCK, f"frozen pack not run: {frozen.summary}")
    with tempfile.TemporaryDirectory(prefix="crewline-adp-") as raw:
        target = Path(raw)
        for platform in ("cursor", "claude", "generic"):
            check = adapter_check.run(platform, str(target), sync=True)
            if check.status == "FAIL":
                for f in check.findings:
                    res.add("CS-002", BLOCK, f"{platform}: {f.message}", evidence=platform)
            elif check.status == "NOT_RUN":
                res.add("CS-002", BLOCK, f"{platform}: adapter-check not run: {check.summary}", evidence=platform)
    _synthetic(res)
    res.add("CS-004", INFO,
            "framework kit only. Human P5 (one feature, new machine, every --apply, no Crewline author): "
            + PLAYBOOK.as_posix())
    return res.finish()

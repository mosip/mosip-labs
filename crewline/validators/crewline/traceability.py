"""Cross-SDLC traceability: Requirement -> AC -> code -> test id -> recorded result (Plan §8).

  TRC-001  AC has no test (no test_ids and no matrix_row_ids)                         BLOCK
  TRC-002  code task and the AC has no code_refs                                       BLOCK (NFR ACs: WARN)
  TRC-003  a test id of the AC has no recorded result on the branch (test_results)     BLOCK
  TRC-004  a test id of the AC FAILS on the branch                                     WARN (full_regression + exceptions decide)
  TRC-005  a code_ref is outside scope.approved_paths                                  BLOCK
  TRC-006  no acceptance criteria recorded at all                                      BLOCK
  TRC-008  code task: a user-facing AC (`api: true` or `ui: true`) has no system-level automated test
           (`system_test_ids`: TestRig uniqueIdentifier / UI rig scenario) - SDET builds it if it does not exist   BLOCK
  TRC-009  a system_test_id has no result, or is DEFERRED without an attributed system_tests exception         BLOCK
  TRC-007  system tests NOT_APPLICABLE and an API-facing AC (`api: true`) has no component test
           (`component_test_ids`: MockMvc / @WebMvcTest / @SpringBootTest at the HTTP boundary) with a PASS result   BLOCK

For the SDET path (task_type test-automation) traceability is AC -> matrix row -> uniqueIdentifier, which
CoverageCli already checks; this validator then only needs test_ids/matrix_row_ids and results.
"""
from __future__ import annotations

import json
from pathlib import Path

from .change_scope import _match
from .result import BLOCK, WARN, Result

CODE_TASKS = {"feature", "bug-fix", "database-migration", "dependency-upgrade"}
NEW_BEHAVIOUR_TASKS = {"feature", "bug-fix", "database-migration"}     # ACs that must be automated end to end


def run(manifest_path: str) -> Result:
    res = Result("traceability", inputs={"manifest": manifest_path})
    doc = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    acs = doc.get("requirements", {}).get("acceptance_criteria", [])
    task_type = doc.get("task_type") or "test-automation"
    approved = doc.get("scope", {}).get("approved_paths", [])
    results = {k.lower(): v for k, v in doc.get("test_results", {}).items()}
    deferred_ok = any(e.get("gate") == "system_tests" and all(e.get(k) for k in ("approver", "reason", "scope", "timestamp"))
                      for e in doc.get("exceptions", []))
    system_na = deferred_ok or any(g.get("gate") == "system_tests" and g.get("status") == "NOT_APPLICABLE"
                                   for g in doc.get("gates", []))
    if not acs:
        res.add("TRC-006", BLOCK, "no acceptance criteria recorded")
    for ac in acs:
        aid = ac.get("id", "?")
        tests = ac.get("test_ids", [])
        if not tests and not ac.get("matrix_row_ids"):
            res.add("TRC-001", BLOCK, f"{aid}: no test maps to this acceptance criterion", evidence=aid)
        if task_type in CODE_TASKS and not ac.get("code_refs"):
            res.add("TRC-002", WARN if ac.get("nfr") else BLOCK, f"{aid}: no code_refs (which change implements it?)", evidence=aid)
        for t in tests:
            r = results.get(t.lower())
            if r is None or r == "NOT_RUN":
                res.add("TRC-003", BLOCK, f"{aid}: {t} has no recorded result on the branch", evidence=t)
            elif r == "FAIL":
                res.add("TRC-004", WARN, f"{aid}: {t} fails on the branch", evidence=t)
        if system_na and ac.get("api") and not any(results.get(t.lower()) == "PASS" for t in ac.get("component_test_ids", [])):
            res.add("TRC-007", BLOCK, f"{aid}: API-facing and no system tests ran - needs a passing component test "
                                      "at the HTTP boundary (component_test_ids)", evidence=aid)
        user_facing = ac.get("api") or ac.get("ui")
        if task_type in NEW_BEHAVIOUR_TASKS and user_facing and not ac.get("system_test_ids"):
            res.add("TRC-008", BLOCK, f"{aid}: user-facing and no automated system test (system_test_ids) - "
                                      "SDET: reuse a TestRig/UI-rig case or build one in this task", evidence=aid)
        for t in ac.get("system_test_ids", []):
            r = results.get(t.lower())
            if r == "DEFERRED" and deferred_ok:
                res.add("TRC-009", WARN, f"{aid}: {t} deferred to the post-merge run (attributed system_tests exception)", evidence=t)
            elif r in (None, "NOT_RUN", "DEFERRED"):
                res.add("TRC-009", BLOCK, f"{aid}: system test {t} has no result on the branch build", evidence=t)
            elif r == "FAIL":
                res.add("TRC-004", WARN, f"{aid}: system test {t} fails on the branch (see defects)", evidence=t)
        for ref in ac.get("code_refs", []):
            path = ref.split(":")[0].split("#")[0]
            if approved and not any(_match(path, p) for p in approved):
                res.add("TRC-005", BLOCK, f"{aid}: code_ref {path} is outside the approved paths", path=path)
    res.inputs["acceptance_criteria"] = len(acs)
    return res.finish()

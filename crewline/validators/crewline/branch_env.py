"""Branch-environment gate (Q8): system tests of production code need an env running THIS branch.

Does not provision the environment. It refuses SYSTEM_TEST_EXECUTION when the plan has no
kind, names a released-only env as if it were the branch, or defers without an exception.

  BEV-001  code/test task: test_plan.environment_kind missing or not an allowed value              BLOCK
  BEV-002  post-merge-deferred without an attributed system_tests exception                        BLOCK
  BEV-003  environment_kind is branch-deployed-env or local-stack but test_plan.environment empty  BLOCK
  BEV-004  environment string names a released-only host (api-internal.released) as if it were the branch  BLOCK

  python -m crewline branch-env --manifest <m>
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .result import BLOCK, Result

RELEASED_HOST = re.compile(r"api-internal\.released|\.released\b|released-only", re.I)

NEEDS_ENV = {"feature", "bug-fix", "refactor", "dependency-upgrade", "database-migration", "test-automation"}
ALLOWED = {"branch-deployed-env", "local-stack", "post-merge-deferred"}


def run(manifest_path: str) -> Result:
    res = Result("branch-env", inputs={"manifest": manifest_path})
    try:
        doc = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return Result.not_run("branch-env", str(e))
    task_type = doc.get("task_type") or "test-automation"
    if task_type not in NEEDS_ENV:
        return res.finish()
    plan = doc.get("test_plan") or {}
    kind = plan.get("environment_kind") or ""
    env = (plan.get("environment") or "").strip()
    if kind not in ALLOWED:
        res.add("BEV-001", BLOCK, f"test_plan.environment_kind={kind!r}: need branch-deployed-env, local-stack, "
                "or post-merge-deferred (open-questions Q8: an env that runs the branch build)",
                remediation="name how the branch build gets onto a non-prod env, or a local-stack; never treat "
                "api-internal.released as the branch")
    if kind == "post-merge-deferred":
        ok = any(e.get("gate") == "system_tests" and all(e.get(k) for k in ("approver", "reason", "scope", "timestamp"))
                 for e in doc.get("exceptions") or [])
        if not ok:
            res.add("BEV-002", BLOCK, "post-merge-deferred needs an attributed system_tests exception "
                    "(environment + date); results stay DEFERRED and become a follow-up task")
    if kind in {"branch-deployed-env", "local-stack"} and not env:
        res.add("BEV-003", BLOCK, "environment_kind set but test_plan.environment is empty")
    if kind in {"branch-deployed-env", "local-stack"} and env and RELEASED_HOST.search(env):
        res.add("BEV-004", BLOCK, f"test_plan.environment={env!r} is a released-only host; Q8 needs the BRANCH build "
                "(local-stack docker-compose / mvn spring-boot:run, or a named dev/qa env running this image)")
    res.inputs["environment_kind"] = kind
    return res.finish()

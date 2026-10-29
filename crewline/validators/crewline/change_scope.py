"""Change-scope gate: every changed file must be inside the plan's approved paths.

  SCP-001  file changed outside scope.approved_paths (no scope_change approval names it)      BLOCK
  SCP-002  sensitive path changed (CI workflows, build/deploy config, secrets-like files)      BLOCK unless approved
  SCP-003  approved path matched nothing in the change (plan and diff disagree)                INFO

approved_paths are globs relative to the repository root (`**` crosses directories). A human approval with
action `scope_change` whose `scope` contains the path (or a glob matching it) covers SCP-001/SCP-002.
"""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path

from .gitio import changed_files
from .result import BLOCK, INFO, Result

SENSITIVE = [".github/**", "**/Dockerfile", "helm/**", "deploy/**", "**/*.env", "**/application-*.properties",
             "**/bootstrap*.properties", "**/settings.xml", "Jenkinsfile"]


def _match(path: str, pattern: str) -> bool:
    pattern = pattern.strip().removeprefix("./")
    return fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(path, pattern.replace("**/", "")) \
        or (pattern.endswith("/**") and path.startswith(pattern[:-3] + "/")) or path == pattern


def run(repo: str, base: str, manifest_path: str) -> Result:
    res = Result("change-scope", inputs={"repo": repo, "base": base})
    doc = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    approved = doc.get("scope", {}).get("approved_paths", [])
    if not approved:
        return Result.not_run("change-scope", "scope.approved_paths is empty: the plan must list what may change")
    try:
        changed = changed_files(repo, base)
    except RuntimeError as e:
        return Result.not_run("change-scope", str(e))
    grants = [a for a in doc.get("approvals", []) if a.get("action") == "scope_change"
              and all(a.get(k) for k in ("approver", "reason", "scope", "timestamp"))]

    def granted(path: str) -> str | None:
        for a in grants:
            for item in a["scope"].replace(",", " ").split():
                if _match(path, item):
                    return a["approver"]
        return None

    used = set()
    for path, kind in sorted(changed.items()):
        hits = [p for p in approved if _match(path, p)]
        used.update(hits)
        if not hits:
            f = res.add("SCP-001", BLOCK, f"{kind} {path} is outside the approved paths", path=path,
                        remediation="impact analysis + approval scope_change naming the file, or revert it")
            f.approved_by = granted(path)
        if any(_match(path, s) for s in SENSITIVE):
            f = res.add("SCP-002", BLOCK, f"{kind} {path} is a CI/build/deploy/config file", path=path,
                        remediation="needs an explicit scope_change approval even when inside approved paths")
            f.approved_by = granted(path)
    for p in approved:
        if p not in used:
            res.add("SCP-003", INFO, f"approved path {p} has no change")
    res.inputs["changed_files"] = len(changed)
    return res.finish()

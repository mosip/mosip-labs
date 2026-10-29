"""Expected-result / assertion change detector (Plan §23.2, Blueprint §6.1).

Compares the working tree against a base ref. Every finding is BLOCK unless an approval record
covers it. Approvals live in the task workspace, never in the module repo:

    approvals:
      - rule_id: EXP-001
        target: preReg/createPrereg/createPrereg.yml::Prereg_CreatePrereg_All_Valid_Smoke_sid_pos
        approver: <name>
        reason: <approved requirement change, with story key>
        timestamp: 2026-10-27T10:00:00Z

Rules
  EXP-001  `output` changed
  EXP-002  `outputTemplate` changed
  EXP-003  assertion relaxed: checkErrorsOnlyInResponse / checkOnlyStatusCodeInResponse turned on
  EXP-004  expected value replaced by $IGNORE$
  EXP-005  case removed
  EXP-006  uniqueIdentifier changed for the same case name (identity churn)
  EXP-007  result template (*Result.hbs / error.hbs) changed
  EXP-008  case added to testCaseSkippedList.txt
  EXP-009  role changed (can turn an auth-negative case into a positive one)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .apitestrig import Module
from .result import BLOCK, WARN, Result

RELAX_FLAGS = ("checkErrorsOnlyInResponse", "checkOnlyStatusCodeInResponse")


def _truthy(v) -> bool:
    return str(v).strip().lower() == "true"


def _json_or_none(s):
    try:
        return json.loads(re.sub(r"\$[A-Z0-9_:]+\$", '"__tok__"', s or ""))
    except (ValueError, TypeError):
        return None


def _ignored_fields(before: str, after: str) -> list[str]:
    """Fields whose expected value became $IGNORE$."""
    pat = re.compile(r'"([^"]+)"\s*:\s*"?([^",}\n]*)')
    b = dict(pat.findall(before or ""))
    a = dict(pat.findall(after or ""))
    return [k for k, v in a.items() if v.strip() == "$IGNORE$" and k in b and b[k].strip() != "$IGNORE$"]


def load_approvals(path: str | None) -> list[dict]:
    if not path:
        return []
    return (yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}).get("approvals", [])


def run(module: Module, base: str, approvals_file: str | None = None) -> Result:
    res = Result("expected-result-diff", inputs={"module_root": str(module.root), "base": base})
    try:
        before = {(c.yml, c.name): c for c in module.base_cases(base)}
        changed = module.changed_paths(base)
    except Exception as e:  # git missing, bad ref, not a repo
        return Result.not_run("expected-result-diff", f"cannot read base '{base}': {e}")
    after = {(c.yml, c.name): c for c in module.cases()}
    for rel, msg in {**module.base_parse_errors, **module.parse_errors}.items():
        touched = rel in changed
        res.add("YAML-PARSE", BLOCK if touched else WARN,
                f"YAML does not parse{'' if touched else ' (not touched; its cases are not diffed)'}: {msg}", path=rel)
    # An empty base next to a populated working tree means the paths are wrong, not that every
    # case is new. Never let that read as PASS.
    if not before and after:
        return Result.not_run("expected-result-diff",
                              f"base '{base}' has no testcase YAML under {module.resources_git_prefix()} "
                              f"while the working tree has {len(after)} case(s); check --module-root/profile")
    res.inputs["base_cases"] = len(before)
    res.inputs["working_cases"] = len(after)

    for key, b in before.items():
        a = after.get(key)
        target = f"{key[0]}::{key[1]}"
        if a is None:
            res.add("EXP-005", BLOCK, "case removed", path=key[0], line=b.line, evidence=target,
                    remediation="removing a case needs approval; its matrix row must become 🟡 not_automated")
            continue
        at = dict(path=a.yml, line=a.line, evidence=target)
        bf, af = b.fields, a.fields
        if (bf.get("output") or "") != (af.get("output") or ""):
            if _json_or_none(bf.get("output")) != _json_or_none(af.get("output")) or \
                    _json_or_none(bf.get("output")) is None:
                res.add("EXP-001", BLOCK, "expected output changed", **at)
            for fld in _ignored_fields(bf.get("output"), af.get("output")):
                res.add("EXP-004", BLOCK, f"expected value of '{fld}' replaced by $IGNORE$", **at)
        if bf.get("outputTemplate") != af.get("outputTemplate"):
            res.add("EXP-002", BLOCK, f"outputTemplate {bf.get('outputTemplate')} -> {af.get('outputTemplate')}", **at)
        for flag in RELAX_FLAGS:
            if _truthy(af.get(flag)) and not _truthy(bf.get(flag)):
                res.add("EXP-003", BLOCK, f"assertion relaxed: {flag} turned on", **at)
        if bf.get("uniqueIdentifier") != af.get("uniqueIdentifier"):
            res.add("EXP-006", BLOCK, f"uniqueIdentifier {bf.get('uniqueIdentifier')} -> {af.get('uniqueIdentifier')}",
                    remediation="IDs are stable; matrix rows reference them", **at)
        if bf.get("role") != af.get("role"):
            res.add("EXP-009", WARN, f"role {bf.get('role')} -> {af.get('role')}", **at)

    for rel in changed:
        name = Path(rel).name
        if name.endswith("Result.hbs") or name.lower() == "error.hbs":
            res.add("EXP-007", BLOCK, "result template changed", path=rel, evidence=rel)
        if name == "testCaseSkippedList.txt":
            try:
                old = set(module.read_base(base, rel).split())
            except Exception:
                old = set()
            new = set((module.resources / rel).read_text(encoding="utf-8").split()) if (module.resources / rel).exists() else set()
            for skipped in sorted(new - old):
                res.add("EXP-008", BLOCK, f"case added to skip list: {skipped}", path=rel, evidence=skipped)

    for appr in load_approvals(approvals_file):
        if str(appr.get("status", "")).upper().startswith(("SUPERSEDED", "REVOKED")):
            continue  # a withdrawn approval never covers a finding
        for f in res.findings:
            if f.rule_id == appr.get("rule_id") and appr.get("target") in (f.evidence, f.path) \
                    and appr.get("approver") and appr.get("reason"):
                f.approved_by = appr["approver"]
    res.inputs["changed_paths"] = len(changed)
    return res.finish()

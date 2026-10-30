"""Requirement-fit gate: the diff must implement the story/bug, not a nearby guess.

Traceability checks that ACs *link* to code and tests. This gate checks that the *content*
of those files (and the production diff vs base) still contains the observables the AC named
(status, error code, route, quoted value). Review rounds of "that's not what the story said"
are a process failure. IMPLEMENTATION_REVIEW is refused until this PASSes.

  RFT-001  an extractable AC token (status / MOSIP-* / route / quoted value) is absent from the
           production diff and the AC's code_ref files                                                   BLOCK
  RFT-002  a non-NFR AC's code_ref was not touched in this change                                        BLOCK
  RFT-003  story/bug task has no acceptance criteria                                                     BLOCK
  RFT-004  an AC has no extractable observable (clarity should have caught this; still WARN)             WARN
  RFT-005  code task: none of the AC observables appear in a changed *test* file                         BLOCK

  python -m crewline requirement-fit --repo <dir> --base <ref> --manifest <m>
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .coding_standards import is_test_path
from .gitio import changed_files, git, top
from .result import BLOCK, WARN, Result

STORY_TASKS = {"feature", "bug-fix", "test-automation", "database-migration"}
CODE_TASKS = {"feature", "bug-fix", "database-migration"}
STATUS = re.compile(r"\b([1-5]\d{2})\b")
ERROR = re.compile(r"\b(MOSIP[-_][A-Z0-9][-A-Z0-9]*)\b", re.I)
QUOTED = re.compile(r"\"([^\"]{3,80})\"|'([^']{3,80})'")
ROUTE = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+(\/\S+)", re.I)


def observables(text: str) -> list[str]:
    found: list[str] = []
    for rx in (STATUS, ERROR, ROUTE):
        found.extend(rx.findall(text or ""))
    for m in QUOTED.finditer(text or ""):
        found.append(m.group(1) or m.group(2))
    out, seen = [], set()
    for tok in found:
        key = tok.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(tok.strip())
    return out


def _ref_path(ref: str) -> str:
    return (ref or "").split(":")[0].split("#")[0].replace("\\", "/").lstrip("./")


def _haystack(repo: Path, base: str, acs: list[dict]) -> str | None:
    try:
        parts = [git(repo, "diff", base)]
    except RuntimeError as e:
        return None if "Needed a single revision" in str(e) or "unknown revision" in str(e).lower() else None
    for ac in acs:
        for ref in ac.get("code_refs") or []:
            path = _ref_path(ref)
            fp = repo / path
            if fp.is_file():
                try:
                    parts.append(fp.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    pass
    return "\n".join(parts)


def run(repo: str, base: str, manifest_path: str) -> Result:
    res = Result("requirement-fit", inputs={"repo": repo, "base": base, "manifest": manifest_path})
    try:
        doc = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        root = top(repo)
        changed = changed_files(root, base)
    except (OSError, ValueError, RuntimeError) as e:
        return Result.not_run("requirement-fit", str(e))
    task_type = doc.get("task_type") or "test-automation"
    if task_type not in STORY_TASKS:
        return res.finish()
    acs = (doc.get("requirements") or {}).get("acceptance_criteria") or []
    if not acs:
        res.add("RFT-003", BLOCK, "no acceptance criteria: cannot prove the diff implements the story/bug")
        return res.finish()
    hay = _haystack(root, base, acs)
    if hay is None:
        return Result.not_run("requirement-fit", f"cannot diff {base}")
    hay_l = hay.lower()
    prod_changed = {p.replace("\\", "/") for p, st in changed.items()
                    if st != "D" and not is_test_path(p)}
    test_hay_parts: list[str] = []
    if task_type in CODE_TASKS:
        for p, st in changed.items():
            if st == "D" or not is_test_path(p):
                continue
            fp = root / p
            if fp.is_file():
                try:
                    test_hay_parts.append(fp.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    pass
    test_hay_l = "\n".join(test_hay_parts).lower()
    for ac in acs:
        aid = ac.get("id", "?")
        text = ac.get("text") or ""
        tokens = observables(text)
        if not tokens:
            res.add("RFT-004", WARN, f"{aid}: no status/error/route/quoted token to match against the diff",
                    evidence=aid)
            continue
        missing = [t for t in tokens if t.lower() not in hay_l]
        if missing:
            res.add("RFT-001", BLOCK, f"{aid}: AC observables not in the diff or code_refs: {missing}",
                    evidence=aid, remediation="implement the named status/error/route/value, or correct the AC")
        if task_type in CODE_TASKS and not ac.get("nfr"):
            refs = [_ref_path(r) for r in (ac.get("code_refs") or []) if _ref_path(r)]
            if refs and not any(r in prod_changed or any(c == r or c.startswith(r.rstrip("/") + "/")
                                                         for c in prod_changed) for r in refs):
                res.add("RFT-002", BLOCK, f"{aid}: code_refs {refs} were not touched in this change",
                        evidence=aid, remediation="point code_refs at the files this task actually changed")
            if tokens and not any(t.lower() in test_hay_l for t in tokens):
                res.add("RFT-005", BLOCK, f"{aid}: AC observables are not in any changed test "
                        "(a production string is not proof the test asserts the story)",
                        evidence=aid, remediation="assert the named status/error/route in a unit or component test")
    res.inputs["acceptance_criteria"] = len(acs)
    return res.finish()

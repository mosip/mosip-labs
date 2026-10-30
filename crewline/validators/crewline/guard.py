"""Platform-enforced rails: block shipping actions unless the task gates already pass.

  GRD-001  commit / push / PR with no active Crewline task
  GRD-002  always-denied action (force-push, hard reset, stash, branch delete, merge, production)
  GRD-003  commit / push / PR before the matching workflow state and gates
  GRD-004  write outside scope.approved_paths (and no scope_change grant)
  GRD-005  git commit without -s / --signoff
  GRD-006  --no-verify (skipping git hooks)

The Cursor / Claude adapter runs this from a platform hook so the model cannot skip
`crewline manifest` and still commit. Exit 0 PASS, 1 FAIL, 2 NOT_RUN.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .change_scope import SENSITIVE, _match
from .manifest import CORE, check, transition
from .result import BLOCK, Result

TASKS = CORE / "tasks"
TERMINAL = {"DONE"}
TERMINAL_OUTCOMES = {"SUCCESS", "FAILED", "BLOCKED", "ESCALATED"}
COMMIT_STATES = {"QUALITY_GATE", "COMMIT_PR"}
PUSH_STATES = {"COMMIT_PR", "PR_CLOSEOUT"}
ALWAYS_ALLOW_WRITE_PREFIXES = (
    str(CORE / "tasks").replace("\\", "/").lower() + "/",
)

DENY_RULE = {
    "deny_hooks": ("GRD-006", "--no-verify is refused: git hooks and Crewline gates must run"),
    "deny_force": ("GRD-002", "force-push is disabled in this version"),
    "deny_destructive": ("GRD-002", "hard reset / git clean -f is refused: never discard foreign or uncommitted work"),
    "deny_stash": ("GRD-002", "git stash is refused: never stash another person's uncommitted work"),
    "deny_delete": ("GRD-002", "deleting branches is disabled in this version"),
    "deny_merge": ("GRD-002", "merging the PR is a human action; the agent does not merge"),
    "deny_prod": ("GRD-002", "production deploy is disabled in this version"),
}


def find_active_manifest(tasks_dir: Path | None = None) -> Path | None:
    env = os.environ.get("CREWLINE_TASK_MANIFEST", "").strip()
    if env:
        p = Path(env)
        return p if p.is_file() else None
    root = Path(tasks_dir or TASKS)
    if not root.is_dir():
        return None
    found: list[tuple[float, Path]] = []
    for p in root.glob("*/task-manifest.json"):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if doc.get("current_state") in TERMINAL or doc.get("outcome") in TERMINAL_OUTCOMES:
            continue
        found.append((p.stat().st_mtime, p))
    return max(found)[1] if found else None


def classify_shell(command: str) -> str:
    """Map a shell command to a guard action: deny_*, commit, push, pr, other."""
    text = (command or "").strip()
    if not text:
        return "other"
    low = text.lower()
    if re.search(r"(^|\s)--no-verify(\s|$)", low):
        return "deny_hooks"
    git = bool(re.search(r"(^|[\s;&|])git(\.exe)?\s", low + " ") or low.startswith("git ") or low.startswith("git.exe "))
    if git and re.search(r"\bpush\b", low) and re.search(r"(^|\s)(-f|--force|--force-with-lease)(\s|$)", low):
        return "deny_force"
    if git and re.search(r"\breset\b", low) and re.search(r"--hard", low):
        return "deny_destructive"
    if git and re.search(r"\bclean\b", low) and re.search(r"(^|\s)-[a-z]*f", low):
        return "deny_destructive"
    if git and re.search(r"\bstash\b", low):
        return "deny_stash"
    if git and re.search(r"\bbranch\b", low) and re.search(r"(^|\s)-[dD]\b", low):
        return "deny_delete"
    if re.search(r"\bgh(\.exe)?\s+pr\s+merge\b", low):
        return "deny_merge"
    if re.search(r"\b(helm|kubectl)\b", low) and re.search(r"\b(prod|production|live)\b", low):
        return "deny_prod"
    if git and re.search(r"\bcommit\b", low):
        return "commit"
    if git and re.search(r"\bpush\b", low):
        return "push"
    if re.search(r"\bgh(\.exe)?\s+pr\s+create\b", low):
        return "pr"
    return "other"


def has_signoff(command: str) -> bool:
    if re.search(r"(^|\s)--signoff(\s|$)", command):
        return True
    for tok in command.split():
        if tok in ("-s", "--signoff"):
            return True
        if tok.startswith("-") and not tok.startswith("--") and "s" in tok[1:]:
            return True
    return False


def _load(manifest_path: str) -> dict:
    return json.loads(Path(manifest_path).read_text(encoding="utf-8"))


def _need_task(res: Result, manifest_path: str | None, action: str) -> dict | None:
    if not manifest_path:
        res.add("GRD-001", BLOCK, f"{action} needs an active Crewline task (tasks/<id>/task-manifest.json)",
                remediation="INTAKE: create the manifest first, or set CREWLINE_TASK_MANIFEST")
        return None
    try:
        return _load(manifest_path)
    except (OSError, json.JSONDecodeError) as e:
        res.add("GRD-001", BLOCK, f"cannot read task manifest {manifest_path}: {e}")
        return None


def check_shell(command: str, manifest_path: str | None = None) -> Result:
    res = Result("guard", inputs={"command": command, "manifest": manifest_path or ""})
    action = classify_shell(command)
    res.inputs["action"] = action
    if action.startswith("deny_"):
        rule, msg = DENY_RULE[action]
        res.add(rule, BLOCK, msg, evidence=command)
        return res.finish()
    if action == "other":
        return res.finish()
    if action == "commit" and not has_signoff(command):
        res.add("GRD-005", BLOCK, "git commit must be signed off (`git commit -s`)", evidence=command)
        return res.finish()
    doc = _need_task(res, manifest_path, action)
    if doc is None:
        return res.finish()
    state = doc.get("current_state")
    if action == "commit":
        if state not in COMMIT_STATES:
            res.add("GRD-003", BLOCK, f"git commit is only allowed at QUALITY_GATE or COMMIT_PR, not {state}",
                    remediation="finish reviews, system tests and quality_gate; then crewline manifest --to COMMIT_PR")
            return res.finish()
        gate = transition(manifest_path, "COMMIT_PR") if state == "QUALITY_GATE" else check(manifest_path)
        return _merge(res, gate, "commit refused until COMMIT_PR gates pass")
    if action in ("push", "pr"):
        if state not in PUSH_STATES:
            res.add("GRD-003", BLOCK, f"{action} is only allowed at COMMIT_PR or PR_CLOSEOUT, not {state}",
                    remediation="record approval push_and_pr and pass dco / branch_scope / change_scope")
            return res.finish()
        if state == "COMMIT_PR":
            return _merge(res, transition(manifest_path, "PR_CLOSEOUT"), "push/PR refused until COMMIT_PR->PR_CLOSEOUT guards pass")
        return res.finish()
    return res.finish()


def _merge(res: Result, other: Result, prefix: str) -> Result:
    res.inputs["inner"] = other.validator
    for f in other.findings:
        if f.severity == BLOCK and not f.approved_by:
            res.add(f.rule_id, BLOCK, f"{prefix}: {f.message}", path=f.path, evidence=f.evidence,
                    remediation=f.remediation)
    return res.finish()


def _rel_repo_path(path: str, cwd: str | None = None) -> str:
    p = Path(path)
    if not p.is_absolute() and cwd:
        p = Path(cwd) / p
    try:
        p = p.resolve()
    except OSError:
        p = Path(path)
    text = str(p).replace("\\", "/")
    lower = text.lower()
    for prefix in ALWAYS_ALLOW_WRITE_PREFIXES:
        if lower.startswith(prefix) or lower.startswith(prefix.rstrip("/")):
            return ""  # empty => always allowed (task workspace)
    # Prefer a path relative to cwd / git top so approved_paths globs match.
    root = Path(cwd).resolve() if cwd else p.parent
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return p.name


def check_write(path: str, manifest_path: str | None = None, cwd: str | None = None) -> Result:
    res = Result("guard", inputs={"path": path, "manifest": manifest_path or ""})
    rel = _rel_repo_path(path, cwd)
    if rel == "":
        return res.finish()
    if not manifest_path:
        return res.finish()  # drafting without a task is allowed; shipping is not
    try:
        doc = _load(manifest_path)
    except (OSError, json.JSONDecodeError) as e:
        res.add("GRD-001", BLOCK, f"cannot read task manifest: {e}")
        return res.finish()
    approved = doc.get("scope", {}).get("approved_paths") or []
    grants = [a for a in doc.get("approvals", []) if a.get("action") == "scope_change"
              and all(a.get(k) for k in ("approver", "reason", "scope", "timestamp"))]

    def granted(item: str) -> str | None:
        for a in grants:
            for g in str(a.get("scope", "")).replace(",", " ").split():
                if _match(item, g):
                    return a["approver"]
        return None

    if not approved:
        if any(_match(rel, s) for s in ("src/**", "**/src/**", "api-test/**", "helm/**",
                                         "db_upgrade_scripts/**", ".github/**")):
            res.add("GRD-004", BLOCK, f"{rel} has no scope.approved_paths yet (plan first)",
                    path=rel, remediation="IMPLEMENTATION_PLAN must list approved_paths before module edits")
        return res.finish()
    if not any(_match(rel, p) for p in approved):
        f = res.add("GRD-004", BLOCK, f"{rel} is outside scope.approved_paths", path=rel,
                    remediation="impact analysis + approval scope_change naming the file")
        f.approved_by = granted(rel)
    if any(_match(rel, s) for s in SENSITIVE) and not granted(rel):
        f = res.add("GRD-004", BLOCK, f"{rel} is a CI/build/deploy/config file (needs scope_change)", path=rel)
        f.approved_by = granted(rel)
    return res.finish()


def run(kind: str, target: str, manifest_path: str | None = None, cwd: str | None = None) -> Result:
    if kind == "shell":
        return check_shell(target, manifest_path)
    if kind == "write":
        return check_write(target, manifest_path, cwd)
    return Result.not_run("guard", f"unknown kind {kind!r}")

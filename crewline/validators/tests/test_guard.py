"""Platform guard rails (ADR-0007, GRD-001..006)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from crewline import guard, hook, manifest

ROOT = Path(__file__).resolve().parents[2]
HUMAN = {"approver": "mohan", "reason": "r", "scope": "s", "timestamp": "2026-10-28T00:00:00Z"}


def ids(res):
    return {f.rule_id for f in res.findings}


def write_manifest(tmp_path, **over):
    d = {
        "task_id": "t-g", "task_type": "documentation", "risk_tier": "L2", "outcome": "IN_PROGRESS",
        "current_state": "QUALITY_GATE",
        "scope": {"module": "svc", "repositories": [], "approved_paths": ["docs/**", "README.md"]},
        "requirements": {"source_refs": [], "acceptance_criteria": [], "open_ambiguities": 0},
        "testcases": {"canonical_format": "none"},
        "repair": {"attempt_count": 0, "dev_attempt_count": 0, "attempt_history": [], "classification": ""},
        "reviews": {"implementation_review": "PASS", "fresh_context_review": "PASS"},
        "gates": [{"gate": g, "status": "PASS"} for g in
                  ("quality_gate", "deterministic_validation", "change_scope", "secrets", "token_budget")],
        "approvals": [{"action": "commit_pr", **HUMAN}],
        "evidence_refs": [],
        "github": {"issue": None, "subtasks": [], "pull_request": None},
        "test_plan": {"environment": "n/a", "environment_kind": "local-stack"},
    }
    d.update(over)
    p = tmp_path / "task-manifest.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("command,action", [
    ("git commit -s -m MOSIP-1", "commit"),
    ("git commit -sm MOSIP-1", "commit"),
    ("git push origin HEAD", "push"),
    ("gh pr create --title x", "pr"),
    ("git push --force origin HEAD", "deny_force"),
    ("git push -f", "deny_force"),
    ("git reset --hard HEAD~1", "deny_destructive"),
    ("git stash", "deny_stash"),
    ("git branch -D tmp", "deny_delete"),
    ("gh pr merge 12", "deny_merge"),
    ("helm upgrade x chart -n production", "deny_prod"),
    ("git commit -s --no-verify -m x", "deny_hooks"),
    ("mvn -B test", "other"),
])
def test_classify_shell(command, action):
    assert guard.classify_shell(command) == action


def test_unsigned_commit_is_blocked():
    res = guard.check_shell("git commit -m skip-signoff")
    assert res.status == "FAIL" and "GRD-005" in ids(res)


def test_commit_without_task_is_blocked():
    res = guard.check_shell("git commit -s -m MOSIP-1", None)
    assert res.status == "FAIL" and "GRD-001" in ids(res)


def test_commit_before_quality_gate_is_blocked(tmp_path):
    m = write_manifest(tmp_path, current_state="IMPLEMENTATION")
    res = guard.check_shell("git commit -s -m MOSIP-1", m)
    assert res.status == "FAIL" and "GRD-003" in ids(res)


def test_signed_commit_at_quality_gate_passes_when_template_gates_pass(tmp_path):
    m = write_manifest(tmp_path)
    assert manifest.transition(m, "COMMIT_PR").status == "PASS"
    assert guard.check_shell("git commit -s -m MOSIP-1 docs", m).status == "PASS"


def test_force_push_always_denied(tmp_path):
    m = write_manifest(tmp_path, current_state="COMMIT_PR",
                       approvals=[{"action": "commit_pr", **HUMAN}, {"action": "push_and_pr", **HUMAN}],
                       gates=[{"gate": g, "status": "PASS"} for g in
                              ("quality_gate", "deterministic_validation", "change_scope", "secrets",
                               "dco", "branch_scope")])
    res = guard.check_shell("git push --force origin HEAD", m)
    assert res.status == "FAIL" and "GRD-002" in ids(res)


def test_write_outside_approved_paths_blocked(tmp_path):
    m = write_manifest(tmp_path, current_state="IMPLEMENTATION")
    res = guard.check_write("src/main/java/X.java", m, cwd=str(tmp_path))
    assert res.status == "FAIL" and "GRD-004" in ids(res)
    assert guard.check_write("docs/guide.md", m, cwd=str(tmp_path)).status == "PASS"


def test_write_without_task_is_allowed():
    assert guard.check_write("src/main/java/X.java", None).status == "PASS"


def test_hook_denies_force_push_json():
    out = hook.handle("shell", {"command": "git push --force"})
    assert out["permission"] == "deny"
    assert "GRD-002" in out["agent_message"]


def test_hook_claude_protocol_and_bash_payload():
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": "git push --force origin HEAD"}}
    cursor = hook.handle("shell", payload)
    claude = hook.to_claude(cursor, "PreToolUse")
    assert claude["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "GRD-002" in claude["hookSpecificOutput"]["permissionDecisionReason"]
    assert hook.detect_protocol(payload, False) == "claude"
    assert hook.detect_mode(payload) == "shell"


def test_hook_session_injects_context():
    out = hook.handle("session", {})
    assert "Crewline hooks are active" in out["additional_context"]


def test_git_hook_exit_denies_commit_without_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CREWLINE_TASK_MANIFEST", raising=False)
    assert hook.git_exit("git-commit", []) == 1
    assert hook.git_exit("git-push", []) == 1


def test_cli_guard_shell():
    proc = subprocess.run(
        [sys.executable, "-m", "crewline", "--json", "guard", "--shell", "git stash"],
        cwd=str(ROOT / "validators"), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["status"] == "FAIL"


def _install(tmp_path, platform):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "adapters" / "install.py"), "--platform", platform,
         "--target", str(tmp_path), "--write"],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc


def test_install_cursor_writes_hooks(tmp_path):
    _install(tmp_path, "cursor")
    hooks = json.loads((tmp_path / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    assert hooks["hooks"]["beforeShellExecution"][0]["failClosed"] is True
    trampoline = (tmp_path / ".cursor" / "hooks" / "crewline_hook.py").read_text(encoding="utf-8")
    assert "{{CORE}}" not in trampoline
    mdc = (tmp_path / ".cursor" / "rules" / "crewline.mdc").read_text(encoding="utf-8")
    assert "alwaysApply: true" in mdc


def test_install_claude_writes_hooks_and_deny_rules(tmp_path):
    _install(tmp_path, "claude")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    deny = settings["permissions"]["deny"]
    assert "Bash(git push --force *)" in deny
    matchers = [g.get("matcher") for g in settings["hooks"]["PreToolUse"]]
    assert "Bash" in matchers and "Write|Edit" in matchers
    skill = (tmp_path / ".claude" / "skills" / "crewline" / "SKILL.md").read_text(encoding="utf-8")
    assert "{{CORE}}" not in skill
    assert "crewline guard" in skill
    trampoline = (tmp_path / ".claude" / "hooks" / "crewline_hook.py").read_text(encoding="utf-8")
    assert "{{CORE}}" not in trampoline


def test_install_sync_rewrites_drift(tmp_path):
    _install(tmp_path, "cursor")
    mdc = tmp_path / ".cursor" / "rules" / "crewline.mdc"
    mdc.write_text("# tampered\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "adapters" / "install.py"), "--platform", "cursor",
         "--target", str(tmp_path), "--sync", "--check"],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "# tampered" not in mdc.read_text(encoding="utf-8")


def test_install_check_detects_drift(tmp_path):
    _install(tmp_path, "cursor")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "adapters" / "install.py"), "--platform", "cursor",
         "--target", str(tmp_path), "--check"],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    mdc = tmp_path / ".cursor" / "rules" / "crewline.mdc"
    mdc.write_text(mdc.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "adapters" / "install.py"), "--platform", "cursor",
         "--target", str(tmp_path), "--check"],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode != 0 and "drift" in (proc.stdout + proc.stderr)


def test_install_generic_writes_git_hooks(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _install(tmp_path, "generic")
    entry = (tmp_path / ".crewline" / "ENTRY.md").read_text(encoding="utf-8")
    assert "{{CORE}}" not in entry
    assert "crewline guard" in entry
    pre = (tmp_path / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "git-commit" in pre
    assert "{{HOOK}}" not in pre
    assert (tmp_path / ".crewline" / "hooks" / "crewline_hook.py").is_file()

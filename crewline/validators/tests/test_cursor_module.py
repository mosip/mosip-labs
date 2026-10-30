"""Cursor without a Crewline clone: the module's .cursor/crewline.py bootstrap (templates/module-cursor/)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]                 # .../crewline
TPL = ROOT / "templates" / "module-cursor"
FAKE_CLI = ("import json, sys\n"
            "print(json.dumps({'args': sys.argv[1:], 'stdin': sys.stdin.read(), 'v': VERSION}))\n")


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout


def commit(cwd, msg):
    git(cwd, "add", "-A")
    git(cwd, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", msg)


def source_repo(tmp_path, version="1"):
    """A stand-in for mosip-labs: crewline/validators/crewline_cli.py echoes what it was given."""
    src = tmp_path / "labs"
    (src / "crewline/validators").mkdir(parents=True)
    (src / "crewline/validators/crewline_cli.py").write_text(f"VERSION = {version!r}\n" + FAKE_CLI, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "develop", str(src)], check=True)
    commit(src, "v" + version)
    return src


def module(tmp_path, onboarded=True):
    m = tmp_path / "module"
    (m / ".cursor").mkdir(parents=True)
    shutil.copy(TPL / "crewline.py", m / ".cursor" / "crewline.py")
    subprocess.run(["git", "init", "-q", str(m)], check=True)
    if onboarded:
        (m / ".crewline").mkdir()
        (m / ".crewline/module.yaml").write_text("module: mod\nroles:\n  development: []\n", encoding="utf-8")
    commit(m, "init") if any(m.iterdir()) else None
    return m


def run(m, args, env, stdin=""):
    e = {k: v for k, v in os.environ.items() if not k.startswith("CREWLINE")}
    e.update(env)
    return subprocess.run([sys.executable, str(m / ".cursor" / "crewline.py"), *args], input=stdin,
                          capture_output=True, text=True, env=e, cwd=str(m))


def test_fetches_once_caches_and_refreshes_when_due(tmp_path):
    src = source_repo(tmp_path)
    m = module(tmp_path)
    env = {"CREWLINE_SOURCE": str(src), "CREWLINE_HOME": str(tmp_path / "home")}
    where = run(m, ["where"], env)
    assert where.returncode == 0 and where.stdout.strip().endswith("crewline")
    out = json.loads(run(m, ["hook", "shell"], env, '{"command": "ls"}').stdout)
    assert out["args"] == ["hook", "--cursor", "--plugin", "shell"] and out["stdin"] == '{"command": "ls"}'
    assert out["v"] == "1"
    (src / "crewline/validators/crewline_cli.py").write_text("VERSION = '2'\n" + FAKE_CLI, encoding="utf-8")
    commit(src, "v2")
    assert json.loads(run(m, ["hook", "shell"], env, "{}").stdout)["v"] == "1"                # within a day: cached copy
    env["CREWLINE_REFRESH_SECONDS"] = "0"
    assert json.loads(run(m, ["hook", "shell"], env, "{}").stdout)["v"] == "2"                # due: refreshed
    exclude = (m / ".git/info/exclude").read_text(encoding="utf-8")
    assert ".cursor/crewline.local.json" in exclude and ".crewline-work/" in exclude


def test_offline_never_blocks(tmp_path):
    m = module(tmp_path)
    env = {"CREWLINE_SOURCE": str(tmp_path / "missing"), "CREWLINE_HOME": str(tmp_path / "home")}
    assert json.loads(run(m, ["hook", "shell"], env, '{"command": "git status"}').stdout) == {"permission": "allow"}
    assert "could not be fetched" in json.loads(run(m, ["hook", "session"], env, "{}").stdout)["additional_context"]
    assert run(m, ["where"], env).returncode == 2


def test_off_switches(tmp_path):
    src = source_repo(tmp_path)
    m = module(tmp_path)
    env = {"CREWLINE_SOURCE": str(src), "CREWLINE_HOME": str(tmp_path / "home")}
    assert json.loads(run(m, ["hook", "shell"], {**env, "CREWLINE": "off"}, "{}").stdout) == {"permission": "allow"}
    (m / ".cursor/crewline.local.json").write_text('{"enabled": false}', encoding="utf-8")
    assert json.loads(run(m, ["hook", "shell"], env, "{}").stdout) == {"permission": "allow"}
    assert not (tmp_path / "home/cache").exists() or not any((tmp_path / "home/cache").iterdir())   # nothing fetched


def test_local_file_selects_source_and_ref(tmp_path):
    src = source_repo(tmp_path)
    git(src, "switch", "-q", "-c", "feature")
    (src / "crewline/validators/crewline_cli.py").write_text("VERSION = 'feature'\n" + FAKE_CLI, encoding="utf-8")
    commit(src, "feature")
    m = module(tmp_path)
    (m / ".cursor/crewline.local.json").write_text(json.dumps({"source": str(src), "ref": "feature"}), encoding="utf-8")
    out = run(m, ["hook", "shell"], {"CREWLINE_HOME": str(tmp_path / "home")}, "{}")
    assert json.loads(out.stdout)["v"] == "feature"


def test_broken_core_asks_instead_of_blocking(tmp_path):
    src = source_repo(tmp_path)
    (src / "crewline/validators/crewline_cli.py").write_text("raise SystemExit('No module named yaml')\n", encoding="utf-8")
    commit(src, "broken")
    m = module(tmp_path)
    out = json.loads(run(m, ["hook", "shell"], {"CREWLINE_SOURCE": str(src), "CREWLINE_HOME": str(tmp_path / "home")},
                         "{}").stdout)
    assert out["permission"] == "ask" and "pyyaml" in out["user_message"]


def test_real_guard_through_cursor_payloads(tmp_path):
    """With the real Crewline core: Cursor payloads (which also carry hook_event_name) get Cursor-format answers."""
    m = module(tmp_path)
    env = {"CREWLINE_CORE": str(ROOT)}
    shell = {"hook_event_name": "beforeShellExecution", "command": "git push --force origin HEAD", "cwd": str(m)}
    out = json.loads(run(m, ["hook", "shell"], env, json.dumps(shell)).stdout)
    assert out["permission"] == "deny" and "GRD-002" in out["agent_message"]
    ok = {"hook_event_name": "beforeShellExecution", "command": "git status", "cwd": str(m)}
    assert json.loads(run(m, ["hook", "shell"], env, json.dumps(ok)).stdout)["permission"] == "allow"
    ctx = json.loads(run(m, ["hook", "session"], env, json.dumps({"hook_event_name": "sessionStart", "cwd": str(m)})).stdout)
    assert "Crewline is ACTIVE" in ctx["additional_context"] and "crewline.py rule" in ctx["additional_context"]
    rule = run(m, ["rule"], env)
    assert rule.returncode == 0 and "{{CORE}}" not in rule.stdout and "python -m crewline" not in rule.stdout
    assert "python .cursor/crewline.py manifest" in rule.stdout


def test_real_guard_leaves_other_repos_alone(tmp_path):
    m = module(tmp_path, onboarded=False)
    shell = {"hook_event_name": "beforeShellExecution", "command": "git push --force", "cwd": str(m)}
    out = json.loads(run(m, ["hook", "shell"], {"CREWLINE_CORE": str(ROOT)}, json.dumps(shell)).stdout)
    assert out["permission"] == "allow"


def test_module_templates_are_portable():
    hooks = json.loads((TPL / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    commands = [h["command"] for group in hooks.values() for h in group]
    assert commands and all(c.startswith("python .cursor/crewline.py hook ") for c in commands)
    assert all(h.get("failClosed") for h in hooks["beforeShellExecution"] + hooks["preToolUse"])
    rule = (TPL / "crewline.mdc").read_text(encoding="utf-8")
    assert "alwaysApply: true" in rule and "{{CORE}}" not in rule and ":/" not in rule
    boot = (TPL / "crewline.py").read_text(encoding="utf-8")
    assert "import yaml" not in boot and 'SOURCE = "https://github.com/mosip/mosip-labs.git"' in boot

"""SessionStart hook: tell the assistant whether Crewline applies to the repository the session opened in.

  crewline session-start        (run by hooks/hooks.json; reads CLAUDE_PROJECT_DIR, prints hook JSON, always exits 0)

- `.crewline/` present            -> Crewline is active: follow the crewline skill, read the module's context
- plugin enabled, no `.crewline/` -> say so once and offer `module-onboarding`; do not change behaviour otherwise
- CREWLINE=off in the environment -> silent (one-session opt-out)
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml


def repo_top(start: Path) -> Path:
    r = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8")
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else start


def context(project_dir: str | None = None, env: dict | None = None) -> str | None:
    env = os.environ if env is None else env
    if str(env.get("CREWLINE", "")).lower() in ("off", "0", "false", "disabled"):
        return None
    top = repo_top(Path(project_dir or env.get("CLAUDE_PROJECT_DIR") or os.getcwd()))
    cl = top / ".crewline"
    if not cl.is_dir():
        return ("Crewline is enabled here, but this repository has no .crewline/ folder yet. Work normally; if the user asks "
                "for a Crewline task, start with the module-onboarding task (crewline skill) to create .crewline/.")
    module, roles = top.name, []
    idx = cl / "module.yaml"
    if idx.is_file():
        try:
            data = yaml.safe_load(idx.read_text(encoding="utf-8")) or {}
            module = data.get("module", module)
            roles = list((data.get("roles") or {}).keys())
        except yaml.YAMLError:
            pass
    roles = roles or sorted(p.name for p in cl.iterdir() if p.is_dir())
    return (f"Crewline is ACTIVE for this repository (module {module}; context in .crewline/: {', '.join(roles) or 'no role folders'}). "
            "For any change to this repository (feature, bug fix, refactor, upgrade, migration, test automation, release, docs), "
            "use the crewline skill workflow: classify the task, create the manifest in .crewline-work/tasks/<task-id>/, ask the "
            "upstream base branch before branching, delegate to the Crewline role agents, run the `crewline` validators, and ask "
            "the user for every commit, push, PR and bug. Read .crewline/README.md first; the repository's own AGENTS.md / "
            "CLAUDE.md win where they are more specific. Questions and read-only explanations need no task. The user can turn "
            "Crewline off for this repository in .claude/settings.local.json (\"enabledPlugins\": {\"crewline@mosip-labs\": false}) "
            "or for one session with CREWLINE=off.")


def run() -> int:
    try:
        text = context()
    except Exception:  # a hook must never break the session
        text = None
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
    return 0

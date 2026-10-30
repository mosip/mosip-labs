"""Where a task's records live.

- CREWLINE_TASKS=<dir>                        explicit (tests, CI)
- a repository with a `.crewline/` folder    <main clone>/.crewline-work/tasks/  (also from inside a task worktree:
                                              the main clone is found through git's common dir, so one clone has one
                                              task list)
- anything else (a Crewline clone)            <core>/tasks/
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

CORE = Path(__file__).resolve().parents[2]


def _git(start: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(start), *args], capture_output=True, text=True, encoding="utf-8", timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def module_top(cwd: str | os.PathLike | None = None) -> Path | None:
    """The repository root when it carries `.crewline/` (Crewline is active there), else None."""
    start = Path(cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if not start.is_dir():
        start = start.parent
    top = _git(start, "rev-parse", "--show-toplevel")
    if top and (Path(top) / ".crewline").is_dir():
        return Path(top)
    return None


def main_clone(top: Path) -> Path:
    common = _git(top, "rev-parse", "--path-format=absolute", "--git-common-dir")
    p = Path(common) if common else None
    return p.parent if p and p.name == ".git" else top


def tasks_root(cwd: str | os.PathLike | None = None) -> Path:
    env = os.environ.get("CREWLINE_TASKS")
    if env:
        return Path(env)
    top = module_top(cwd)
    return main_clone(top) / ".crewline-work" / "tasks" if top else CORE / "tasks"


def disabled(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return str(env.get("CREWLINE", "")).lower() in ("off", "0", "false", "disabled")

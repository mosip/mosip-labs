"""The Crewline rule for Cursor, rendered for a module that runs Crewline through .cursor/crewline.py.

  python .cursor/crewline.py rule        (calls `crewline cursor-rule`)

The module commits only a short, stable rule (templates/module-cursor/crewline.mdc) that tells the agent to run this; the
workflow itself comes from the cached Crewline core, so it changes when Crewline is updated, not when the module is.
"""
from __future__ import annotations

from pathlib import Path

CORE = Path(__file__).resolve().parents[2]


def render(core: Path = CORE) -> str:
    text = (core / "adapters" / "cursor" / "crewline.mdc").read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2].lstrip("\n")
    text = text.replace("{{CORE}}", core.as_posix())
    text = text.replace("python -m crewline", "python .cursor/crewline.py")
    text = text.replace("(from `" + core.as_posix() + "/validators`)", "")
    text = text.replace("Fail-closed hooks (`.cursor/hooks.json`) call `python .cursor/crewline.py guard`",
                        "Fail-closed hooks (`.cursor/hooks.json`, through `.cursor/crewline.py`) run the Crewline guard")
    try:
        import json
        version = json.loads((core / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version", "")
    except (OSError, ValueError):
        version = ""
    head = (f"# Crewline {version} for this repository (Cursor)\n\n"
            f"Crewline core (cached, read-only): `{core.as_posix()}`. Task records: `<clone>/.crewline-work/tasks/<id>/`, "
            "worktrees `<clone>/.crewline-work/worktrees/<id>` (both excluded from git).\n\n")
    return head + text


def run() -> int:
    print(render())
    return 0

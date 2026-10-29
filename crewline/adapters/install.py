"""Render the thin platform adapters into a target workspace.

  python adapters/install.py --platform claude|cursor --target <workspace dir>   # dry run: prints the plan
  python adapters/install.py --platform claude --target <dir> --write             # writes files

Claude: <target>/.claude/skills/crewline/SKILL.md and <target>/.claude/agents/crewline-<agent>.md
Cursor: <target>/.cursor/rules/crewline.mdc
Existing files are never overwritten unless --force is given.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]
CLAUDE_TOOLS = {  # core/permissions.yaml profile -> Claude Code tool allow-list
    "read-only": "Read, Grep, Glob",
    "analysis": "Read, Grep, Glob, Bash",
    "workspace-write": "Read, Grep, Glob, Bash, Edit, Write",
}


def render(text: str) -> str:
    return text.replace("{{CORE}}", CORE.as_posix())


def agent_files():
    for p in sorted((CORE / "agents").rglob("*.md")):      # role folders: product/, ui-ux/, development/, qa/ ...
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):                     # agents/README.md (role map) is not a contract
            continue
        fm = dict(re.findall(r"^(\w+):\s*(.+)$", text.split("---")[1], re.M))
        profile = fm.get("permission_profile", "read-only").split()[0]
        body = text.split("---", 2)[2].lstrip()
        header = (f"---\nname: crewline-{fm['name']}\ndescription: {json.dumps(fm['description'], ensure_ascii=False)}\n"
                  f"tools: {CLAUDE_TOOLS.get(profile, CLAUDE_TOOLS['read-only'])}\n---\n\n")
        note = f"Core: `{CORE.as_posix()}` (contracts, workflow, validators).\n\n"
        yield f"crewline-{fm['name']}.md", header + note + body


def plan(platform: str, target: Path):
    if platform == "claude":
        yield target / ".claude/skills/crewline/SKILL.md", render((CORE / "adapters/claude/SKILL.md").read_text(encoding="utf-8"))
        for name, text in agent_files():
            yield target / ".claude/agents" / name, text
    else:
        yield target / ".cursor/rules/crewline.mdc", render((CORE / "adapters/cursor/crewline.mdc").read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", choices=["claude", "cursor"], required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for path, text in plan(a.platform, Path(a.target).resolve()):
        exists = path.exists()
        action = "skip (exists)" if exists and not a.force else ("write" if a.write else "would write")
        print(f"{action:14} {path}")
        if a.write and (not exists or a.force):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

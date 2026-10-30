"""Render the thin platform adapters into a target workspace (for tools without plugin support; Claude Code users
should prefer the plugin: see README "Turn Crewline on for a module").

  python adapters/install.py --platform claude|cursor|generic --target <workspace dir>
  python adapters/install.py --platform claude --target <dir> --write
  python adapters/install.py --platform cursor --target <dir> --check   # fail if installed files drifted
  python adapters/install.py --platform cursor --target <dir> --sync    # write --force (idempotent re-render)

Claude: skill, crewline-* subagents, .claude/settings.json hooks + deny rules, .claude/hooks/crewline_hook.py
Cursor: .cursor/rules/crewline.mdc, .cursor/hooks.json, .cursor/hooks/crewline_hook.py
Generic: .crewline/ENTRY.md and git hooks (pre-commit / commit-msg / pre-push) that call `crewline guard`
Existing files are never overwritten unless --force is given. Claude settings.json is merged on --force.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]
HOOK_PY = CORE / "adapters/hooks/crewline_hook.py"
CLAUDE_TOOLS = {  # core/permissions.yaml profile -> Claude Code tool allow-list
    "read-only": "Read, Grep, Glob",
    "analysis": "Read, Grep, Glob, Bash",
    "workspace-write": "Read, Grep, Glob, Bash, Edit, Write",
}


def render(text: str) -> str:
    return text.replace("{{CORE}}", CORE.as_posix()).replace("${CLAUDE_PLUGIN_ROOT}", CORE.as_posix())


def python_cmd(*, posix: bool = False) -> str:
    exe = Path(sys.executable).resolve()
    s = exe.as_posix() if posix else str(exe)
    return f'"{s}"' if " " in s else s


def render_json_template(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8").replace("{{PYTHON}}", "PYTHON_PLACEHOLDER"))

    def fix(obj):
        if isinstance(obj, dict):
            return {k: fix(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [fix(v) for v in obj]
        if isinstance(obj, str):
            return obj.replace("PYTHON_PLACEHOLDER", python_cmd())
        return obj

    return json.dumps(fix(data), indent=2) + "\n"


def merge_claude_settings(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    hooks = dict(out.get("hooks") or {})
    hooks.update(incoming.get("hooks") or {})
    out["hooks"] = hooks
    perms = dict(out.get("permissions") or {})
    deny = list(perms.get("deny") or [])
    for rule in (incoming.get("permissions") or {}).get("deny") or []:
        if rule not in deny:
            deny.append(rule)
    if deny:
        perms["deny"] = deny
        out["permissions"] = perms
    return out


def executable(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def git_hooks_dir(target: Path) -> Path | None:
    git = target / ".git"
    if git.is_dir():
        return git / "hooks"
    if git.is_file():
        text = git.read_text(encoding="utf-8").strip()
        if text.lower().startswith("gitdir:"):
            real = Path(text.split(":", 1)[1].strip())
            if not real.is_absolute():
                real = (target / real).resolve()
            return real / "hooks"
    return None


def git_hook(name: str, hook_py: Path) -> str:
    raw = (CORE / "adapters/generic/git-hooks" / name).read_text(encoding="utf-8")
    return raw.replace("{{PYTHON}}", python_cmd(posix=True)).replace("{{HOOK}}", hook_py.as_posix())


def agent_files():
    for p in sorted((CORE / "agents").rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):                     # docs/agents-by-role.md (role map) is not a contract
            continue
        fm = dict(re.findall(r"^(\w+):\s*(.+)$", text.split("---")[1], re.M))
        profile = fm.get("permission_profile", "read-only").split()[0]
        body = text.split("---", 2)[2].lstrip()
        header = (f"---\nname: crewline-{fm['name']}\ndescription: {json.dumps(fm['description'], ensure_ascii=False)}\n"
                  f"tools: {CLAUDE_TOOLS.get(profile, CLAUDE_TOOLS['read-only'])}\n---\n\n")
        yield f"crewline-{fm['name']}.md", header + render(body)


def plan(platform: str, target: Path):
    trampoline = render(HOOK_PY.read_text(encoding="utf-8"))
    if platform == "claude":
        yield target / ".claude/skills/crewline/SKILL.md", render((CORE / "skills/crewline/SKILL.md").read_text(encoding="utf-8"))
        for name, text in agent_files():
            yield target / ".claude/agents" / name, text
        yield target / ".claude/hooks/crewline_hook.py", trampoline
        yield target / ".claude/settings.json", render_json_template(CORE / "adapters/claude/settings.json")
    elif platform == "cursor":
        yield target / ".cursor/rules/crewline.mdc", render((CORE / "adapters/cursor/crewline.mdc").read_text(encoding="utf-8"))
        yield target / ".cursor/hooks.json", render_json_template(CORE / "adapters/cursor/hooks.json")
        yield target / ".cursor/hooks/crewline_hook.py", trampoline
    elif platform == "generic":
        yield target / ".crewline/ENTRY.md", render((CORE / "adapters/generic/ENTRY.md").read_text(encoding="utf-8"))
        hook_py = target / ".crewline/hooks/crewline_hook.py"
        yield hook_py, trampoline
        for name in ("pre-commit", "commit-msg", "pre-push"):
            body = executable(git_hook(name, hook_py))
            yield target / ".crewline/git-hooks" / name, body
            hooks_dir = git_hooks_dir(target)
            if hooks_dir is not None:
                yield hooks_dir / name, body
    else:
        raise ValueError(f"unknown platform {platform}")


def chmod_hook(path: Path) -> None:
    if path.parent.name in ("hooks", "git-hooks") or path.name in ("pre-commit", "commit-msg", "pre-push"):
        try:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass


def write_file(path: Path, text: str, force: bool) -> str:
    exists = path.exists()
    if exists and not force:
        if path.name == "settings.json" and path.parent.name == ".claude":
            return "skip (exists)"
        return "skip (exists)"
    action = "write"
    path.parent.mkdir(parents=True, exist_ok=True)
    if exists and path.name == "settings.json" and path.parent.name == ".claude":
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        text = json.dumps(merge_claude_settings(existing, json.loads(text)), indent=2) + "\n"
        action = "merge"
    path.write_text(text, encoding="utf-8", newline="\n")
    chmod_hook(path)
    return action


def check(platform: str, target: Path) -> list[str]:
    """Return drift/missing messages. Empty means the install matches adapters/."""
    errors: list[str] = []
    for path, text in plan(platform, target):
        if not path.exists():
            errors.append(f"missing {path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if path.name == "settings.json" and path.parent.name == ".claude":
            try:
                have, want = json.loads(actual), json.loads(text)
            except json.JSONDecodeError:
                errors.append(f"drift {path} (not JSON)")
                continue
            deny_have = (have.get("permissions") or {}).get("deny") or []
            deny_want = (want.get("permissions") or {}).get("deny") or []
            missing_deny = [r for r in deny_want if r not in deny_have]
            if missing_deny:
                errors.append(f"drift {path}: missing deny {missing_deny}")
            continue
        if actual.replace("\r\n", "\n") != text.replace("\r\n", "\n"):
            errors.append(f"drift {path}")
    return errors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", choices=["claude", "cursor", "generic"], required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true", help="exit 1 if installed files are missing or differ from adapters/")
    ap.add_argument("--sync", action="store_true", help="write --force: re-render from adapters/ (idempotent)")
    a = ap.parse_args()
    target = Path(a.target).resolve()
    if a.sync:
        a.write = True
        a.force = True
    if a.check and not a.sync:
        errors = check(a.platform, target)
        if errors:
            print("\n".join(errors))
            sys.exit(1)
        print("ok")
        return
    for path, text in plan(a.platform, target):
        if not a.write:
            exists = path.exists()
            print(f"{'skip (exists)' if exists and not a.force else 'would write':14} {path}")
            continue
        print(f"{write_file(path, text, a.force):14} {path}")
    if a.check:
        errors = check(a.platform, target)
        if errors:
            print("\n".join(errors))
            sys.exit(1)
        print("ok")


if __name__ == "__main__":
    main()

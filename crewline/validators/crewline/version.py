"""Crewline's own version: what machines install, and the rule that every shipped change raises it.

  python -m crewline version                          print the version of this Crewline
  python -m crewline version --repo <git root> --base <ref>   (CI on a pull request)

Claude Code updates an installed plugin only when `version` in .claude-plugin/plugin.json changes, so a change that
ships without a bump stays invisible on machines that already have Crewline.

  VER-001  files that ship to users changed since <base> but the version is not higher                     BLOCK
  VER-002  VERSION and .claude-plugin/plugin.json disagree                                                 BLOCK
  VER-003  version is not MAJOR.MINOR.PATCH                                                                BLOCK
  VER-004  the version (and, with --base, the base version and the shipped files that changed)            INFO
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .gitio import git
from .result import BLOCK, INFO, Result

CORE = Path(__file__).resolve().parents[2]
PLUGIN = Path(".claude-plugin/plugin.json")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
NOT_SHIPPED = ("validators/tests/", "evals/", "ci/")     # checked in CI, but nothing a user's session loads


def current(core: Path = CORE) -> str:
    try:
        return str(json.loads((core / PLUGIN).read_text(encoding="utf-8")).get("version", ""))
    except (OSError, ValueError):
        return ""


def _key(v: str) -> tuple[int, ...] | None:
    m = SEMVER.match(v or "")
    return tuple(int(x) for x in m.groups()) if m else None


def run(repo: str | None = None, base: str | None = None, core: Path = CORE) -> Result:
    v = current(core)
    res = Result("version", inputs={"version": v, "base": base or ""})
    if not _key(v):
        res.add("VER-003", BLOCK, f"plugin.json version {v!r} is not MAJOR.MINOR.PATCH", path=str(PLUGIN))
    vf = core / "VERSION"
    if vf.is_file() and vf.read_text(encoding="utf-8").strip() != v:
        res.add("VER-002", BLOCK, f"VERSION says {vf.read_text(encoding='utf-8').strip()!r} but plugin.json says {v!r}",
                path="VERSION", remediation="keep both at the same version")
    if not base:
        res.add("VER-004", INFO, f"Crewline {v}")
        return res.finish()
    top = Path(git(repo or str(core), "rev-parse", "--show-toplevel").strip())
    prefix = core.resolve().relative_to(top.resolve()).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    changed = [p[len(prefix):] for p in git(str(top), "diff", "--name-only", f"{base}...HEAD", "--", prefix or ".").splitlines()
               if p.startswith(prefix)]
    shipped = [p for p in changed if not p.startswith(NOT_SHIPPED)]
    try:
        old = str(json.loads(git(str(top), "show", f"{base}:{prefix}{PLUGIN.as_posix()}")).get("version", ""))
    except (RuntimeError, ValueError):
        old = ""                                                  # no plugin at the base: first release
    res.inputs.update(base_version=old, shipped_changed=len(shipped))
    res.add("VER-004", INFO, f"Crewline {old or '(none)'} at {base} -> {v}; {len(shipped)} shipped file(s) changed",
            evidence=", ".join(shipped[:10]))
    if shipped and old and _key(v) and _key(old) and _key(v) <= _key(old):
        res.add("VER-001", BLOCK, f"{len(shipped)} shipped file(s) changed but the version is still {v} (base {old}): "
                                  "machines that have Crewline would never receive this change",
                path=str(PLUGIN), evidence=", ".join(shipped[:10]),
                remediation="raise .claude-plugin/plugin.json and VERSION (patch: fix, minor: new rule/gate/agent, "
                            "major: a change that breaks tasks in progress) and add a CHANGELOG.md entry")
    return res.finish()

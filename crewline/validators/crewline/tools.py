"""Check the local tool capabilities in core/tools.yaml and print enable steps for any that are missing.

  TOOL-001  required capability missing (enable steps attached)   BLOCK
  TOOL-002  capability present                                     INFO
Connector/browser capabilities (`check.adapter`) are reported as NOT_CHECKED: the adapter verifies them by
calling the tool, and must show the same `enable` steps when they are missing.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

from .result import BLOCK, INFO, WARN, Result

CORE = Path(__file__).resolve().parents[2]


def run(only: list[str] | None = None) -> Result:
    spec = yaml.safe_load((CORE / "core" / "tools.yaml").read_text(encoding="utf-8"))["capabilities"]
    res = Result("tools")
    for name, cap in spec.items():
        if only and name not in only:
            continue
        check = cap.get("check", {})
        steps = "\n".join(f"  {i}. {s}" for i, s in enumerate(cap.get("enable", []), 1))
        if "adapter" in check:
            res.add("TOOL-000", WARN, f"{name}: NOT_CHECKED here ({check['adapter']}); adapter must verify",
                    remediation=steps)
            continue
        cmd = check.get("command", "")
        if "<" in cmd:                      # needs task parameters (e.g. upstream repo); checked at REPO_READY
            continue
        exe = cmd.split()[0]
        ok = shutil.which(exe) is not None
        out = ""
        if ok:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            out = (p.stdout + p.stderr).strip()
            ok = p.returncode == 0 and (check.get("expect", "") in out)
        if ok:
            res.add("TOOL-002", INFO, f"{name}: available ({out.splitlines()[0][:60] if out else exe})")
        else:
            res.add("TOOL-001", BLOCK, f"{name}: not available; needed for {', '.join(map(str, cap.get('needed_for', [])))}",
                    remediation="Enable it:\n" + steps)
    return res.finish()

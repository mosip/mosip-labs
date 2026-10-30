"""Installed adapter vs adapters/ source. Stale Cursor/Claude rules are a skipped rail.

  ADP-001  an installed file is missing or differs from the rendered adapter source                  BLOCK

  python -m crewline adapter-check --platform cursor|claude|generic --target <workspace> [--sync]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .result import BLOCK, Result

CORE = Path(__file__).resolve().parents[2]
INSTALL = CORE / "adapters" / "install.py"


def run(platform: str, target: str, sync: bool = False) -> Result:
    res = Result("adapter-check", inputs={"platform": platform, "target": target, "sync": sync})
    if sync:
        proc = subprocess.run(
            [sys.executable, str(INSTALL), "--platform", platform, "--target", target, "--sync"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            body = (proc.stdout or proc.stderr or "adapter sync failed").strip()
            res.add("ADP-001", BLOCK, f"sync failed: {body[-1500:]}")
            return res.finish()
    proc = subprocess.run(
        [sys.executable, str(INSTALL), "--platform", platform, "--target", target, "--check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        body = (proc.stdout or proc.stderr or "adapter check failed").strip()
        for line in body.splitlines() or [body]:
            res.add("ADP-001", BLOCK, line)
    return res.finish()

#!/usr/bin/env python3
"""Platform hook trampoline. {{CORE}} is baked in by install.py. Used by Cursor, Claude Code and git hooks."""
from __future__ import annotations

import sys
from pathlib import Path

CORE = Path(r"{{CORE}}")
sys.path.insert(0, str(CORE / "validators"))

from crewline.hook import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

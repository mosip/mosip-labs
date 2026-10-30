"""Entry point for bin/crewline: runs the validators package without installing it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crewline.__main__ import main  # noqa: E402

sys.exit(main())

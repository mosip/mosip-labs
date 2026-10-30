"""Consumer setup scripts exist and cover the documented one-time path."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / "scripts" / "setup.sh"
BAT = ROOT / "scripts" / "setup.bat"


def test_setup_scripts_exist_and_cover_prereqs():
    assert SH.is_file() and BAT.is_file()
    sh, bat = SH.read_text(encoding="utf-8"), BAT.read_text(encoding="utf-8")
    for text in (sh, bat):
        assert "validators/requirements.txt" in text.replace("\\", "/")
        assert "pytest" in text
        assert "crewline tools" in text
        assert "adapters/install.py" in text.replace("\\", "/")
        assert "cursor" in text and "claude" in text and "generic" in text
        assert "3.11" in text
    assert BAT.read_text(encoding="utf-8").lstrip().startswith("@echo off")
    assert SH.read_text(encoding="utf-8").lstrip().startswith("#!/usr/bin/env bash")

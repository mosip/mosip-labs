"""Active product pack: MOSIP plugin vs generic core.

  Packs live in packs/<id>/pack.yaml. Default is packs/ACTIVE (committed as `mosip`).
  Override for a process: CREWLINE_PACK=generic python -m crewline tools
  Switch the checkout:     python -m crewline pack --set generic
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from .result import BLOCK, INFO, Result

CORE = Path(__file__).resolve().parents[2]
PACKS = CORE / "packs"
ACTIVE_FILE = PACKS / "ACTIVE"
DEFAULT_PACK = "mosip"


def active_id() -> str:
    env = os.environ.get("CREWLINE_PACK", "").strip()
    if env:
        return env
    if ACTIVE_FILE.is_file():
        return ACTIVE_FILE.read_text(encoding="utf-8").splitlines()[0].strip() or DEFAULT_PACK
    return DEFAULT_PACK


def pack_dir(pack_id: str | None = None) -> Path:
    return PACKS / (pack_id or active_id())


def load(pack_id: str | None = None) -> dict:
    pid = pack_id or active_id()
    path = pack_dir(pid) / "pack.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"unknown pack {pid!r}: expected {path}")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    doc["id"] = doc.get("id") or pid
    doc["_dir"] = path.parent
    return doc


def list_ids() -> list[str]:
    return sorted(p.name for p in PACKS.iterdir() if p.is_dir() and (p / "pack.yaml").is_file())


def knowledge_dirs(pack_id: str | None = None) -> list[Path]:
    doc = load(pack_id)
    return [CORE / rel for rel in doc.get("knowledge") or []]


def uses_testrig(pack_id: str | None = None) -> bool:
    return bool((load(pack_id).get("sdet") or {}).get("testrig"))


def uses_coverage_cli(pack_id: str | None = None) -> bool:
    return bool((load(pack_id).get("sdet") or {}).get("coverage_cli"))


def merged_tools(pack_id: str | None = None) -> dict:
    core = yaml.safe_load((CORE / "core" / "tools.yaml").read_text(encoding="utf-8")) or {}
    doc = load(pack_id)
    rel = doc.get("tools")
    if not rel:
        return core
    overlay_path = pack_dir(pack_id) / rel
    if not overlay_path.is_file():
        return core
    overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
    caps = dict(core.get("capabilities") or {})
    caps.update(overlay.get("capabilities") or {})
    core["capabilities"] = caps
    if overlay.get("permission_gated"):
        pg = dict(core.get("permission_gated") or {})
        pg.update(overlay["permission_gated"])
        core["permission_gated"] = pg
    return core


def set_active(pack_id: str) -> Path:
    load(pack_id)  # raises if missing
    ACTIVE_FILE.write_text(pack_id.strip() + "\n", encoding="utf-8")
    return ACTIVE_FILE


def run(set_to: str | None = None) -> Result:
    res = Result("pack", inputs={"active": active_id()})
    if set_to:
        try:
            set_active(set_to)
        except FileNotFoundError as e:
            res.add("PCK-001", BLOCK, str(e), remediation=f"known packs: {', '.join(list_ids())}")
            return res.finish()
        res.inputs["active"] = active_id()
        res.add("PCK-002", INFO, f"active pack is now {active_id()}")
    doc = load()
    res.inputs["title"] = doc.get("title")
    res.inputs["testrig"] = uses_testrig()
    res.inputs["knowledge"] = [str(p) for p in knowledge_dirs()]
    res.inputs["packs"] = list_ids()
    res.add("PCK-002", INFO, f"active pack {doc['id']} ({doc.get('title', '')}); testrig={uses_testrig()}; "
            f"knowledge={', '.join(doc.get('knowledge') or ['(none)'])}")
    return res.finish()

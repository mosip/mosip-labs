"""Secret-scan attached defect reports before they are published or filed.

PILOT-001 attached an actuator dump. Procedure in the defect-analyst contract is not enough:
APPLICATION / SECURITY defects need a report_path, and that file is scanned. Values are never echoed.

  DEF-001  APPLICATION/SECURITY defect has no report_path                                          BLOCK
  DEF-002  report_path is missing on disk                                                          BLOCK
  DEF-003  the report contains a secret (fingerprint only; value never printed)                    BLOCK

  python -m crewline defect-reports --manifest <m>
"""
from __future__ import annotations

import json
from pathlib import Path

from . import secrets_scan
from .result import BLOCK, Result

NEEDS_REPORT = {"APPLICATION", "SECURITY"}


def run(manifest_path: str) -> Result:
    res = Result("defect-reports", inputs={"manifest": manifest_path})
    try:
        doc = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return Result.not_run("defect-reports", str(e))
    base = Path(manifest_path).resolve().parent
    for d in doc.get("defects") or []:
        did, cls, raw = d.get("id", "?"), d.get("class"), d.get("report_path") or ""
        if cls in NEEDS_REPORT and not str(raw).strip():
            res.add("DEF-001", BLOCK, f"{did}: {cls} defect has no secret-scanned report_path "
                    "(never attach a raw full report)", evidence=did)
            continue
        if not str(raw).strip():
            continue
        p = Path(raw)
        if not p.is_file():
            p = base / raw
        if not p.is_file():
            res.add("DEF-002", BLOCK, f"{did}: report_path {raw!r} is not a file", evidence=did)
            continue
        sec = secrets_scan.run([str(p)], str(p.parent), use_gitleaks=False)
        if sec.status == "FAIL":
            fps = ", ".join(f.evidence for f in sec.findings if f.evidence) or "redacted"
            res.add("DEF-003", BLOCK, f"{did}: report contains a secret; do not publish it ({fps})",
                    path=str(p), remediation="strip env/config dumps, rotate if committed, attach the error report only")
    return res.finish()

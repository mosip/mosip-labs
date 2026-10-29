"""Secret scan. Prefers an installed `gitleaks`; falls back to built-in patterns.

Secret values are NEVER printed or returned: findings carry the rule, location and a short
SHA-256 fingerprint so a human can locate the value without it entering model context.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .result import BLOCK, Result

# A value that is a framework placeholder is not a secret: $TOKEN$, {{hbs}}, ${env}, empty.
PLACEHOLDER = re.compile(r"^\s*(\$[A-Za-z0-9_:]+\$|\{\{.*\}\}|\$\{.*\}|<.*>|\"?\"?|changeme|xxx+)\s*$", re.I)
PATTERNS = [
    ("SEC-001", "private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("SEC-002", "AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SEC-003", "GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("SEC-004", "JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("SEC-005", "credential assignment",
     re.compile(r"(?i)\b([a-z0-9_.\-]*(?:secret|password|passwd|pwd|api[_-]?key|client[_-]?secret|access[_-]?token))\b"
                r"\s*[:=]\s*(?P<val>[^\s#]+)")),
]
TEXT_EXT = {".yml", ".yaml", ".properties", ".json", ".hbs", ".xml", ".java", ".md", ".txt", ".env", ".sh", ".py", ".ts", ".js"}


def _fp(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def _builtin(files: list[Path], base_dir: Path, res: Result) -> None:
    for p in files:
        if p.suffix.lower() not in TEXT_EXT or not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for rule, label, pat in PATTERNS:
                for m in pat.finditer(line):
                    val = m.groupdict().get("val") or m.group(0)
                    if rule == "SEC-005" and (PLACEHOLDER.match(val) or len(val.strip("'\"")) < 6):
                        continue
                    res.add(rule, BLOCK, f"possible {label}", path=p.relative_to(base_dir).as_posix()
                            if p.is_relative_to(base_dir) else str(p), line=n,
                            evidence=f"sha256:{_fp(val)}",
                            remediation="remove the value, rotate it if it was ever committed, "
                                        "and follow the incident procedure")


def run(paths: list[str], base_dir: str = ".", use_gitleaks: bool = True) -> Result:
    base = Path(base_dir).resolve()
    res = Result("secrets", inputs={"paths": len(paths), "engine": "builtin"})
    files = []
    for raw in paths:
        p = (base / raw).resolve()
        files.extend(sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p])
    exe = shutil.which("gitleaks") if use_gitleaks else None
    if exe:
        res.inputs["engine"] = "gitleaks"
        with tempfile.TemporaryDirectory() as td:
            report = Path(td, "r.json")
            for f in files:
                subprocess.run([exe, "detect", "--no-git", "--redact", "-s", str(f), "-r", str(report),
                                "--report-format", "json", "--exit-code", "0"], capture_output=True)
                if report.exists():
                    for item in json.loads(report.read_text() or "[]"):
                        res.add("SEC-GL", BLOCK, f"gitleaks: {item.get('RuleID')}", path=str(f),
                                line=item.get("StartLine"), evidence=f"fingerprint:{item.get('Fingerprint', '')[-10:]}")
    else:
        _builtin(files, base, res)
    return res.finish()

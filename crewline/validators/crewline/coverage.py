"""Wrapper around the team's existing CoverageCli `check` (apitest-commons). Commons-first: this is
the authoritative check for duplicate/missing uniqueIdentifier, verb mismatch, orphan cases,
traceability rows, Story keys, unreachable/unmapped endpoints and stale generated reports.

The wrapper only runs it and normalises the outcome; it never re-implements a gap type.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .result import BLOCK, INFO, Result

GAP_LINE = re.compile(r"^\s*([a-z][a-z\-]+)\s+(.+)$")
SUMMARY = re.compile(r"check:\s*(\d+)\s+gap\(s\)(?:,\s*(\d+)\s+accepted by baseline)?")


def run(commons_dir: str, module_root: str, module_code: str, offline: bool = False,
        extra_args: str = "--require-app-source") -> Result:
    res = Result("coverage-matrix", inputs={"commons_dir": commons_dir, "module_root": module_root,
                                            "module_code": module_code})
    mvn = shutil.which("mvn") or shutil.which("mvn.cmd")
    if not mvn:
        return Result.not_run("coverage-matrix", "maven not found on PATH")
    common = ["-q", "-Dgpg.skip=true", "-Dmaven.gitcommitid.skip=true"] + (["-o"] if offline else [])
    args = f"check --keys --module-root {Path(module_root).resolve()} --module-code {module_code} {extra_args}".strip()
    try:
        subprocess.run([mvn, *common, "compile"], cwd=commons_dir, check=True, capture_output=True, text=True)
        p = subprocess.run([mvn, *common, "org.codehaus.mojo:exec-maven-plugin:3.1.0:java",
                            "-Dexec.mainClass=io.mosip.testrig.apirig.coverage.CoverageCli", f"-Dexec.args={args}"],
                           cwd=commons_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        return Result.not_run("coverage-matrix", f"commons compile failed: {(e.stderr or e.stdout)[-400:]}")
    out = p.stdout + p.stderr
    m = SUMMARY.search(out)
    res.inputs["exit_code"] = p.returncode
    res.inputs["output_tail"] = out[-2000:]
    if not m:
        return Result.not_run("coverage-matrix", f"could not parse CoverageCli output (exit {p.returncode})",
                              output_tail=out[-1000:])
    gaps, accepted = int(m.group(1)), int(m.group(2) or 0)
    for line in out.splitlines():
        g = GAP_LINE.match(line)
        if g and "-" in g.group(1) and not line.lstrip().startswith(("check:", "app-source", "pre-registration")):
            res.add(f"COV:{g.group(1)}", BLOCK if p.returncode else INFO, g.group(2).strip())
    if p.returncode and not res.findings:
        res.add("COV:gap", BLOCK, f"{gaps} open gap(s); see output_tail")
    res.summary = f"{gaps} open gap(s), {accepted} accepted by baseline (CoverageCli exit {p.returncode})"
    res.status = "FAIL" if p.returncode else "PASS"
    return res

"""Database migration pairing (reversibility first). Compares the working tree with a base ref.

MOSIP layout (Verified: pre-registration db_upgrade_scripts/ and db_release_scripts/, 2026-10-28):
  db_upgrade_scripts/<db>/sql/<from>_to_<to>_upgrade.sql   twin  <from>_to_<to>_rollback.sql  (or _revoke.sql)
  db_release_scripts/<db>/sql/<ver>-release.sql            twin  <ver>-revoke.sql            (or _revoke.sql)
Flyway layout: V<ver>__<desc>.sql twin U<ver>__<desc>.sql.

  MIG-001  new forward script without its rollback/revoke twin                 BLOCK
  MIG-002  a script that exists on the base was modified or deleted            BLOCK (released scripts are immutable)
  MIG-003  new rollback/revoke script without a forward twin                   WARN
  MIG-004  destructive statement in a forward script (DROP TABLE/COLUMN, TRUNCATE, DELETE without WHERE)  WARN -> needs migration_review
"""
from __future__ import annotations

import re

from .gitio import changed_files, top
from .result import BLOCK, WARN, Result

FORWARD = [  # (forward regex, function giving acceptable twin names)
    (re.compile(r"^(?P<d>.*/)(?P<k>[^/]+)_upgrade\.sql$"), lambda m: [f"{m['d']}{m['k']}_rollback.sql", f"{m['d']}{m['k']}_revoke.sql"]),
    (re.compile(r"^(?P<d>.*/)(?P<k>[^/]+?)[-_]release\.sql$"), lambda m: [f"{m['d']}{m['k']}-revoke.sql", f"{m['d']}{m['k']}_revoke.sql"]),
    (re.compile(r"^(?P<d>.*/)V(?P<k>[^/]+\.sql)$"), lambda m: [f"{m['d']}U{m['k']}"]),
]
BACKWARD = re.compile(r"(_rollback|[-_]revoke)\.sql$|/U[^/]+\.sql$")
DESTRUCTIVE = re.compile(r"\bDROP\s+(TABLE|COLUMN|SCHEMA)\b|\bTRUNCATE\b|\bDELETE\s+FROM\s+\S+\s*;", re.I)


def run(repo: str, base: str) -> Result:
    res = Result("migration", inputs={"repo": repo, "base": base})
    try:
        root = top(repo)
        changed = {p: k for p, k in changed_files(repo, base).items() if p.lower().endswith(".sql")}
    except RuntimeError as e:
        return Result.not_run("migration", str(e))
    present = lambda p: (root / p).exists()
    for path, kind in sorted(changed.items()):
        if kind in ("M", "D"):
            res.add("MIG-002", BLOCK, f"{'modified' if kind == 'M' else 'deleted'} existing script {path}", path=path,
                    remediation="released migrations are immutable: add a new upgrade/rollback pair instead")
            continue
        for rx, twins in FORWARD:
            m = rx.match("/" + path)
            if m:
                cands = [t.lstrip("/") for t in twins(m)]
                if not any(present(t) for t in cands):
                    res.add("MIG-001", BLOCK, f"{path} has no rollback twin (expected {' or '.join(cands)})", path=path)
                text = (root / path).read_text(encoding="utf-8", errors="replace")
                for hit in DESTRUCTIVE.findall(text):
                    res.add("MIG-004", WARN, f"destructive statement ({' '.join(hit) if isinstance(hit, tuple) else hit}) "
                                             "needs approval migration_review", path=path)
                break
        else:
            if BACKWARD.search("/" + path):
                fwd = re.sub(r"_rollback\.sql$|_revoke\.sql$", "_upgrade.sql", path)
                fwd2 = re.sub(r"[-_]revoke\.sql$", "-release.sql", path)
                fwd3 = re.sub(r"/U([^/]+\.sql)$", r"/V\1", "/" + path).lstrip("/")
                if not any(present(p) for p in {fwd, fwd2, fwd3, re.sub(r"-release", "_release", fwd2)} - {path}):
                    res.add("MIG-003", WARN, f"{path} has no forward twin", path=path)
    res.inputs["changed_sql"] = len(changed)
    return res.finish()

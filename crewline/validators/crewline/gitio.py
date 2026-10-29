"""Small git helpers shared by the SDLC validators (change-scope, test-integrity, migration, evidence)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def git(repo: str | Path, *args: str, check: bool = True) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def top(repo: str | Path) -> Path:
    return Path(git(repo, "rev-parse", "--show-toplevel").strip())


def changed_files(repo: str | Path, base: str) -> dict[str, str]:
    """Working tree (committed + uncommitted + untracked) vs base: repo-relative path -> A|M|D|R."""
    root = top(repo)
    git(root, "rev-parse", "--verify", f"{base}^{{commit}}")
    out: dict[str, str] = {}
    for line in git(root, "diff", "--name-status", "-M", base).splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            out[parts[-1]] = parts[0][0]
            if parts[0].startswith("R"):
                out[parts[1]] = "D"
    for path in git(root, "ls-files", "--others", "--exclude-standard").splitlines():
        out.setdefault(path, "A")
    return out


def show(repo: str | Path, ref: str, path: str) -> str | None:
    root = top(repo)
    r = subprocess.run(["git", "-C", str(root), "show", f"{ref}:{path}"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def head(repo: str | Path) -> str:
    return git(repo, "rev-parse", "HEAD").strip()


def worktree_digest(repo: str | Path) -> str:
    """Hash of the uncommitted state (tracked diff vs HEAD + untracked file contents). Identifies what was tested."""
    root = top(repo)
    h = hashlib.sha256(git(root, "diff", "--binary", "HEAD").encode("utf-8", "replace"))
    for path in sorted(git(root, "ls-files", "--others", "--exclude-standard").splitlines()):
        h.update(path.encode())
        try:
            h.update((root / path).read_bytes())
        except OSError:
            pass
    return h.hexdigest()

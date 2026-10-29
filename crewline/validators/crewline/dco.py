"""DCO sign-off check over a commit range (Plan §23.2). Reads git; never trusts a commit-message claim
made by the model.

  DCO-001  commit has no `Signed-off-by:` trailer                     BLOCK
  DCO-002  no sign-off matches the commit author's email               BLOCK
"""
from __future__ import annotations

import re
import subprocess

from .result import BLOCK, INFO, Result

SOB = re.compile(r"^Signed-off-by:\s*(.+?)\s*<([^>]+)>\s*$", re.M)


def run(repo: str, rev_range: str) -> Result:
    res = Result("dco", inputs={"repo": repo, "range": rev_range})
    try:
        out = subprocess.run(["git", "-C", repo, "log", "--no-merges", "--format=%H%x1f%an%x1f%ae%x1f%B%x1e", rev_range],
                             check=True, capture_output=True, text=True, encoding="utf-8").stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return Result.not_run("dco", f"git log failed for {rev_range}: {getattr(e, 'stderr', e)}")
    commits = [c.strip("\n") for c in out.split("\x1e") if c.strip()]
    for c in commits:
        sha, name, email, body = c.split("\x1f", 3)
        signers = SOB.findall(body)
        short = sha[:10]
        if not signers:
            res.add("DCO-001", BLOCK, f"{short} has no Signed-off-by trailer", evidence=sha,
                    remediation="git commit --amend -s (or git rebase --signoff) before the PR gate")
        elif email.lower() not in {e.lower() for _, e in signers}:
            res.add("DCO-002", BLOCK, f"{short} sign-off does not match author <{email}>", evidence=sha)
    if not commits:
        res.add("DCO-000", INFO, f"no commits in {rev_range}")
    res.inputs["commits"] = len(commits)
    return res.finish()

"""The method body at the commit a pod is running.

The line number comes from the log. The file text comes from that commit on GitHub.
A line that is not in the file is reported as missing. Nothing here invents a line.
"""
from __future__ import annotations

import json
import logging
import os
import re

log = logging.getLogger(__name__)

_REPO = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<name>[^/.]+)")
# How many catalogued throw sites to open per scan. Each one is a tree lookup plus one file.
_MAX = 8


def java_relpath(class_name: str, file_name: str | None) -> str:
    """io.mosip.foo.Bar + Bar.java -> io/mosip/foo/Bar.java. An inner class stays in its outer file."""
    parts = (class_name or "").split(".")
    simple = parts[-1].split("$")[0] if parts and parts[-1] else "Unknown"
    name = file_name or (simple + ".java")
    if not name.endswith(".java"):
        name += ".java"
    return "/".join(parts[:-1] + [name])


def lines_around(text: str, line: int, radius: int = 3) -> dict | None:
    """Copy `radius` lines either side of the logged line. None when that line is not in the file."""
    rows = text.splitlines()
    if line < 1 or line > len(rows):
        return None
    start = max(1, line - radius)
    end = min(len(rows), line + radius)
    return {
        "line": line,
        "lines": [{"n": n, "text": rows[n - 1], "hit": n == line} for n in range(start, end + 1)],
    }


def path_for(paths: list[str], class_name: str, file_name: str | None) -> str | None:
    """The blob path whose suffix is src/main/java/<package>/<File>.java."""
    suffix = "src/main/java/" + java_relpath(class_name, file_name)
    hits = [p for p in paths if p.endswith(suffix)]
    return hits[0] if hits else None


def _repo(url: str) -> tuple[str, str] | None:
    m = _REPO.search(url or "")
    return (m.group("owner"), m.group("name")) if m else None


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "roottrace"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _http_get(url: str):
    """(status, text). Network errors are a status of 0 so a scan can record the miss and continue."""
    import requests
    try:
        r = requests.get(url, headers=_headers(), timeout=20)
        return r.status_code, r.text
    except requests.RequestException as e:
        log.info("source fetch failed: %s", e)
        return 0, ""


def fetch_snippet(repo_url: str, commit: str, class_name: str, line: int,
                  file_name: str | None = None, get=_http_get) -> dict:
    """Snippet dict, or snippet_note when the file or the line is not at this commit."""
    pair = _repo(repo_url)
    if not pair or not commit or not class_name or not line:
        return {"snippet_note": "no repository or commit for this frame"}
    owner, name = pair
    status, body = get(f"https://api.github.com/repos/{owner}/{name}/git/trees/{commit}?recursive=1")
    if status != 200:
        return {"snippet_note": f"could not list {owner}/{name} at {commit[:12]}"}
    try:
        data = json.loads(body)
    except ValueError:
        return {"snippet_note": f"could not list {owner}/{name} at {commit[:12]}"}
    if data.get("truncated"):
        return {"snippet_note": f"tree of {owner}/{name} at {commit[:12]} was truncated"}
    paths = [t.get("path") or "" for t in data.get("tree") or []]
    found = path_for(paths, class_name, file_name)
    if not found:
        return {"snippet_note": f"no source file for {class_name} at {commit[:12]}"}
    status, text = get(f"https://raw.githubusercontent.com/{owner}/{name}/{commit}/{found}")
    if status != 200:
        return {"snippet_note": f"could not read {found} at {commit[:12]}"}
    snip = lines_around(text, int(line))
    if not snip:
        return {"snippet_note": f"logged line {line} is past the end of {found} at {commit[:12]}"}
    snip["path"] = found
    snip["commit"] = commit
    return {"snippet": snip, "commit": commit}


def attach_snippets(issues: list[dict], revisions: list[dict], fetch=fetch_snippet) -> None:
    """Open the running commit for the highest-scoring frames that have one.

    A frame with no revision keeps a note. The sample commit in sources.yaml is not used.
    """
    by_pod = {}
    for row in revisions or []:
        commit = (row.get("revision") or {}).get("commit")
        if row.get("pod") and commit:
            by_pod[(row.get("namespace"), row["pod"])] = commit
    opened = 0
    ranked = sorted(issues, key=lambda i: -(i.get("score") or 0))
    for iss in ranked:
        code = iss.get("code")
        if not code or not code.get("line"):
            continue
        ns = iss.get("namespace")
        pods = [code["pod"]] if code.get("pod") else list(iss.get("pods") or [])
        commit = next((by_pod[(ns, p)] for p in pods if (ns, p) in by_pod), None)
        if not commit:
            code["snippet_note"] = "running commit was not read from the pod"
            continue
        if not code.get("repo"):
            code["commit"] = commit
            code["snippet_note"] = "no repository mapped for this class"
            continue
        if opened >= _MAX:
            code["commit"] = commit
            code["snippet_note"] = "snippet skipped; the scan already opened 8 files"
            continue
        opened += 1
        found = fetch(code["repo"], commit, code["class"], code["line"], code.get("file"))
        code.update(found)

"""
Code Crawler — Stage 1d.

Fetches MOSIP source code files from GitHub repositories and prepares them
for embedding into the mosip_code ChromaDB collection.

Why source code matters for a support chatbot:
  - Error code constants are DEFINED in Java files — e.g. IDA-MLC-009 is a string
    literal in IdAuthenticationErrorConstants.java with a comment explaining it.
  - Service implementation files show exactly what validation is performed and
    what triggers each error — the "why" behind error codes.
  - Configuration files show what parameters control behaviour.

Repo discovery:
  Uses the same get_org_repos() function as github_crawler — auto-discovers all
  relevant repos in the MOSIP org and uses each repo's own default_branch.
  Most repos are on 'master'; some use 'main' or a version branch like '1.2.0'.
  Only the default branch of each repo is crawled — feature branches are not
  relevant for a support chatbot and would add noise.

Strategy (smart, not exhaustive):
  1. Priority files  — *ErrorConstants*, *ServiceImpl*, *Controller*, etc.
                       Always fetched. These define what errors mean and why.
  2. Standard files  — other .java, .yaml, .properties files, up to per-repo limit.
  3. Skip patterns   — test files, generated code, build output — just noise.

Output: data/mosip_code.json  (same format as other data files)
"""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    CODE_EXCLUDE_PATTERNS, CODE_FILE, CODE_INCLUDE_EXTENSIONS,
    CODE_MAX_FILE_BYTES, CODE_PRIORITY_PATTERNS,
    CRAWL_DELAY_SECS, GITHUB_TOKEN,
)
from crawler.github_crawler import get_org_repos

_GITHUB_API = "https://api.github.com"

# Per-repo limits to keep total size manageable on first run
_PRIORITY_LIMIT_PER_REPO = 100   # always fetch these
_STANDARD_LIMIT_PER_REPO = 200   # regular files after priority


def _headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _is_excluded(path: str) -> bool:
    """Return True if the path matches any exclusion pattern."""
    return any(pat in path for pat in CODE_EXCLUDE_PATTERNS)


def _is_priority(name: str) -> bool:
    """Return True if the filename matches any priority pattern."""
    return any(pat in name for pat in CODE_PRIORITY_PATTERNS)


def _ext(name: str) -> str:
    return Path(name).suffix.lower()


def get_repo_file_tree(repo: str, branch: str = "master") -> tuple[list[dict], str]:
    """Return the full recursive file tree for a repo branch and the resolved branch name.

    Falls back to 'main', 'master', 'develop' if the requested branch doesn't exist.
    Returns (entries, resolved_branch) so callers can build correct blob URLs.
    """
    for ref in (branch, "main", "master", "develop"):
        url = f"{_GITHUB_API}/repos/{repo}/git/trees/{ref}?recursive=1"
        res = requests.get(url, headers=_headers(), timeout=30)
        if res.ok:
            tree = res.json().get("tree", [])
            print(f"  {repo}: {len(tree)} entries in tree (branch: {ref})")
            return [
                e for e in tree
                if e.get("type") == "blob"
                and _ext(e["path"]) in CODE_INCLUDE_EXTENSIONS
                and not _is_excluded(e["path"])
                and e.get("size", 0) <= CODE_MAX_FILE_BYTES
            ], ref
        if res.status_code == 409:
            continue   # empty repo or branch not found
    print(f"  {repo}: could not fetch tree")
    return [], branch


def fetch_file_content(repo: str, file_path: str) -> str | None:
    """Fetch the decoded content of one file via the GitHub contents API."""
    url = f"{_GITHUB_API}/repos/{repo}/contents/{file_path}"
    try:
        res = requests.get(url, headers=_headers(), timeout=30)
        if not res.ok:
            return None
        data = res.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content", "")
    except Exception:
        return None


def crawl_repo(repo: str, branch: str = "master") -> list[dict]:
    """Crawl one repo: fetch priority files first, then standard files.

    Priority files (ErrorConstants, ServiceImpl, etc.) are always fetched.
    Standard files fill the remaining quota up to _STANDARD_LIMIT_PER_REPO.
    """
    print(f"\n  Crawling code in {repo} ...")
    entries, resolved_branch = get_repo_file_tree(repo, branch)
    if not entries:
        return []

    # Separate priority vs standard files
    priority = [e for e in entries if _is_priority(Path(e["path"]).name)]
    standard = [e for e in entries if not _is_priority(Path(e["path"]).name)]

    print(f"    {len(priority)} priority files, {len(standard)} standard files")

    results: list[dict] = []

    def _fetch_and_store(entry: dict) -> bool:
        file_path = entry["path"]
        content   = fetch_file_content(repo, file_path)
        time.sleep(CRAWL_DELAY_SECS)
        if not content or len(content.strip()) < 50:
            return False

        lang = _ext(file_path).lstrip(".")
        file_url = f"https://github.com/{repo}/blob/{resolved_branch}/{file_path}"
        results.append({
            "source_type": "code",
            "url":         file_url,
            "title":       Path(file_path).name,
            "repo":        repo,
            "file_path":   file_path,
            "language":    lang,
            "content":     content,
        })
        return True

    # Fetch priority files (no limit)
    fetched_priority = 0
    for entry in priority[:_PRIORITY_LIMIT_PER_REPO]:
        if _fetch_and_store(entry):
            fetched_priority += 1

    # Fill remaining quota with standard files
    fetched_standard = 0
    for entry in standard[:_STANDARD_LIMIT_PER_REPO]:
        if _fetch_and_store(entry):
            fetched_standard += 1

    print(f"    Done: {fetched_priority} priority + {fetched_standard} standard = {len(results)} files")
    return results


def crawl_all(repos: list[dict] | None = None) -> list[dict]:
    """Crawl all MOSIP repos for source code.

    repos, if provided, must be a list of dicts with 'full_name' and 'default_branch'
    (same shape as get_org_repos() output). When None, auto-discovers via get_org_repos().
    """
    repo_metas = repos or get_org_repos()
    all_results: list[dict] = []
    for meta in repo_metas:
        full_name = meta["full_name"]
        branch    = meta.get("default_branch", "master")
        results   = crawl_repo(full_name, branch)
        all_results.extend(results)
        print(f"  Running total: {len(all_results)} files")
    return all_results


def crawl_incremental(state: dict) -> list[dict]:
    """Incremental code update: re-fetch files whose SHA has changed.

    Compares the current tree SHA against saved SHAs in crawl state.
    Only files with a new SHA are re-fetched — unchanged files are skipped.
    Uses get_org_repos() to discover repos dynamically (picks up new repos automatically).
    """
    code_state: dict = state.get("code", {})
    all_new: list[dict] = []

    for meta in get_org_repos():
        repo   = meta["full_name"]
        branch = meta.get("default_branch", "master")

        saved_shas: dict = code_state.get(repo, {}).get("file_shas", {})
        entries, resolved_branch = get_repo_file_tree(repo, branch)
        new_entries = [
            e for e in entries
            if saved_shas.get(e["path"]) != e.get("sha", "")
        ]
        if not new_entries:
            print(f"  {repo}: no code changes detected.")
            continue

        print(f"  {repo}: {len(new_entries)} files changed - fetching...")
        for entry in new_entries:
            file_path = entry["path"]
            content   = fetch_file_content(repo, file_path)
            time.sleep(CRAWL_DELAY_SECS)
            if not content or len(content.strip()) < 50:
                continue

            lang = _ext(file_path).lstrip(".")
            all_new.append({
                "source_type": "code",
                "url":         f"https://github.com/{repo}/blob/{resolved_branch}/{file_path}",
                "title":       Path(file_path).name,
                "repo":        repo,
                "file_path":   file_path,
                "language":    lang,
                "content":     content,
                "_sha":        entry.get("sha", ""),
            })

    return all_new


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("⚠️  GITHUB_TOKEN not set. Rate limited to 60 req/hr. "
              "Add it to .env for 5,000 req/hr.")

    print("MOSIP Code Crawler - fetching source files from all repos...")
    results = crawl_all()

    with open(CODE_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(results)} source files -> {CODE_FILE}")

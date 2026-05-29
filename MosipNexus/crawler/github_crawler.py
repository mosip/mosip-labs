"""
GitHub Issues Crawler — Stage 1c.

Fetches closed issues (with all comments) from MOSIP's public GitHub repositories.
GitHub Issues are the richest source of real error resolutions — community members
post the exact error, and maintainers post the exact fix.

Repo discovery:
  When GITHUB_TOKEN is set, this crawler auto-discovers ALL repos in the MOSIP
  GitHub org (https://github.com/orgs/mosip/repositories) via the org API and
  filters them intelligently:
    ✅  Java/Python/Shell/TypeScript repos — core services and utilities
    ❌  Archived repos — no longer maintained
    ❌  Empty repos — nothing to index
    ❌  Test/benchmark repos — noise (acceptance-tests, performance-tests)
    ❌  Documentation repo — already crawled by docs_crawler
  Without a token, falls back to the hardcoded GITHUB_REPOS list in settings.py.

Branch strategy:
  Each repo uses its own default_branch (returned by the org API).
  Most MOSIP repos use 'master'; some use 'main' or a version branch like '1.2.0'.
  Only the default branch is indexed — feature branches are not relevant for support.

API used:
  GET /orgs/{org}/repos?type=public&per_page=100&page=N  — repo discovery
  GET /repos/{owner}/{repo}/issues?state=all&per_page=100&page=N
  GET /repos/{owner}/{repo}/issues/{number}/comments

Authentication:
  Without GITHUB_TOKEN : 60 requests/hour (too slow for a full crawl).
  With    GITHUB_TOKEN : 5,000 requests/hour (create a free token at
  github.com → Settings → Developer Settings → Personal Access Tokens → Classic).
  No special scopes needed — public repos only.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    CRAWL_DELAY_SECS, GITHUB_FILE, GITHUB_MAX_ISSUES,
    GITHUB_ORG, GITHUB_REPO_EXCLUDE, GITHUB_REPOS,
    GITHUB_TOKEN, GITHUB_USEFUL_LANGUAGES,
)

_GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _check_rate_limit() -> None:
    res = requests.get(f"{_GITHUB_API}/rate_limit", headers=_headers(), timeout=10)
    data = res.json().get("rate", {})
    remaining = data.get("remaining", 0)
    if remaining < 10:
        reset_in = data.get("reset", 0) - int(time.time())
        print(f"  ⚠️  GitHub rate limit almost exhausted ({remaining} left). "
              f"Resets in {max(reset_in, 0)//60} min. "
              f"Add GITHUB_TOKEN to .env for 5,000 req/hr.")


def get_repo_issues(repo: str, state: str = "all", max_issues: int = GITHUB_MAX_ISSUES) -> list[dict]:
    """Fetch up to max_issues issues from a repo, excluding pull requests."""
    issues: list[dict] = []
    page = 1
    while len(issues) < max_issues:
        url = f"{_GITHUB_API}/repos/{repo}/issues"
        params = {"state": state, "per_page": 100, "page": page, "direction": "desc"}
        res = requests.get(url, headers=_headers(), params=params, timeout=30)

        if res.status_code == 403:
            print(f"  Rate limited on {repo}. Add GITHUB_TOKEN to .env.")
            break
        if res.status_code == 404:
            print(f"  Repo not found: {repo}")
            break
        if not res.ok:
            print(f"  HTTP {res.status_code} for {repo} page {page}")
            break

        batch = [i for i in res.json() if "pull_request" not in i]
        if not batch:
            break

        issues.extend(batch)
        if len(res.json()) < 100:
            break
        page += 1
        time.sleep(CRAWL_DELAY_SECS)

    return issues[:max_issues]


def get_issue_comments(repo: str, issue_number: int) -> str:
    """Fetch all comments for an issue and return them as joined text."""
    url = f"{_GITHUB_API}/repos/{repo}/issues/{issue_number}/comments"
    try:
        res = requests.get(url, headers=_headers(), timeout=30)
        if not res.ok:
            return ""
        comments = res.json()
        parts = []
        for c in comments:
            body = (c.get("body") or "").strip()
            author = c.get("user", {}).get("login", "")
            if body:
                parts.append(f"[{author}]: {body}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def crawl_repo(repo: str, max_issues: int = GITHUB_MAX_ISSUES) -> list[dict]:
    """Crawl one repo: fetch issues + comments, return structured dicts."""
    print(f"\n  Crawling {repo} ...")
    _check_rate_limit()

    issues = get_repo_issues(repo, state="all", max_issues=max_issues)
    print(f"  Found {len(issues)} issues — fetching comments...")

    results: list[dict] = []
    for i, issue in enumerate(issues, 1):
        number = issue["number"]
        title  = issue.get("title", "").strip()
        body   = (issue.get("body") or "").strip()
        state  = issue.get("state", "")
        labels = ", ".join(lb["name"] for lb in issue.get("labels", []))

        comments = get_issue_comments(repo, number)
        time.sleep(CRAWL_DELAY_SECS)

        # Build a readable document: problem + resolution in one text block
        content_parts = []
        if body:
            content_parts.append(f"Problem description:\n{body}")
        if comments:
            content_parts.append(f"Discussion and resolution:\n{comments}")
        content = "\n\n".join(content_parts)

        if not content.strip():
            continue

        results.append({
            "source_type": "github",
            "url":         issue["html_url"],
            "title":       title,
            "repo":        repo,
            "number":      number,
            "state":       state,
            "labels":      labels,
            "content":     content,
        })
        if i % 50 == 0:
            print(f"    [{i}/{len(issues)}] processed...")

    print(f"  Done: {len(results)} usable issues from {repo}")
    return results


def get_org_repos() -> list[dict]:
    """Discover all relevant public repos in the MOSIP GitHub org.

    Returns a list of dicts, each with:
      full_name      — e.g. "mosip/id-authentication"
      default_branch — the repo's own default branch (master / main / 1.2.0 / etc.)
      description    — repo description string

    Filters applied:
      - archived=False        (skip unmaintained repos)
      - size > 0              (skip empty repos)
      - language in useful set (skip pure HTML/CSS/docs repos)
      - name not in exclude list (skip tests, demos, docs repo)

    Falls back to GITHUB_REPOS hardcoded list if the token is missing or the
    org API returns an error.
    """
    if not GITHUB_TOKEN:
        print("  No GITHUB_TOKEN — using hardcoded GITHUB_REPOS fallback list.")
        return [{"full_name": r, "default_branch": "master", "description": ""}
                for r in GITHUB_REPOS]

    repos: list[dict] = []
    page = 1
    while True:
        url = f"{_GITHUB_API}/orgs/{GITHUB_ORG}/repos"
        params = {"type": "public", "per_page": 100, "page": page}
        res = requests.get(url, headers=_headers(), params=params, timeout=30)

        if not res.ok:
            print(f"  Org API error {res.status_code}: {res.json().get('message', '')}. "
                  f"Falling back to hardcoded list.")
            return [{"full_name": r, "default_branch": "master", "description": ""}
                    for r in GITHUB_REPOS]

        batch = res.json()
        if not batch:
            break

        for r in batch:
            name     = r.get("name", "")
            language = r.get("language") or ""
            archived = r.get("archived", False)
            size     = r.get("size", 0)

            if archived:
                continue
            if size == 0:
                continue
            if name in GITHUB_REPO_EXCLUDE:
                continue
            if language and language not in GITHUB_USEFUL_LANGUAGES:
                # Allow repos with no declared language (e.g. config-only repos)
                continue

            repos.append({
                "full_name":      r["full_name"],
                "default_branch": r.get("default_branch", "master"),
                "description":    r.get("description") or "",
            })

        if len(batch) < 100:
            break
        page += 1
        time.sleep(CRAWL_DELAY_SECS)

    print(f"  Discovered {len(repos)} relevant repos in '{GITHUB_ORG}' org "
          f"(out of all public repos, after filtering).")
    return repos


def crawl_all(repos: list[dict] | None = None) -> list[dict]:
    """Full crawl: discover all org repos (or use provided list) and fetch issues.

    Each entry in repos must be a dict with at least 'full_name'.
    When repos is None, calls get_org_repos() to auto-discover.
    """
    repo_metas = repos or get_org_repos()
    all_results: list[dict] = []
    for meta in repo_metas:
        full_name = meta["full_name"]
        results = crawl_repo(full_name)
        all_results.extend(results)
        print(f"  Running total: {len(all_results)} issues across all repos")
    return all_results


def get_new_issue_ids(repo: str, max_number: int) -> list[dict]:
    """Return issues from repo with number > max_number (incremental mode).

    GitHub issues are numbered sequentially, and the API returns them newest-first,
    so we stop pagination as soon as we hit an issue we already have.
    """
    new_issues: list[dict] = []
    page = 1
    while True:
        url = f"{_GITHUB_API}/repos/{repo}/issues"
        params = {"state": "all", "per_page": 100, "page": page, "direction": "desc"}
        res = requests.get(url, headers=_headers(), params=params, timeout=30)

        if not res.ok:
            break

        batch = [i for i in res.json() if "pull_request" not in i]
        if not batch:
            break

        new_on_page = [i for i in batch if i["number"] > max_number]
        new_issues.extend(new_on_page)

        # If any issue on this page is already known, stop — older pages have nothing new
        if len(new_on_page) < len(batch):
            break

        page += 1
        time.sleep(CRAWL_DELAY_SECS)

    return new_issues


def crawl_incremental(state: dict) -> list[dict]:
    """Fetch only issues created after the last known issue number per repo.

    Uses get_org_repos() to discover repos dynamically — so new repos added
    to the MOSIP org will be picked up automatically on the next incremental run.
    """
    github_state: dict = state.get("github", {})
    all_new: list[dict] = []

    repo_metas = get_org_repos()
    repo_names = [m["full_name"] for m in repo_metas]

    for repo in repo_names:
        max_number = github_state.get(repo, {}).get("max_issue_number", 0)
        print(f"  {repo}: checking issues > #{max_number} ...")

        new_raw = get_new_issue_ids(repo, max_number)
        if not new_raw:
            print(f"    No new issues.")
            continue

        print(f"    {len(new_raw)} new issues — fetching comments...")
        for issue in new_raw:
            number  = issue["number"]
            body    = (issue.get("body") or "").strip()
            comments = get_issue_comments(repo, number)
            time.sleep(CRAWL_DELAY_SECS)

            content_parts = []
            if body:
                content_parts.append(f"Problem description:\n{body}")
            if comments:
                content_parts.append(f"Discussion and resolution:\n{comments}")
            content = "\n\n".join(content_parts)

            if not content.strip():
                continue

            all_new.append({
                "source_type": "github",
                "url":         issue["html_url"],
                "title":       issue.get("title", "").strip(),
                "repo":        repo,
                "number":      number,
                "state":       issue.get("state", ""),
                "labels":      ", ".join(lb["name"] for lb in issue.get("labels", [])),
                "content":     content,
            })

    return all_new


if __name__ == "__main__":
    print("GitHub Issues Crawler — crawling all MOSIP repos...")
    if not GITHUB_TOKEN:
        print("⚠️  GITHUB_TOKEN not set. Rate limited to 60 req/hr. "
              "Add it to .env for 5,000 req/hr (free).")

    results = crawl_all()

    with open(GITHUB_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(results)} GitHub issues -> {GITHUB_FILE}")

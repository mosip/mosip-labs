"""
Jira Crawler (optional).

Fetches resolved Jira tickets (with descriptions and comments) from MOSIP's
Jira project. Resolved tickets are the most valuable — they contain the problem
and the confirmed fix.

Requires JIRA_URL, JIRA_USER, and JIRA_TOKEN in .env.

Generate an Atlassian API token at:
  https://id.atlassian.com/manage-profile/security/api-tokens

Usage:
  uv run python MosipNexus/crawler/jira_crawler.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    CRAWL_DELAY_SECS, JIRA_FILE, JIRA_PROJECT_KEYS,
    JIRA_TOKEN, JIRA_URL, JIRA_USER,
)


def _is_configured() -> bool:
    return all([JIRA_URL, JIRA_USER, JIRA_TOKEN])


def _auth() -> tuple[str, str]:
    return (JIRA_USER, JIRA_TOKEN)


def search_issues(project_key: str, start: int = 0, max_results: int = 100) -> list[dict]:
    """Search Jira for resolved issues in a project."""
    url = f"{JIRA_URL}/rest/api/2/search"
    jql = (
        f"project = {project_key} "
        f"AND status in (Resolved, Done, Closed) "
        f"ORDER BY updated DESC"
    )
    params = {
        "jql":        jql,
        "startAt":    start,
        "maxResults": max_results,
        "fields":     "summary,description,comment,status,labels,issuetype,resolution",
    }
    try:
        res = requests.get(url, auth=_auth(), params=params, timeout=30)
        res.raise_for_status()
        return res.json().get("issues", [])
    except Exception as e:
        print(f"  Jira search error for {project_key}: {e}")
        return []


def _to_text(value) -> str:
    """Extract plain text from a string or an ADF (Atlassian Document Format) object.

    Jira Cloud REST v3 returns description/body as ADF dicts; v2/Server returns strings.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        out: list[str] = []

        def _walk(node):
            if isinstance(node, dict):
                if node.get("type") == "text" and isinstance(node.get("text"), str):
                    out.append(node["text"])
                for child in node.get("content", []):
                    _walk(child)
            elif isinstance(node, list):
                for child in node:
                    _walk(child)

        _walk(value)
        return " ".join(out).strip()
    return ""


def issue_to_dict(issue: dict) -> dict | None:
    """Convert a Jira issue API response to our standard document format."""
    key    = issue.get("key", "")
    fields = issue.get("fields", {})
    title  = fields.get("summary", "").strip()
    desc   = _to_text(fields.get("description"))
    status = fields.get("status", {}).get("name", "")
    labels = ", ".join(fields.get("labels", []))
    resolution = fields.get("resolution", {})
    resolution_name = resolution.get("name", "") if resolution else ""

    # Collect comments
    comment_bodies = []
    for c in fields.get("comment", {}).get("comments", []):
        body = _to_text(c.get("body"))
        author = c.get("author", {}).get("displayName", "")
        if body:
            comment_bodies.append(f"[{author}]: {body}")

    content_parts = []
    if desc:
        content_parts.append(f"Problem:\n{desc}")
    if resolution_name:
        content_parts.append(f"Resolution: {resolution_name}")
    if comment_bodies:
        content_parts.append("Discussion:\n" + "\n\n".join(comment_bodies))

    content = "\n\n".join(content_parts)
    if len(content.strip()) < 50:
        return None

    return {
        "source_type": "jira",
        "url":         f"{JIRA_URL}/browse/{key}",
        "title":       f"[{key}] {title}",
        "key":         key,
        "status":      status,
        "labels":      labels,
        "content":     content,
    }


def crawl_project(project_key: str) -> list[dict]:
    """Crawl all resolved issues in one Jira project."""
    results: list[dict] = []
    start = 0
    batch_size = 100
    while True:
        batch = search_issues(project_key, start=start, max_results=batch_size)
        if not batch:
            break
        for issue in batch:
            doc = issue_to_dict(issue)
            if doc:
                results.append(doc)
                print(f"    OK  {doc['key']}: {doc['title'][:70]}")
            time.sleep(CRAWL_DELAY_SECS)
        if len(batch) < batch_size:
            break
        start += batch_size
    return results


def crawl_all() -> list[dict]:
    """Crawl all configured Jira projects."""
    if not _is_configured():
        print("Jira not configured. Set JIRA_URL, JIRA_USER, JIRA_TOKEN in .env")
        return []

    results: list[dict] = []
    for project_key in JIRA_PROJECT_KEYS:
        print(f"\n  Crawling Jira project: {project_key} ...")
        project_results = crawl_project(project_key)
        print(f"  Done: {len(project_results)} issues from {project_key}")
        results.extend(project_results)
    return results


if __name__ == "__main__":
    if not _is_configured():
        print("Set JIRA_URL, JIRA_USER, JIRA_TOKEN in .env first.")
        sys.exit(1)

    print(f"Crawling Jira: {JIRA_URL} ...")
    results = crawl_all()

    with open(JIRA_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(results)} Jira tickets → {JIRA_FILE}")

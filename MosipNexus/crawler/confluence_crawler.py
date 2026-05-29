"""
Confluence Crawler (optional).

Crawls a Confluence space and exports pages as plain text for ingestion.
Requires CONFLUENCE_URL, CONFLUENCE_USER, and CONFLUENCE_TOKEN in .env.

Generate an Atlassian API token at:
  https://id.atlassian.com/manage-profile/security/api-tokens

Usage:
  uv run python MosipNexus/crawler/confluence_crawler.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests
from markdownify import markdownify

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    CONFLUENCE_FILE, CONFLUENCE_SPACE_KEYS,
    CONFLUENCE_TOKEN, CONFLUENCE_URL, CONFLUENCE_USER,
    CRAWL_DELAY_SECS,
)


def _is_configured() -> bool:
    return all([CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN])


def _auth() -> tuple[str, str]:
    return (CONFLUENCE_USER, CONFLUENCE_TOKEN)


def get_pages_in_space(space_key: str, limit: int = 50) -> list[dict]:
    """Paginate through all pages in a Confluence space."""
    pages: list[dict] = []
    start = 0
    while True:
        url = f"{CONFLUENCE_URL}/rest/api/content"
        params = {
            "type": "page",
            "spaceKey": space_key,
            "status": "current",
            "limit": limit,
            "start": start,
            "expand": "body.storage,metadata.labels",
        }
        try:
            res = requests.get(url, auth=_auth(), params=params, timeout=30)
            res.raise_for_status()
            data = res.json()
            batch = data.get("results", [])
            pages.extend(batch)
            if len(batch) < limit:
                break
            start += limit
            time.sleep(CRAWL_DELAY_SECS)
        except Exception as e:
            print(f"  Error fetching space {space_key} at start={start}: {e}")
            break
    return pages


def page_to_dict(page: dict) -> dict | None:
    """Convert a Confluence page API response to our standard document format."""
    page_id   = page.get("id", "")
    title     = page.get("title", "")
    html      = page.get("body", {}).get("storage", {}).get("value", "")
    labels    = [lb["name"] for lb in page.get("metadata", {}).get("labels", {}).get("results", [])]

    content = markdownify(html, heading_style="ATX", strip=["script", "style"]).strip()
    if len(content) < 100:
        return None

    page_url = f"{CONFLUENCE_URL}/pages/viewpage.action?pageId={page_id}"
    return {
        "source_type": "confluence",
        "url":         page_url,
        "title":       title,
        "labels":      ", ".join(labels),
        "content":     content,
    }


def crawl_all() -> list[dict]:
    """Crawl all configured Confluence spaces."""
    if not _is_configured():
        print("Confluence not configured. Set CONFLUENCE_URL, CONFLUENCE_USER, "
              "CONFLUENCE_TOKEN in .env")
        return []

    results: list[dict] = []
    for space_key in CONFLUENCE_SPACE_KEYS:
        print(f"\n  Crawling Confluence space: {space_key} ...")
        pages = get_pages_in_space(space_key)
        print(f"  Found {len(pages)} pages")
        for page in pages:
            doc = page_to_dict(page)
            if doc:
                results.append(doc)
                safe_title = doc['title'][:80].encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
                print(f"    OK  {safe_title}")
            time.sleep(CRAWL_DELAY_SECS)

    return results


if __name__ == "__main__":
    if not _is_configured():
        print("Set CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN in .env first.")
        sys.exit(1)

    print(f"Crawling Confluence: {CONFLUENCE_URL} ...")
    results = crawl_all()

    with open(CONFLUENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(results)} pages -> {CONFLUENCE_FILE}")

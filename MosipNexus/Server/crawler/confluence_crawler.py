"""
Confluence Crawler (optional).

Crawls configured Confluence spaces and exports pages as plain text for
ingestion. Requires ``CONFLUENCE_URL``, ``CONFLUENCE_USER``, and
``CONFLUENCE_TOKEN`` in the environment.

Generate an Atlassian API token at:
  https://id.atlassian.com/manage-profile/security/api-tokens

Public crawl helpers: ``get_pages_in_space``, ``page_to_dict``, ``crawl_all``,
``crawl_incremental`` (version-based delta for ``run_update.py``).

Usage:
  uv run python Server/crawler/confluence_crawler.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    CONFLUENCE_FILE, CONFLUENCE_SPACE_KEYS,
    CONFLUENCE_TOKEN, CONFLUENCE_URL, CONFLUENCE_USER,
    CRAWL_DELAY_SECS,
)
from crawler.utils import table_to_prose


def _is_configured() -> bool:
    return all([CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN])


def _auth() -> tuple[str, str]:
    return (CONFLUENCE_USER, CONFLUENCE_TOKEN)


def get_pages_in_space(space_key: str, limit: int = 50) -> list[dict]:
    """Paginate through all current pages in a Confluence space.

    Args:
        space_key: Confluence space key (e.g. ``MOSIP``).
        limit: Page size for the REST API.

    Returns:
        Raw Confluence page objects (with expanded body/version).
    """
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
            "expand": "body.storage,metadata.labels,version",
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
    version   = page.get("version", {}).get("number", 0)

    # Convert tables to prose before markdownify so Confluence spec/config
    # tables embed correctly (header+value pairs instead of raw pipe-cells).
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        prose = table_to_prose(table)
        if prose:
            replacement = soup.new_tag("p")
            replacement.string = prose
            table.replace_with(replacement)

    content = markdownify(str(soup), heading_style="ATX", strip=["script", "style"]).strip()
    if len(content) < 100:
        return None

    page_url = f"{CONFLUENCE_URL}/pages/viewpage.action?pageId={page_id}"
    return {
        "source_type": "confluence",
        "url":         page_url,
        "title":       title,
        "labels":      ", ".join(labels),
        "content":     content,
        # Internal bookkeeping for incremental updates — ignored by ingestion.
        "_page_id":    page_id,
        "_version":    version,
    }


def crawl_all() -> list[dict]:
    """Crawl all configured Confluence spaces into ingestion-ready dicts.

    Returns:
        List of page dicts, or ``[]`` when Confluence env is not configured.
    """
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


def crawl_incremental(state: dict) -> tuple[list[dict], list[dict], int]:
    """Crawl only new and changed Confluence pages.

    Confluence's API returns each page's version number directly, so unlike
    the docs crawler we don't need to hash content to detect a change — we
    just compare the version number against the one seen last run. Skips the
    (cheap) markdownify conversion for pages whose version hasn't moved.

    Returns:
        new_pages:     pages whose ID was not seen in the previous run
        changed_pages: pages whose version number differs from last run
        unchanged:     count of pages skipped (no version change)
    """
    if not _is_configured():
        return [], [], 0

    page_versions: dict = state.get("confluence", {}).get("page_versions", {})

    new_pages: list[dict] = []
    changed_pages: list[dict] = []
    unchanged = 0

    for space_key in CONFLUENCE_SPACE_KEYS:
        print(f"\n  Checking Confluence space: {space_key} ...")
        pages = get_pages_in_space(space_key)
        print(f"  Found {len(pages)} pages")
        for page in pages:
            page_id = page.get("id", "")
            version = page.get("version", {}).get("number", 0)
            known_version = page_versions.get(page_id)

            if known_version == version:
                unchanged += 1
                time.sleep(CRAWL_DELAY_SECS)
                continue

            doc = page_to_dict(page)
            time.sleep(CRAWL_DELAY_SECS)
            if doc is None:
                continue

            if known_version is None:
                new_pages.append(doc)
            else:
                changed_pages.append(doc)

    return new_pages, changed_pages, unchanged


if __name__ == "__main__":
    if not _is_configured():
        print("Set CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN in .env first.")
        sys.exit(1)

    print(f"Crawling Confluence: {CONFLUENCE_URL} ...")
    results = crawl_all()

    with open(CONFLUENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(results)} pages -> {CONFLUENCE_FILE}")

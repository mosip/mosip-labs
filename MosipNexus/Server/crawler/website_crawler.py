"""
Configurable Website Crawler.

Crawls one or more websites defined in WEBSITE_URLS (comma-separated env var).
Each URL is crawled on its own origin; internal links are followed up to `depth` levels.
HTML is converted to Markdown via markdownify.

Supports incremental updates via content hashes.

Usage (full crawl):
    uv run python crawler/website_crawler.py

Set WEBSITE_URLS to override the default:
    WEBSITE_URLS=https://www.mosip.io,https://www.inji.io uv run python crawler/website_crawler.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import CRAWL_DELAY_SECS, HTTP_HEADERS, WEBSITE_FILE, WEBSITE_URLS


def _fetch_as_markdown(soup: BeautifulSoup) -> str:
    """Extract main content from parsed HTML and convert to Markdown."""
    content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("section")
        or soup.find("div", class_="container")
        or soup.body
    )
    return markdownify(
        str(content),
        heading_style="ATX",
        strip=["script", "style", "nav", "footer", "head"],
    )


def _crawl_single(base_url: str, depth: int = 3) -> list[dict]:
    """Depth-first crawl of a single base URL, staying on the same origin."""
    visited: set[str] = set()
    docs: list[dict] = []
    base = urlparse(base_url)

    def _crawl(url: str, d: int) -> None:
        if d == 0 or url in visited:
            return
        visited.add(url)
        try:
            response = requests.get(url, headers=HTTP_HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            content = _fetch_as_markdown(soup)
            if len(content.strip()) > 100:
                docs.append({"url": url, "content": content, "source_type": "website"})
                print(f"  OK   {url}")
            for a in soup.find_all("a", href=True):
                next_url = urljoin(url, a["href"]).split("#")[0]
                parsed = urlparse(next_url)
                if parsed.scheme in ("http", "https") and parsed.netloc == base.netloc:
                    _crawl(next_url, d - 1)
        except Exception as e:
            print(f"  SKIP {url}: {e}")
        time.sleep(CRAWL_DELAY_SECS)

    _crawl(base_url, depth)
    return docs


def crawl_website(urls: list[str] | None = None, depth: int = 3) -> list[dict]:
    """Crawl all configured website URLs and return combined page list."""
    targets = urls if urls is not None else WEBSITE_URLS
    all_docs: list[dict] = []
    for base_url in targets:
        base_url = base_url.strip()
        if not base_url:
            continue
        print(f"\nCrawling {base_url} ...")
        pages = _crawl_single(base_url, depth)
        print(f"  → {len(pages)} pages from {base_url}")
        all_docs.extend(pages)
    return all_docs


def crawl_incremental(state: dict) -> tuple[list[dict], list[dict], int]:
    """Return (new_pages, changed_pages, unchanged_count) for incremental ingestion."""
    from crawler.state import content_hash

    url_hashes: dict = state.get("website", {}).get("url_hashes", {})

    all_pages = crawl_website()

    new_pages: list[dict] = []
    changed_pages: list[dict] = []
    unchanged = 0

    for page in all_pages:
        content = page.get("content", "")
        if not content.strip():
            continue
        chash = content_hash(content)
        page["_hash"] = chash
        old_hash = url_hashes.get(page["url"])
        if old_hash is None:
            new_pages.append(page)
            print(f"NEW      {page['url']}")
        elif old_hash != chash:
            changed_pages.append(page)
            print(f"CHANGED  {page['url']}")
        else:
            unchanged += 1

    return new_pages, changed_pages, unchanged


if __name__ == "__main__":
    print(f"Configured URLs: {WEBSITE_URLS}")
    docs = crawl_website()
    with open(WEBSITE_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)
    print(f"\nCollected {len(docs)} total pages -> {WEBSITE_FILE}")

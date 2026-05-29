"""
Docs Crawler — Stage 1a.

Reads the MOSIP 1.2.0 sitemap, follows child sitemaps recursively, fetches
every documentation page, converts HTML to clean Markdown, and writes the
result to data/mosip_docs.json.  Run once before ingestion.
"""

import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    DOCS_FILE, DOCS_SITEMAP_URL, DOCS_BASE_URL,
    HTTP_HEADERS, CRAWL_DELAY_SECS,
)

_SM_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _get_locs(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    locs = root.findall(".//sm:loc", _SM_NS) or root.findall(".//loc")
    return [loc.text.strip() for loc in locs if loc.text]


def get_all_page_urls(sitemap_url: str, visited: set | None = None) -> list[str]:
    """Follow sitemap indexes recursively; return only actual page URLs."""
    if visited is None:
        visited = set()
    if sitemap_url in visited:
        return []
    visited.add(sitemap_url)

    try:
        res = requests.get(sitemap_url, headers=HTTP_HEADERS, timeout=30)
        res.raise_for_status()
    except Exception as e:
        print(f"  Sitemap fetch error {sitemap_url}: {e}")
        return []

    xml_text = res.text
    locs = _get_locs(xml_text)

    if "<sitemapindex" in xml_text:
        pages: list[str] = []
        for child in locs:
            pages.extend(get_all_page_urls(child, visited))
        return pages

    return [u for u in locs if not u.endswith(".xml")]


def fetch_page_as_markdown(url: str) -> str:
    """Fetch a single docs page and return its main content as ATX Markdown."""
    res = requests.get(url, headers=HTTP_HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_="markdown-section")
        or soup.find("div", class_="page-inner")
        or soup.body
        or soup
    )
    return markdownify(
        str(content),
        heading_style="ATX",
        strip=["script", "style", "nav", "footer", "head"],
    )


def crawl_fallback(depth: int = 3) -> list[dict]:
    """Depth-first crawl from DOCS_BASE_URL — used only when sitemap is absent."""
    visited, docs = set(), []

    def _crawl(url: str, d: int) -> None:
        if d == 0 or url in visited:
            return
        visited.add(url)
        try:
            content = fetch_page_as_markdown(url)
            if len(content.strip()) > 100:
                docs.append({"url": url, "content": content, "source_type": "docs"})
            soup = BeautifulSoup(
                requests.get(url, headers=HTTP_HEADERS, timeout=30).text, "html.parser"
            )
            for a in soup.find_all("a", href=True):
                next_url = urljoin(url, str(a["href"])).split("#")[0]
                cand = urlparse(next_url)
                base = urlparse(DOCS_BASE_URL)
                if cand.scheme in {"http", "https"} and cand.netloc == base.netloc:
                    _crawl(next_url, d - 1)
        except Exception as e:
            print(f"  SKIP {url}: {e}")

    _crawl(DOCS_BASE_URL, depth)
    return docs


def crawl_incremental(state: dict) -> tuple[list[dict], list[dict], int]:
    """Crawl only new and changed documentation pages.

    Fetches all sitemap URLs but compares content hashes against the previous
    run.  Only pages that are new or whose content changed are returned —
    unchanged pages are skipped entirely, avoiding redundant re-embedding.

    Returns:
        new_pages:     pages not seen in the previous run
        changed_pages: pages whose content hash differs from last run
        unchanged:     count of pages skipped (no change detected)
    """
    from crawler.state import content_hash

    url_hashes: dict = state.get("docs", {}).get("url_hashes", {})

    print(f"Fetching sitemap from {DOCS_SITEMAP_URL} ...")
    all_urls = get_all_page_urls(DOCS_SITEMAP_URL)
    if not all_urls:
        print("Sitemap returned no pages.")
        return [], [], 0

    print(f"Found {len(all_urls)} URLs — checking for new / changed pages...")
    new_pages: list[dict] = []
    changed_pages: list[dict] = []
    unchanged = 0

    for i, url in enumerate(all_urls, 1):
        known_hash = url_hashes.get(url)
        try:
            content = fetch_page_as_markdown(url)
            if len(content.strip()) < 100:
                continue
            chash = content_hash(content)
            page = {"url": url, "content": content, "source_type": "docs", "_hash": chash}

            if known_hash is None:
                new_pages.append(page)
                print(f"[{i}/{len(all_urls)}] NEW     {url}")
            elif known_hash != chash:
                changed_pages.append(page)
                print(f"[{i}/{len(all_urls)}] CHANGED {url}")
            else:
                unchanged += 1
                if unchanged % 50 == 0:
                    print(f"[{i}/{len(all_urls)}] ... {unchanged} unchanged so far")
        except Exception as e:
            print(f"[{i}/{len(all_urls)}] ERR     {url}: {e}")
        time.sleep(CRAWL_DELAY_SECS)

    return new_pages, changed_pages, unchanged


if __name__ == "__main__":
    print(f"Fetching sitemap from {DOCS_SITEMAP_URL} ...")
    urls = get_all_page_urls(DOCS_SITEMAP_URL)

    if urls:
        print(f"Found {len(urls)} page URLs in sitemap")
    else:
        print("Sitemap returned no pages — falling back to recursive crawl")

    docs: list[dict] = []

    if urls:
        for i, url in enumerate(urls, 1):
            try:
                content = fetch_page_as_markdown(url)
                if len(content.strip()) > 100:
                    docs.append({"url": url, "content": content, "source_type": "docs"})
                    print(f"[{i}/{len(urls)}] OK   {url}")
                else:
                    print(f"[{i}/{len(urls)}] SKIP (empty) {url}")
            except Exception as e:
                print(f"[{i}/{len(urls)}] ERR  {url}: {e}")
            time.sleep(CRAWL_DELAY_SECS)
    else:
        docs = crawl_fallback(depth=3)

    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(docs)} doc pages -> {DOCS_FILE}")

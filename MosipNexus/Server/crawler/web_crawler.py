"""
Generic Web Crawler.

Crawls sitemap.xml first; falls back to recursive same-origin depth crawl.
Used by esignet_crawler.py and can be invoked standalone:

    uv run python crawler/web_crawler.py --base-url https://docs.esignet.io --output data/esignet_docs.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import defusedxml.ElementTree as ET
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import CRAWL_DELAY_SECS, HTTP_HEADERS

_SM_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _get_locs(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    locs = root.findall(".//sm:loc", _SM_NS) or root.findall(".//loc")
    return [loc.text.strip() for loc in locs if loc.text]


def get_all_page_urls(sitemap_url: str, visited: Optional[set] = None) -> list[str]:
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
    try:
        locs = _get_locs(xml_text)
    except ET.ParseError as e:
        print(f"  Sitemap parse error {sitemap_url}: {e}")
        return []

    if "<sitemapindex" in xml_text:
        pages: list[str] = []
        for child in locs:
            pages.extend(get_all_page_urls(child, visited))
        return pages

    return [u for u in locs if not u.endswith(".xml")]


def fetch_page(url: str) -> tuple[str, str]:
    """Fetch a page and return (title, cleaned_text)."""
    res = requests.get(url, headers=HTTP_HEADERS, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    for tag in soup(["script", "style", "header", "footer", "nav", "noscript"]):
        tag.decompose()

    content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_="markdown-section")
        or soup.find("div", class_="page-inner")
        or soup.body
        or soup
    )

    text = content.get_text(separator="\n", strip=True)
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    return title, "\n".join(lines)


def crawl_fallback(base_url: str, depth: int = 3) -> list[dict]:
    """Depth-first crawl from base_url, staying on the same origin."""
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
            title = soup.title.get_text(strip=True) if soup.title else ""
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            content = soup.get_text("\n", strip=True)
            if len(content.strip()) > 100:
                docs.append({"url": url, "title": title, "content": content})
            for a in soup.find_all("a", href=True):
                next_url = urljoin(url, str(a["href"])).split("#")[0]
                cand = urlparse(next_url)
                if cand.scheme in {"http", "https"} and cand.netloc == base.netloc:
                    time.sleep(CRAWL_DELAY_SECS)
                    _crawl(next_url, d - 1)
        except Exception as e:
            print(f"  SKIP {url}: {e}")

    _crawl(base_url, depth)
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generic Web Crawler")
    parser.add_argument("--base-url", required=True, help="Base URL to crawl")
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args()

    sitemap_url = args.base_url.rstrip("/") + "/sitemap.xml"
    print(f"Fetching sitemap from {sitemap_url} ...")
    urls = get_all_page_urls(sitemap_url)

    docs: list[dict] = []
    if urls:
        print(f"Found {len(urls)} page URLs in sitemap")
        for i, url in enumerate(urls, 1):
            try:
                title, content = fetch_page(url)
                if len(content.strip()) > 100:
                    docs.append({"url": url, "title": title, "content": content})
                    print(f"[{i}/{len(urls)}] OK   {url}")
                else:
                    print(f"[{i}/{len(urls)}] SKIP (empty) {url}")
            except Exception as e:
                print(f"[{i}/{len(urls)}] ERR  {url}: {e}")
            time.sleep(CRAWL_DELAY_SECS)
    else:
        print("Sitemap returned no pages — falling back to recursive crawl")
        docs = crawl_fallback(args.base_url, depth=3)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(docs)} pages -> {args.output}")


if __name__ == "__main__":
    main()

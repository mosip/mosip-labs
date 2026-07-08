"""
eSignet Documentation Crawler.

Uses the generic web crawler functions to crawl eSignet documentation
and supports incremental updates using content hashes.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    CRAWL_DELAY_SECS,
    ESIGNET_BASE_URL,
    ESIGNET_FILE,
)
from crawler.state import content_hash
from crawler.web_crawler import (
    crawl_fallback,
    fetch_page,
    get_all_page_urls,
)


def crawl_esignet() -> list[dict]:
    """Crawl all eSignet documentation pages and write them to JSON."""
    sitemap_url = ESIGNET_BASE_URL.rstrip("/") + "/sitemap.xml"
    urls = get_all_page_urls(sitemap_url)

    docs: list[dict] = []

    if urls:
        for i, url in enumerate(urls, 1):
            try:
                title, content = fetch_page(url)
                if len(content.strip()) > 100:
                    docs.append(
                        {
                            "url": url,
                            "title": title,
                            "content": content,
                        }
                    )
                    print(f"[{i}/{len(urls)}] OK   {url}")
            except Exception as e:
                print(f"[{i}/{len(urls)}] ERR  {url}: {e}")
            time.sleep(CRAWL_DELAY_SECS)
    else:
        docs = crawl_fallback(ESIGNET_BASE_URL, depth=3)

    with open(ESIGNET_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    return docs


def crawl_incremental(state: dict) -> tuple[list[dict], list[dict], int]:
    """Return new and changed eSignet documentation pages."""
    url_hashes: dict = state.get("esignet", {}).get("url_hashes", {})

    sitemap_url = ESIGNET_BASE_URL.rstrip("/") + "/sitemap.xml"
    print(f"Fetching sitemap from {sitemap_url} ...")
    urls = get_all_page_urls(sitemap_url)

    if not urls:
        print("Sitemap returned no pages — falling back to recursive crawl")
        fallback_pages = crawl_fallback(ESIGNET_BASE_URL, depth=3)

        new_pages: list[dict] = []
        changed_pages: list[dict] = []
        unchanged = 0

        for page in fallback_pages:
            content = page.get("content", "")
            if not content.strip():
                continue

            chash = content_hash(content)
            page["source_type"] = "esignet"
            page["_hash"] = chash
            known_hash = url_hashes.get(page["url"])

            if known_hash is None:
                new_pages.append(page)
            elif known_hash != chash:
                changed_pages.append(page)
            else:
                unchanged += 1

        return new_pages, changed_pages, unchanged

    new_pages: list[dict] = []
    changed_pages: list[dict] = []
    unchanged = 0

    for i, url in enumerate(urls, 1):
        known_hash = url_hashes.get(url)

        try:
            title, content = fetch_page(url)
            if len(content.strip()) < 100:
                continue

            chash = content_hash(content)
            page = {
                "url": url,
                "title": title,
                "content": content,
                "source_type": "esignet",
                "_hash": chash,
            }

            if known_hash is None:
                new_pages.append(page)
                print(f"[{i}/{len(urls)}] NEW     {url}")
            elif known_hash != chash:
                changed_pages.append(page)
                print(f"[{i}/{len(urls)}] CHANGED {url}")
            else:
                unchanged += 1

        except Exception as e:
            print(f"[{i}/{len(urls)}] ERR     {url}: {e}")

        time.sleep(CRAWL_DELAY_SECS)

    return new_pages, changed_pages, unchanged


if __name__ == "__main__":
    crawl_esignet()

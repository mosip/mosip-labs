"""
Community Crawler — Stage 1b.

Uses the Discourse JSON API to crawl ``COMMUNITY_BASE_URL``.
For each topic it extracts the question, all answers, the accepted answer,
tags, vote counts, and the topic URL. Output: ``data/{PRODUCT_SLUG}_community.json``.

Discourse API endpoints used:
  GET /latest.json?page=N   — paginated list of topic stubs
  GET /t/{id}.json           — full topic with all posts

Public crawl helpers: ``get_topic_ids``, ``fetch_topic``, ``get_new_topic_ids``,
``crawl_incremental`` (for ``run_update.py``).
"""

import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    COMMUNITY_FILE, COMMUNITY_BASE_URL, COMMUNITY_API_ROOT,
    HTTP_HEADERS, CRAWL_DELAY_SECS, COMMUNITY_MAX_PAGES, COMMUNITY_MIN_POSTS,
)


def _list_url(page: int) -> str:
    """Build the correct Discourse listing URL for root or category-based base URLs.

    Root forum:  https://community.mosip.io  → /latest.json?page=N
    Category:    https://community.mosip.io/c/inji/16  → /c/inji/16.json?page=N
    """
    b = COMMUNITY_BASE_URL.rstrip("/")
    import re
    if re.search(r"/c/[^/]+/\d+$", b):
        return f"{b}.json?page={page}"
    return f"{b}/latest.json?page={page}"


def _html_to_text(html: str) -> str:
    """Convert Discourse cooked HTML to clean plain text."""
    return markdownify(html, heading_style="ATX", strip=["script", "style"]).strip()


def get_topic_ids(max_pages: int = COMMUNITY_MAX_PAGES) -> list[int]:
    """Paginate ``/latest.json`` and collect topic IDs with enough posts.

    Args:
        max_pages: Maximum Discourse list pages to scan.

    Returns:
        Topic id list (order follows Discourse newest-first pagination).
    """
    ids: list[int] = []
    for page in range(max_pages):
        url = _list_url(page)
        try:
            res = requests.get(url, headers=HTTP_HEADERS, timeout=30)
            res.raise_for_status()
            topics = res.json().get("topic_list", {}).get("topics", [])
            if not topics:
                break
            for t in topics:
                if t.get("posts_count", 0) > COMMUNITY_MIN_POSTS:
                    ids.append(t["id"])
            print(f"  Page {page}: {len(topics)} topics (total so far: {len(ids)})")
        except Exception as e:
            print(f"  Page {page} error: {e}")
        time.sleep(CRAWL_DELAY_SECS)
    return ids


def fetch_topic(topic_id: int) -> dict | None:
    """Fetch a full topic and structure it for ingestion.

    Returns a dict with:
      title, url, tags, question, answers (list), accepted_answer (str|None)
    Returns None if the topic cannot be fetched or has no content.
    """
    url = f"{COMMUNITY_API_ROOT}/t/{topic_id}.json"
    try:
        res = requests.get(url, headers=HTTP_HEADERS, timeout=30)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"    ERR topic {topic_id}: {e}")
        return None

    title = data.get("title", "")
    raw_tags = data.get("tags", [])
    tags = [t["name"] if isinstance(t, dict) else str(t) for t in raw_tags]
    slug  = data.get("slug", str(topic_id))
    topic_url = f"{COMMUNITY_API_ROOT}/t/{slug}/{topic_id}"

    posts = data.get("post_stream", {}).get("posts", [])
    if not posts:
        return None

    question_html = posts[0].get("cooked", "")
    question_text = _html_to_text(question_html)

    answers = []
    accepted_answer: str | None = None

    for post in posts[1:]:
        text = _html_to_text(post.get("cooked", "")).strip()
        if not text:
            continue
        vote_count = post.get("like_count", 0)
        is_accepted = bool(post.get("accepted_answer", False))
        answers.append({
            "text": text,
            "vote_count": vote_count,
            "accepted": is_accepted,
        })
        if is_accepted and accepted_answer is None:
            accepted_answer = text

    # Sort: accepted first, then by votes descending
    answers.sort(key=lambda a: (not a["accepted"], -a["vote_count"]))

    return {
        "source_type": "community",
        "url": topic_url,
        "title": title,
        "tags": tags,
        "question": question_text,
        "answers": answers,
        "accepted_answer": accepted_answer,
    }


def get_new_topic_ids(max_topic_id: int) -> list[int]:
    """Return only topic IDs created after max_topic_id.

    Discourse returns topics newest-first, so pagination stops as soon as all
    topics on a page are older than the last known ID — no need to scan all pages.
    """
    new_ids: list[int] = []
    for page in range(COMMUNITY_MAX_PAGES):
        url = _list_url(page)
        try:
            res = requests.get(url, headers=HTTP_HEADERS, timeout=30)
            res.raise_for_status()
            topics = res.json().get("topic_list", {}).get("topics", [])
        except Exception as e:
            print(f"  Page {page} error: {e}")
            break

        if not topics:
            break

        page_ids = [t["id"] for t in topics if t.get("posts_count", 0) > COMMUNITY_MIN_POSTS]
        new_on_page = [tid for tid in page_ids if tid > max_topic_id]
        new_ids.extend(new_on_page)

        # If every topic on this page is already known, stop paginating
        if len(new_on_page) < len(page_ids):
            print(f"  Reached known topics at page {page} — stopping.")
            break

        time.sleep(CRAWL_DELAY_SECS)

    return new_ids


def crawl_incremental(state: dict) -> list[dict]:
    """Fetch only community topics newer than the last crawl run.

    Uses the Discourse newest-first ordering to stop pagination early,
    making incremental runs take seconds instead of minutes.

    Args:
        state: Crawl state dict (reads ``community.max_topic_id``).

    Returns:
        List of structured topic dicts ready for ingestion.
    """
    max_topic_id: int = state.get("community", {}).get("max_topic_id", 0)
    print(f"Fetching new community topics (last known ID: {max_topic_id}) ...")

    new_ids = get_new_topic_ids(max_topic_id)
    if not new_ids:
        print("  No new topics found.")
        return []

    print(f"  Found {len(new_ids)} new topics — fetching...")
    results: list[dict] = []
    for i, tid in enumerate(new_ids, 1):
        topic = fetch_topic(tid)
        if topic and topic["question"].strip():
            results.append(topic)
            print(f"  [{i}/{len(new_ids)}] OK   {topic['url']}")
        time.sleep(CRAWL_DELAY_SECS)

    return results


if __name__ == "__main__":
    print(f"Crawling community forum at {COMMUNITY_BASE_URL} ...")
    topic_ids = get_topic_ids()
    print(f"\nFetching {len(topic_ids)} topics ...")

    results: list[dict] = []
    for i, tid in enumerate(topic_ids, 1):
        topic = fetch_topic(tid)
        if topic and topic["question"].strip():
            results.append(topic)
            print(f"[{i}/{len(topic_ids)}] OK   {topic['url']}")
        else:
            print(f"[{i}/{len(topic_ids)}] SKIP {tid}")
        time.sleep(CRAWL_DELAY_SECS)

    with open(COMMUNITY_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nCollected {len(results)} topics -> {COMMUNITY_FILE}")

"""
Crawl state — persists between runs to enable incremental updates.

Stored in data/crawl_state.json:
  docs.url_hashes            : {url -> MD5 of last-fetched content}
  community.max_topic_id     : highest forum topic ID seen so far
  github.<repo>.max_issue_number  : highest issue number seen per repo
  confluence.page_versions   : {page_id -> last-seen Confluence version number}
  jira.<project>.seen_keys   : issue keys already ingested for that project
  jira.<project>.last_run    : watermark used as the JQL "updated >=" filter
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DATA_DIR

STATE_FILE = DATA_DIR / "crawl_state.json"

_DEFAULT: dict = {
    "docs":      {"url_hashes": {}, "last_run": None},
    "community": {"max_topic_id": 0, "last_run": None},
}


def load() -> dict:
    """Load persisted crawl state, returning defaults if no state file exists."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return _DEFAULT.copy()
    return _DEFAULT.copy()


def save(state: dict) -> None:
    """Persist crawl state to disk atomically to guard against partial writes."""
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_FILE)


def content_hash(text: str) -> str:
    """MD5 of page content — used to detect changes between crawl runs."""
    return hashlib.md5(text.encode()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

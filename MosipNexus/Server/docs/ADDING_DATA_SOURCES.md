# Adding a new data source

Nexus Server indexes multiple knowledge sources (docs, community, GitHub,
code, Confluence, Jira). Each source follows the same pipeline:

```text
Crawler  →  JSON file in Server/data/  →  ingestion/store.py  →  pgvector collection
                                                              ↓
                                                    retrieval/retriever.py
```

Use this checklist when you add a seventh (or nth) source — for example Slack
exports, a second docs site, or an internal wiki.

---

## Overview of existing sources

| Source | Crawler | JSON (default slug `mosip`) | Collection | In `run_update.py`? | Searched by retriever? |
| --- | --- | --- | --- | --- | --- |
| Docs | `crawler/docs_crawler.py` | `*_docs.json` | `*_docs` | Yes | Yes |
| Community | `crawler/community_crawler.py` | `*_community.json` | `*_community` | Yes | Yes |
| GitHub issues | `crawler/github_crawler.py` | `*_github.json` | `*_github` | Yes | Yes |
| Source code | `crawler/code_crawler.py` | `*_code.json` | `*_code` | No (full crawl) | Yes |
| Confluence | `crawler/confluence_crawler.py` | `*_confluence.json` | `*_confluence` | Yes (if configured) | Wire-up if missing |
| Jira | `crawler/jira_crawler.py` | `*_jira.json` | `*_jira` | Yes (if configured) | Wire-up if missing |

File and collection names are prefixed by `PRODUCT_SLUG` (env), so the same
code works for MOSIP (`mosip_*`) or Inji (`inji_*`).

---

## Step-by-step: add `my_source`

### 1. Decide configuration (env)

In `Server/config/settings.py` add:

```python
MY_SOURCE_BASE_URL = os.getenv("MY_SOURCE_BASE_URL", "")
MY_SOURCE_FILE = DATA_DIR / f"{PRODUCT_SLUG}_my_source.json"
MY_SOURCE_COLLECTION = os.getenv("MY_SOURCE_COLLECTION", f"{PRODUCT_SLUG}_my_source")
MY_SOURCE_RETRIEVAL_K = int(os.getenv("MY_SOURCE_RETRIEVAL_K", "6"))
# Auth / filters as needed…
```

Document the new variables in `Server/.env.example` and `Server/k8s/02-secret.yaml`.

### 2. Write a crawler

Create `Server/crawler/my_source_crawler.py` that:

1. Reads settings (URL, tokens, limits)  
2. Fetches remote content  
3. Writes a JSON **list** of objects with at least:

```json
[
  {
    "url": "https://example.com/page",
    "title": "Human readable title",
    "content": "Plain text (or markdown) body used for embedding",
    "source_type": "my_source"
  }
]
```

Optional useful metadata: `tags`, `updated_at`, `accepted`, `repo`, `path`.

Reuse helpers in `crawler/utils.py` (e.g. `table_to_prose`) and incremental
state in `crawler/state.py` when possible.

CLI entry pattern (match other crawlers):

```python
if __name__ == "__main__":
    crawl()  # writes MY_SOURCE_FILE
```

### 3. Ingest into pgvector

In `Server/ingestion/store.py`:

1. Add `prepare_my_source(docs) -> list[Document]` that maps each JSON row to a
   LangChain `Document` with `page_content` + metadata (`source`, `title`,
   `source_type`, …).  
2. Call it from the main ingest flow and upsert into `MY_SOURCE_COLLECTION`
   (same chunking / embedding pattern as existing `prepare_*` functions).

Run:

```powershell
$env:PYTHONPATH = ".\Server"
uv run python Server/ingestion/store.py
```

### 4. Wire retrieval

In `Server/retrieval/retriever.py`:

1. Load the new PGVector store (see `_try_load_optional_store` pattern).  
2. Include it in the MMR / merge / scoring path inside `retrieve()`.  
3. Expose counts in `get_collection_counts()` so `/health` and MCP stay accurate.

**Important:** Confluence/Jira historically could be ingested but omitted from
`retrieve()` — always confirm the new store is merged into search results.

### 5. Incremental updates (optional but recommended)

1. Add `crawl_incremental_*` (or extend the crawler) using `crawler/state.py`.  
2. Call it from `Server/run_update.py` next to the other sources.  
3. Persist cursors (max id, content hash, `updated >=` timestamp) in
   `data/crawl_state.json`.

### 6. Surface in API / MCP / UI (optional)

| Layer | Change |
| --- | --- |
| API | Usually none — `/chat` and `/search` use `retrieve()` |
| MCP | Update `list_knowledge_sources()` (and tool docs) in `mcp_server/server.py` — tool name is `search_knowledge` |
| UI | Add an icon/label in `UI/app/app.py` `_SVG_ICON` / sidebar source list |

UI must **not** import the new crawler — only the Server does.

### 7. Tests

Add a tiny fixture under `Server/tests/data/` and a unit test that
`prepare_my_source` produces documents with the expected metadata.

---

## Configuring for MOSIP vs Inji (no new source)

You do **not** need a new data source type when switching products. Set env:

```env
PRODUCT_NAME=Inji Nexus
PRODUCT_SHORT=Inji
PRODUCT_SLUG=inji
DOCS_BASE_URL=https://docs.example-inji.org
COMMUNITY_BASE_URL=https://community.example-inji.org
GITHUB_ORG=inji
GITHUB_REPOS=inji/repo-a,inji/repo-b
```

Then crawl + ingest so `Server/data/inji_*.json` and `inji_*` collections exist.

---

## Quick reference — files to touch

| Step | File(s) |
| --- | --- |
| Config | `Server/config/settings.py`, `Server/.env.example`, `Server/k8s/02-secret.yaml` |
| Crawl | `Server/crawler/<name>_crawler.py` (+ `utils.py` / `state.py`) |
| Ingest | `Server/ingestion/store.py` |
| Retrieve | `Server/retrieval/retriever.py` |
| Nightly | `Server/run_update.py` |
| Docs / MCP / UI labels | `mcp_server/server.py`, `UI/app/app.py` (labels only) |

See also: [DATABASE_SETUP.md](./DATABASE_SETUP.md) for DB prerequisites before
ingest.

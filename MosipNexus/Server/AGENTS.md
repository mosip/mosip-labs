# AGENTS.md — Server

Instructions for AI coding agents working in `Server/`. See also the root
[`../AGENTS.md`](../AGENTS.md) for repo-wide rules (the UI/Server HTTP boundary
in particular).

Python 3.13 FastAPI backend: RAG pipeline, crawlers, ingestion, Postgres/pgvector,
and an MCP server for Claude Desktop. The same binary serves **MOSIP**, **Inji**,
or a white-label `generic` profile by product selection, not by forking code.

## Layout

| Path | Responsibility |
| --- | --- |
| `api/main.py` | FastAPI routes: `/chat`, `/search`, `/similar`, `/config`, `/session*`, `/feedback`, `/stats`, `/notify`, `/batch`, `/health`. Thin — delegates to `controllers/`. |
| `api/schemas.py`, `api/errors.py`, `api/middleware.py` | Pydantic request/response models, typed error envelope, product-mode + logging middleware. |
| `controllers/` | Business logic: `chat.py` (run a turn), `sessions.py`, `feedback.py`, `stats.py`. |
| `chain/query_engine.py` | Core RAG chain: greeting short-circuit → optional follow-up condense → retrieve → pack context → LLM answer → web fallback. |
| `chain/confidence/` | Confidence scoring + source weighting for answers. |
| `chain/context_budget.py`, `token_usage.py`, `summarizer.py` | Context packing/trimming, token accounting, ingestion-time summarization. |
| `retrieval/retriever.py` | Hybrid MMR search across pgvector collections in parallel; query classification helpers (`is_code_query`, `is_error_code_query`). |
| `retrieval/dedup.py` | Duplicate community-question detection (`/similar`). |
| `ingestion/store.py` | Chunk → embed → upsert into `langchain_pg_embedding` (pgvector). |
| `crawler/` | One crawler per source: `docs_crawler.py`, `community_crawler.py`, `github_crawler.py`, `code_crawler.py`, `confluence_crawler.py`, `jira_crawler.py`, `esignet_crawler.py`, `web_crawler.py`, `website_crawler.py`. Write JSON to `data/{PRODUCT_SLUG}_*.json`. |
| `config/settings.py` | All env var bindings (non-product-scoped: PG, concurrency, LLM limits, SMTP…). |
| `config/products.py` | Per-request product profiles (`mosip`/`inji`/`generic`) via `ContextVar`; `set_current_product()` / `current_product()`. |
| `db/models.py`, `db/engine.py`, `db/crud/`, `db/repositories/` | SQLAlchemy models + Alembic-managed app tables (sessions, feedback, query_events) — separate from the pgvector `langchain_pg_*` tables. |
| `alembic/` | DB migrations for app tables only (not the vector store). |
| `memory/session.py` | Server-side chat session/turn tracking. |
| `notifications/email_notifier.py` | Optional SMTP alerts (expert escalation / unanswered). |
| `mcp_server/server.py` | FastMCP server exposing `search_knowledge`, `list_knowledge_sources`, `list_products` for Claude Desktop — retrieval only, no LLM. |
| `run_update.py` | Incremental crawl + re-embed (also used by the K8s CronJob). |
| `run_product.py` | Helper to run crawl/ingest for a specific product. |
| `tests/` | `unittest`-style tests (see `test_web_crawler.py`); `tests/data/` has fixture JSON. |
| `k8s/` | Namespace, postgres, secrets, API deployment, ingress, cronjob, initial-ingest job manifests (raw `kubectl apply -f`). Helm equivalent lives at repo root `helm/nexus-server/` — see [`../AGENTS.md`](../AGENTS.md). |

## RAG data flow

1. UI/API client `POST /chat` → `controllers.chat.run_chat_turn()`.
2. Question embedded once → parallel search across the active product's
   pgvector collections (`RETRIEVAL_PARALLELISM`).
3. Context packed under `MAX_CONTEXT_CHARS` / `MAX_CONTEXT_DOCS` → LLM answers
   with the caller's BYOK key.
4. `[NO_DOC_SOURCE]` / empty retrieval → capped DuckDuckGo web fallback.
5. Turn + `query_events` persisted to Postgres app tables.

## Key invariants

- **BYOK only** — chat/batch endpoints require the caller's `llm_api_key`
  (Groq, Anthropic, OpenAI, or xAI/Grok). The server never falls back to a
  server-side key for user-facing chat; `GROQ_API_KEY` in `.env` is used only
  for internal ingestion summarization.
- **Product is per-request, not per-process** for chat/MCP — resolved via
  `set_current_product()` (a `ContextVar`), driven by `X-Nexus-Product` header
  / `product` field / MCP tool arg. Crawl/ingest jobs, by contrast, are still
  driven by the process-level `PRODUCT_SLUG` env var.
- **Two separate Postgres schemas share one DB**: Alembic-managed app tables
  (sessions/feedback/query_events) vs. LangChain-managed `langchain_pg_*`
  vector tables (not in Alembic — don't add migrations for them).
- **Concurrency control**: `/chat`, `/batch`, `/search` acquire a slot from the
  `MAX_CONCURRENT_CHATS` semaphore; saturation returns `503` with `Retry-After`.

## Running

```bash
./run.sh          # Linux/macOS — creates .venv, syncs deps, serves :8010
run.bat           # Windows
```

Or manually:

```bash
uv sync
export PYTHONPATH=$(pwd)
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Migrations: `uv run alembic upgrade head` (Docker's `entrypoint.sh` does this
automatically before serving).

## Tests

```bash
uv run python -m unittest discover tests
# or: pytest tests/  (if pytest installed)
```

No CI workflow is configured — run this locally before handing off work.

## Conventions

- Google-style docstrings on public functions, e.g.:
  ```python
  def retrieve(query: str, k: int = 8) -> tuple[list[Document], str]:
      """Search collections and return documents plus confidence.

      Args:
          query: User or condensed search string.
          k: Max chunks per primary collection.

      Returns:
          (documents, confidence) where confidence is high|medium|low.
      """
  ```
- Dependency source of truth is `pyproject.toml` (+ `uv.lock`); `requirements.txt`
  is a generated mirror for `pip install -r`. Keep them in sync if you add a dep.
- No linter/formatter config is checked in — match existing style.
- New app-level DB table → SQLAlchemy model in `db/models.py` + Alembic
  revision (see `docs/DATABASE_LAYER.md`).
- New crawl source → crawler → `data/*.json` → `ingestion/store.py` →
  `retrieval/retriever.py` → optionally `run_update.py` + MCP
  `list_knowledge_sources` (see `docs/ADDING_DATA_SOURCES.md`).
- New env var → document in `docs/ENVIRONMENT.md` and add to `.env.example`.

## Where to read more

- [`README.md`](README.md) — full Server guide (Docker, K8s, env vars, MCP).
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Server-only architecture.
- [`docs/DATABASE_SETUP.md`](docs/DATABASE_SETUP.md), [`docs/DATABASE_LAYER.md`](docs/DATABASE_LAYER.md)
- [`docs/MCP_SERVER.md`](docs/MCP_SERVER.md)
- [`docs/ADDING_DATA_SOURCES.md`](docs/ADDING_DATA_SOURCES.md)
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- [`../AGENTS.md`](../AGENTS.md) — repo-wide rules.

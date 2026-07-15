# Server architecture

How the Nexus Server pieces fit together: HTTP request flow, RAG pipeline,
database split (app tables vs LangChain/pgvector), and the MCP retrieval path.

---

## High-level layout

```text
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  React UI   │     │ Claude /    │     │  Other HTTP      │
│  (Vite)     │     │ MCP client  │     │  clients         │
└──────┬──────┘     └──────┬──────┘     └────────┬─────────┘
       │ REST              │ MCP tools           │ REST
       ▼                   ▼                     ▼
┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ api/main.py      │  │ mcp_server/     │  │ Same FastAPI     │
│ (FastAPI)        │  │ server.py       │  │ endpoints        │
└────────┬─────────┘  └────────┬────────┘  └────────┬─────────┘
         │                     │                      │
         │    chain.query_engine.ask()                │
         │    (LLM + RAG)      │                      │
         │                     │ retrieve() only      │
         └──────────┬──────────┴──────────────────────┘
                    ▼
         retrieval.retriever  →  PostgreSQL + pgvector
                    │
         controllers → db.crud → db.repositories → app tables
```

| Surface | LLM | Role |
| --- | --- | --- |
| `POST /chat`, `/batch` | Caller BYOK (Groq / Anthropic / OpenAI) | Full RAG answer |
| `POST /search`, `/similar` | None | Retrieval / dedup only |
| MCP `search_knowledge` | Client-side (e.g. Claude Desktop) | Retrieval only |

---

## Request flow (`POST /chat`)

1. **Capacity** — `_chat_slot()` acquires an in-process semaphore (`MAX_CONCURRENT_CHATS`). If full → **503** + `Retry-After`.
2. **Chat controller** — `controllers.chat.run_chat_turn` ensures a session, hydrates memory, calls `ask()`, persists the turn, and records stats.
3. **RAG** — `chain.query_engine.ask(...)` with chat history + caller `llm_api_key`.
4. **Notify (optional)** — on low confidence, queue SMTP via `notifications.email_notifier`.
5. **Response** — answer, sources, confidence, similar community titles, `session_id`.

Related endpoints:

| Endpoint | Flow notes |
| --- | --- |
| `POST /batch` | `controllers.chat.run_batch` — sequential RAG with shared history, then turns committed |
| `POST /search` | `retrieve()` only — no LLM |
| `POST /similar` | `find_similar_question()` against community index |
| `POST /feedback` | Validates session/turn, inserts `feedback` |
| `GET /health` | `ensure_ready()` + pgvector collection counts + active session count |
| `GET /stats` | `controllers.stats.get_dashboard_stats` |

Layering rule: **API → controllers → db.crud → repositories → SQLAlchemy**. Routes never run raw SQL. Controllers never import ``api.*``.

---

## RAG pipeline (`chain.query_engine.ask`)

```text
question
   │
   ├─ greeting / meta? ──► short chat reply (no retrieval)
   │
   ├─ condense with history (LCEL) ──► standalone search query
   │
   ├─ retrieve(standalone) ──► MMR across collections + confidence
   │
   ├─ no docs? ──► DuckDuckGo web fallback or source_type=none
   │
   ├─ LLM answer grounded in context (system prompt varies by
   │     error-code / code / env-debug heuristics)
   │
   ├─ [NO_DOC_SOURCE] in answer? ──► web fallback again
   │
   └─ classify source_type, trim sources, return dict
```

Key modules:

| Module | Responsibility |
| --- | --- |
| `retrieval/retriever.py` | Shared embedder, pooled engine, parallel MMR, error-code SQL boost |
| `retrieval/dedup.py` | Community near-duplicate check (`DEDUP_THRESHOLD`) |
| `chain/query_engine.py` | Condenser, prompts, LLM factory, web fallback |
| `memory/session.py` | In-request message list for the condenser (DB is source of truth) |

Confidence labels (`high` / `medium` / `low`) come from the best MMR relevance score against `CONFIDENCE_HIGH` / `CONFIDENCE_MEDIUM`, with a downgrade if the model admits missing info.

---

## Database split

One Postgres database, two ownership domains:

### App tables (Alembic / `db.models`)

| Table | Purpose |
| --- | --- |
| `chat_sessions` | Session metadata, language, idle / cleared timestamps |
| `chat_turns` | Ordered Q&A + sources JSON per turn |
| `feedback` | Positive/negative ratings linked to session + turn |
| `query_events` | Per-answer analytics for `/stats` |

Migrated with Alembic (`alembic/versions/`). See [DATABASE_LAYER.md](./DATABASE_LAYER.md).

### LangChain / pgvector tables (ingestion-owned)

| Table / concept | Purpose |
| --- | --- |
| `langchain_pg_collection` | Named collections (`{PRODUCT_SLUG}_docs`, `_community`, …) |
| `langchain_pg_embedding` | Chunk text + vectors + `cmetadata` |

Written by `ingestion/store.py` and `run_update.py` via `langchain_postgres.PGVector`. **Never** autogenerate Alembic drops against these tables.

Both paths share `db.engine.get_engine()` (pooled SQLAlchemy) so app repos and vector search reuse one pool.

---

## Ingestion path (offline)

```text
crawler/*.py  →  data/{PRODUCT_SLUG}_*.json
                      │
                      ▼
              ingestion/store.py   (full rebuild)
              run_update.py        (incremental delta)
                      │
                      ▼
              langchain_pg_* collections
```

`crawler/state.py` persists `data/crawl_state.json` so incremental runs only re-embed new/changed content. If `PIPELINE_VERSION` (hash of embed model + chunk settings) changes, `run_update.py` forces a full rebuild.

---

## MCP path

```text
MCP client (Claude Desktop, etc.)
        │  stdio or SSE (MCP_TRANSPORT / MCP_PORT)
        ▼
mcp_server/server.py
        │  search_knowledge / list_knowledge_sources
        ▼
retrieval.retriever.retrieve()   ← no server-side chat LLM
```

Details: [MCP_SERVER.md](./MCP_SERVER.md).

---

## Configuration

All tuneables bind in `config/settings.py` from `Server/.env` (and process env). See [ENVIRONMENT.md](./ENVIRONMENT.md).

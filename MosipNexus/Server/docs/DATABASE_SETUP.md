# Database setup — what to change before running Nexus

This guide lists every database-related setting you must review before the
first crawl, ingest, or chat session. The Server talks to **PostgreSQL 16 +
pgvector** only. The UI never connects to the database.

---

Tables:

| Owner | Tables | How created |
| --- | --- | --- |
| **App (Alembic)** | `chat_sessions`, `chat_turns`, `feedback`, `query_events` | `uv run alembic upgrade head` |
| **LangChain PGVector** | `langchain_pg_collection`, `langchain_pg_embedding` | Auto on first ingest — do **not** manage with Alembic |

---

## 1. What you need

| Item | Requirement |
| --- | --- |
| Engine | PostgreSQL **16** (or compatible) with the **`vector`** extension |
| Recommended image | `pgvector/pgvector:pg16` (Docker Compose / Rancher) |
| Database name | Default: `mosipnexus` (changeable) |
| App role | Default user/password: `mosip` / `mosip` (**change in production**) |

Tables for the vector store are created automatically by LangChain PGVector on
first ingest (`langchain_pg_collection`, `langchain_pg_embedding`). You do **not**
hand-write DDL for those collections.

App tables (sessions, feedback, stats) are managed with **Alembic**:

```powershell
cd Server
uv sync
uv run alembic upgrade head
```

Docker / `entrypoint.sh` runs migrations before starting the API.

---

## 2. Checklist before first run

### A. Create the database (manual / non-Docker)

```sql
-- As a PostgreSQL superuser
CREATE DATABASE mosipnexus;
CREATE USER mosip WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE mosipnexus TO mosip;
\c mosipnexus
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO mosip;
```

Docker Compose already runs `Server/k8s/postgres-init.sql` (extension + grants) on
first volume init.

### B. Set `PG_CONNECTION` (required)

Format:

```text
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
```

| Environment | Typical value |
| --- | --- |
| Local (Postgres on host) | `postgresql+psycopg://mosip:PASSWORD@localhost:5432/mosipnexus` |
| Docker Compose | Injected for `nexus-api` / `nexus-mcp`: `@postgres:5432` |
| Rancher / K8s | Secret key `PG_CONNECTION` → `@nexus-postgres:5432` |

**Where to set it**

- Local: copy `Server/.env.example` → `Server/.env` and edit `PG_CONNECTION`
- K8s: edit `Server/k8s/02-secret.yaml` (`POSTGRES_PASSWORD` **and** the matching
  password inside `PG_CONNECTION`), then `kubectl apply`

Also change `POSTGRES_PASSWORD` in:

- `docker-compose.yml` → `postgres.environment.POSTGRES_PASSWORD`
- `Server/k8s/01-postgres.yaml` (if you override the default)
- `Server/k8s/02-secret.yaml` → `POSTGRES_PASSWORD` + `PG_CONNECTION`

All three must agree.

### C. Product / collection naming (MOSIP vs Inji)

Collection and JSON file names use `PRODUCT_SLUG`:

| Env | Default | Effect |
| --- | --- | --- |
| `PRODUCT_SLUG` | `mosip` | Files like `Server/data/mosip_docs.json`, collection `mosip_docs` |
| | `inji` | Files/collections become `inji_docs`, etc. |

If you change `PRODUCT_SLUG` after data was already ingested, either:

1. Re-crawl + re-ingest into the new collections, or  
2. Keep the old slug and only change display URLs (`DOCS_BASE_URL`, etc.).

### D. Optional but recommended before crawl/ingest

| Variable | Why |
| --- | --- |
| `GITHUB_TOKEN` | Raises GitHub API limit (60 → 5 000 req/hr) |
| `GROQ_API_KEY` | Used only by ingestion thread summarizer |
| `HF_TOKEN` | Avoids HuggingFace download rate limits |
| Confluence / Jira vars | Only if you enable those crawlers |

Chat LLM keys are **BYOK** in the UI Settings page — not required in `.env`
for chat.

---

## 3. First-time data load order

1. Postgres healthy + `PG_CONNECTION` correct  
2. Ensure crawl JSON exists under `Server/data/` (committed MOSIP files, or run crawlers)  
3. From `Server/`:

```powershell
cd Server
uv sync
```

```powershell
$env:PYTHONPATH = (Get-Location).Path   # or absolute path to Server/
uv run python ingestion/store.py
```

4. Start API (+ UI). UI uses `NEXUS_API_URL` only — no DB env on the UI service.

---

## 4. What you do **not** need to change

- Hand-written table schemas for embeddings  
- UI `PG_CONNECTION` (UI must not get a DB URL)  
- Embedding dimension (fixed by `EMBED_MODEL`, default `intfloat/multilingual-e5-base`)

Changing `EMBED_MODEL` or chunk sizes bumps `PIPELINE_VERSION` and forces a
full re-embed via `run_update.py` — plan downtime accordingly.

---

## 5. Health check

```text
GET http://localhost:8010/health
```

Returns per-collection chunk counts when pgvector is reachable.

# Nexus Server

Backend for Nexus: crawlers, ingestion, pgvector retrieval, FastAPI REST API, and MCP (Claude Desktop).

The same Server binary can serve **MOSIP**, **Inji**, or another product by changing environment variables — no code fork required.

> UI lives in [`../UI`](../UI/README.md) and must not import this package. It calls the API over HTTP.

---

## What this folder contains

```text
Server/
├── api/main.py              # FastAPI — /chat, /search, /similar, /config, /notify, …
├── config/settings.py       # All env bindings (PRODUCT_*, URLs, GitHub, PG_CONNECTION)
├── crawler/                 # docs, community, github, code, confluence, jira
├── ingestion/store.py       # Chunk → embed → upsert into pgvector
├── retrieval/               # Hybrid retriever + duplicate detection
├── chain/                   # RAG answer generation (used by API)
├── memory/                  # Server-side chat sessions
├── notifications/           # Optional SMTP alerts
├── mcp_server/server.py     # FastMCP — search_knowledge(product=…), list_products
├── data/                    # Crawled JSON ({PRODUCT_SLUG}_*.json)
├── run_update.py            # Incremental crawl + re-embed
├── Dockerfile               # nexus-server image (API / MCP / jobs)
├── docker-compose.yml       # postgres + API + MCP
├── .env.example             # → copy to Server/.env
├── .python-version          # 3.13 (uv / pyenv)
├── .dockerignore
├── pyproject.toml           # Declared Python deps (source of truth for uv)
├── uv.lock                  # Locked versions for uv sync
├── requirements.txt         # Full locked tree for pip (`pip install -r`)
├── requirements-direct.txt  # Direct deps only (mirrors pyproject.toml)
├── db/                      # models, engine, repositories, crud wrappers
├── controllers/             # Session / feedback / stats services
├── alembic/                 # Migrations (app tables only)
├── docs/                    # Database, MCP, adding data sources
├── k8s/                     # Namespace, postgres, API, secrets, cron, ingest
└── README.md                # This file
```

---

## Prerequisites

1. Python **3.13** + [`uv`](https://github.com/astral-sh/uv) *(preferred)* or pip
2. PostgreSQL **16** with **pgvector** — see [Database setup](./docs/DATABASE_SETUP.md)
3. Install deps from `Server/`:
   - **uv:** `uv sync` (uses `pyproject.toml` + `uv.lock`)
   - **pip:** `pip install -r requirements.txt` (full locked tree)
4. Copy env template: `copy .env.example .env` and set at least `PG_CONNECTION`

---

## Parallel users (concurrency)

The API is tuned for many concurrent chats. **Chat sessions, feedback, and stats
are stored in Postgres** (Alembic-managed), so multiple uvicorn workers / replicas
can share state. The HF embedder is still ~1 GB per process — prefer fewer
workers with higher `MAX_CONCURRENT_CHATS` unless you have RAM headroom.

| Knob | Default | Role |
| --- | --- | --- |
| `MAX_CONCURRENT_CHATS` | 32 | In-process semaphore — excess `/chat` get **503** + `Retry-After` |
| `UVICORN_LIMIT_CONCURRENCY` | 64 | Cap open connections at the server |
| `RETRIEVAL_PARALLELISM` | 4 | Parallel pgvector collection searches after **one** query embed |
| `PG_POOL_SIZE` / `PG_MAX_OVERFLOW` | 10 / 20 | Shared SQLAlchemy pool for app + vector stores |
| `EMBED_CACHE_SIZE` | 512 | LRU cache for repeated question embeddings |
| `SESSION_TTL_SECONDS` | 3600 | Idle session soft-clear in DB |

Run migrations before serving traffic: `uv run alembic upgrade head`
(or rely on Docker `entrypoint.sh`). See [docs/DATABASE_LAYER.md](./docs/DATABASE_LAYER.md).

---

## Docker

| File | Role |
| --- | --- |
| `Dockerfile` | Image `nexus-server` — bakes HF embedding model |
| `docker-compose.yml` | postgres + `nexus-api` + `nexus-mcp` |
| `.dockerignore` | Excludes `data/`, secrets, tests |
| `pyproject.toml` | Declared Server dependencies (uv) |
| `uv.lock` | Exact versions for `uv sync` |
| `requirements.txt` | Full locked tree for `pip install -r` |
| `requirements-direct.txt` | Direct deps only (review / docs) |

```powershell
# From repo root — Server stack only
docker compose -f Server/docker-compose.yml --env-file Server/.env up --build

# Build image alone
docker build -t nexus-server:latest -f Server/Dockerfile Server
```

API → http://localhost:8010/docs · MCP → http://localhost:8002/sse

Full stack (Server + UI): `docker compose up --build` from repo root (uses `Server/.env` + `UI/.env`).

---

## Quick start

```powershell
cd "C:\From MOSIP\LABS\MOSIPNexus\Server"
copy .env.example .env
# Edit .env — at least PG_CONNECTION
uv sync

$env:PYTHONPATH = "C:\From MOSIP\LABS\MOSIPNexus\Server"

# Optional: crawl (skip if data/mosip_*.json already present)
uv run python crawler/docs_crawler.py
uv run python crawler/community_crawler.py
uv run python crawler/github_crawler.py
uv run python crawler/code_crawler.py

# Ingest into pgvector (first run can take hours on CPU)
uv run python ingestion/store.py

# API
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Or run **`run.bat`** (Windows) / **`./run.sh`** (Linux / macOS) — listens on **:8010** to match the UI Vite proxy.

| Resource | URL |
| --- | --- |
| Swagger | http://localhost:8000/docs *(or :8010 via `run.bat` / `run.sh`)* |
| Health | http://localhost:8000/health |
| Public config (for UI) | http://localhost:8000/config |

Docker Compose from repo root also starts postgres + `nexus-api` + `nexus-mcp` (see **Docker** above). For the React UI see [`../UI/README.md`](../UI/README.md).

---

## Environment variables

Full catalog: [docs/ENVIRONMENT.md](./docs/ENVIRONMENT.md).  
Set in `Server/.env` (from [`.env.example`](./.env.example)) or `Server/k8s/02-secret.yaml` (Rancher).

### Required

| Variable | Purpose |
| --- | --- |
| `PG_CONNECTION` | `postgresql+psycopg://user:pass@host:5432/dbname` |

### Product identity (MOSIP vs Inji)

Crawl/ingest still uses process-level `PRODUCT_*`. Interactive chat and MCP select a profile per request via `X-Nexus-Product` / tool `product` (see `config/products.py`).

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRODUCT_NAME` | `MOSIP Nexus` | Crawl tooling display name |
| `PRODUCT_SHORT` | `MOSIP` | Short label |
| `PRODUCT_SLUG` | `mosip` | Prefix for JSON files when crawling |
| `DEFAULT_PRODUCT` | `mosip` | API/MCP fallback when client omits product |
| `MCP_DEFAULT_PRODUCT` | same as `DEFAULT_PRODUCT` | MCP tool default when `product` arg is empty |
| `MOSIP_*` / `INJI_*` | see `.env.example` | Per-product URLs and collection names |

### Crawl / knowledge targets

| Variable | Default (MOSIP) |
| --- | --- |
| `DOCS_BASE_URL` | `https://docs.mosip.io/1.2.0` |
| `COMMUNITY_BASE_URL` | `https://community.mosip.io` |
| `COMMUNITY_NEW_TOPIC_PATH` | `/new-topic` |
| `GITHUB_ORG` | `mosip` |
| `GITHUB_REPOS` | Comma-separated `org/repo` fallback list |
| `GITHUB_REPO_EXCLUDE` | Repo names to skip |
| `GITHUB_TOKEN` | Recommended (raises API rate limit) |

### Optional

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Ingestion thread summarizer only — **not** used for chat LLM |
| `CONFLUENCE_*` / `JIRA_*` | Atlassian crawlers |
| `SMTP_*` / `NOTIFY_EMAIL` | Expert / low-confidence email alerts |
| `MCP_TRANSPORT` | `stdio` (default) or `sse` for Claude Desktop URL |
| `MCP_PORT` | `8002` |
| `MCP_DEFAULT_PRODUCT` | `mosip` or `inji` — default for MCP tools when `product` is omitted |

Example Inji overrides:

```env
PRODUCT_NAME=Inji Nexus
PRODUCT_SHORT=Inji
PRODUCT_SLUG=inji
DOCS_BASE_URL=https://docs.example-inji.org
COMMUNITY_BASE_URL=https://community.example-inji.org
GITHUB_ORG=inji
GITHUB_REPOS=inji/repo-a,inji/repo-b
```

Then crawl + ingest so `data/inji_*.json` and `inji_*` collections exist.

---

## REST API (summary)

| Endpoint | Role |
| --- | --- |
| `POST /chat` | RAG answer (requires `llm_api_key` BYOK) |
| `POST /search` | Vector search only (no LLM) |
| `POST /similar` | Duplicate community-thread check |
| `GET /config` | Safe product branding for the UI |
| `POST /notify/expert` | SMTP expert escalation |
| `GET /health` | Collection counts |

Chat LLM keys are **BYOK** — callers (UI or API clients) supply Groq / Anthropic / OpenAI keys. The Server does not need a chat LLM key in `.env`.

---

## MCP (Claude Desktop)

Retrieval-only tools — the LLM runs in Claude Desktop. One process can search **MOSIP and Inji** via the `product` argument.

| Tool | Description |
| --- | --- |
| `search_knowledge(query, product)` | Hybrid search (`product` = `mosip` \| `inji`) |
| `list_knowledge_sources(product)` | Live counts + URLs for that product |
| `list_products()` | Available modes and MCP default |

```powershell
cd Server   # if not already here
$env:PYTHONPATH = (Get-Location).Path
$env:MCP_TRANSPORT = "sse"
$env:MCP_PORT = "8002"
$env:MCP_DEFAULT_PRODUCT = "mosip"
uv run python mcp_server/server.py
```

**Dual Claude Desktop entries** (pinned defaults — recommended):

```json
{
  "mcpServers": {
    "mosip-nexus": {
      "command": "uv",
      "args": ["run", "python", "Server/mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "<repo>/Server",
        "PG_CONNECTION": "postgresql+psycopg://mosip:mosip@localhost:5433/mosipnexus",
        "MCP_TRANSPORT": "stdio",
        "MCP_DEFAULT_PRODUCT": "mosip"
      }
    },
    "inji-nexus": {
      "command": "uv",
      "args": ["run", "python", "Server/mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "<repo>/Server",
        "PG_CONNECTION": "postgresql+psycopg://mosip:mosip@localhost:5433/mosipnexus",
        "MCP_TRANSPORT": "stdio",
        "MCP_DEFAULT_PRODUCT": "inji"
      }
    }
  }
}
```

Or a single SSE URL — ask Claude to pass `product="mosip"` or `product="inji"`:

```json
{
  "mcpServers": {
    "nexus": { "url": "http://localhost:8002/sse" }
  }
}
```

Full guide: [MCP Server guide](./docs/MCP_SERVER.md) · Root [README](../README.md#using-mcp--claude-desktop-no-ui).

---

## Incremental updates

```powershell
cd Server
$env:PYTHONPATH = (Get-Location).Path
uv run python run_update.py
```

Nightly CronJob: `Server/k8s/06-cronjob.yaml`.

---

## Kubernetes

Manifests are under [`Server/k8s/`](./k8s/README.md) only for backend concerns (namespace, postgres, secrets, API, cron, ingest).

```powershell
kubectl apply -f Server/k8s/00-namespace.yaml
kubectl apply -f Server/k8s/01-postgres.yaml
# fill Server/k8s/02-secret.yaml first
kubectl apply -f Server/k8s/02-secret.yaml
kubectl apply -f Server/k8s/03-deployment-api.yaml
kubectl apply -f Server/k8s/04-service-api.yaml
kubectl apply -f Server/k8s/05-ingress-api.yaml
kubectl apply -f Server/k8s/06-cronjob.yaml
kubectl apply -f Server/k8s/07-initial-ingest-job.yaml
```

Then deploy the UI from [`../UI/k8s`](../UI/k8s/README.md).

---

## Adding a data source

See [ADDING_DATA_SOURCES.md](./docs/ADDING_DATA_SOURCES.md). Pattern: crawler → `data/` JSON → `ingestion/store.py` → `retrieval/retriever.py` → optional `run_update.py` + MCP `list_knowledge_sources`.

---

## Related docs

| Doc | Path |
| --- | --- |
| Architecture | [./docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| Environment variables | [./docs/ENVIRONMENT.md](./docs/ENVIRONMENT.md) |
| Docs index | [./docs/README.md](./docs/README.md) |
| Database setup | [./docs/DATABASE_SETUP.md](./docs/DATABASE_SETUP.md) |
| Database layer (Alembic) | [./docs/DATABASE_LAYER.md](./docs/DATABASE_LAYER.md) |
| MCP server | [./docs/MCP_SERVER.md](./docs/MCP_SERVER.md) |
| Adding data sources | [./docs/ADDING_DATA_SOURCES.md](./docs/ADDING_DATA_SOURCES.md) |
| Rancher guide | [../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md](../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md) |
| UI README | [../UI/README.md](../UI/README.md) |
| Root overview | [../README.md](../README.md) |

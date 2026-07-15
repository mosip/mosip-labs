# MOSIP Nexus — System Architecture

High-level map of how **Server**, **UI**, **Postgres**, and **MCP** fit together.

For Server-only detail see [Server/docs/ARCHITECTURE.md](../Server/docs/ARCHITECTURE.md).  
For UI detail see [UI/docs/ARCHITECTURE.md](../UI/docs/ARCHITECTURE.md).

---

## Context

```text
┌─────────────┐     HTTP /api      ┌──────────────────┐
│  React UI   │ ─────────────────► │  FastAPI (Server)│
│  :8501      │                    │  :8000 / :8010   │
└─────────────┘                    └────────┬─────────┘
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     ▼                      ▼                      ▼
              ┌─────────────┐      ┌─────────────────┐    ┌──────────────┐
              │ App tables  │      │ langchain_pg_*  │    │ External LLM │
              │ (Alembic)   │      │ (pgvector RAG)  │    │ (BYOK keys)  │
              └─────────────┘      └─────────────────┘    └──────────────┘
                     ▲                      ▲
                     │                      │
              ┌──────┴──────┐       ┌───────┴────────┐
              │ Claude MCP  │       │ Crawlers +     │
              │ :8002 /sse  │       │ ingestion jobs │
              └─────────────┘       └────────────────┘
```

---

## Responsibilities

| Component | Owns | Does not own |
| --- | --- | --- |
| **UI** | Presentation, BYOK keys in browser, language UX | RAG, DB, crawlers |
| **API** | Chat, search, sessions, feedback, stats, notify | Embedding model training |
| **Retriever** | Hybrid MMR search + confidence | LLM answering |
| **Query engine** | Condense → retrieve → answer → optional web fallback | UI branding |
| **MCP** | `search_knowledge` tools for Claude Desktop | Chat UI |
| **Postgres** | Vectors + app sessions/feedback/events | Secrets for LLM (BYOK) |

---

## Data paths

1. **Chat** — UI `POST /api/chat` → `controllers.chat` → `ask()` → embed once → parallel collection search → LLM → persist turn + `query_events`.
2. **Ingest** — crawlers write `Server/data/*.json` → `ingestion/store.py` → `langchain_pg_embedding`.
3. **Update** — `run_update.py` / CronJob incremental crawl + re-embed.
4. **MCP** — client calls tools → same `retrieve()` as API (no LLM on server).

---

## Configuration

- Product identity (`PRODUCT_*`, docs/community URLs, GitHub org) is **env-driven** so one Server binary serves MOSIP or Inji.
- Full env list: [Server/docs/ENVIRONMENT.md](../Server/docs/ENVIRONMENT.md).
- UI only needs API reachability (`/api` proxy or `VITE_NEXUS_API_URL`).

---

## Deployment shapes

| Shape | How |
| --- | --- |
| Local full stack | Root `docker compose up --build` |
| Server only | `Server/docker-compose.yml` |
| UI only (dev) | `cd UI && npm run dev` (Vite proxies `/api`) |
| Rancher / K8s | `Server/k8s` then `UI/k8s` — see Rancher guide |

Docker Server image runs **Alembic** via `entrypoint.sh` before uvicorn/MCP.

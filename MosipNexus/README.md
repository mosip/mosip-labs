# MOSIP Nexus

Production-grade RAG knowledge assistant (docs, community, GitHub, Confluence, code) with multilingual chat, source attribution, confidence scoring, and Claude Desktop MCP support.

**One Server** serves both **MOSIP** and **Inji**. The client chooses the product mode; the server uses the matching URLs and pgvector collections.

| Client | How product mode is chosen |
| --- | --- |
| **React UI** | Sidebar / Settings → `X-Nexus-Product` (`mosip` \| `inji` \| `generic`) |
| **REST API** | Header / body `product` + optional `answer_mode` (`rag` \| `direct`) |
| **MCP / Claude Desktop** | Tool arg `product` (RAG for mosip/inji; generic is REST direct-only) |

## Component READMEs

| Component | README |
| --- | --- |
| **Server** (API, crawlers, DB, MCP) | **[Server/README.md](Server/README.md)** |
| **UI** (React) | **[UI/README.md](UI/README.md)** |
| **Docs index** | **[docs/README.md](docs/README.md)** |
| **MCP (Claude Desktop)** | **[Server/docs/MCP_SERVER.md](Server/docs/MCP_SERVER.md)** |

## Quick start

```powershell
copy Server\.env.example Server\.env
copy UI\.env.example UI\.env
# Edit Server/.env — set PG_CONNECTION

cd Server; uv sync; cd ..
# or: cd Server; pip install -r requirements.txt; cd ..
cd UI; npm ci; cd ..
# or: cd UI; npm install; cd ..

docker compose up --build
```

Or run the React UI against a local API:

```powershell
# Terminal 1 — API (port 8010)
cd Server
.\run.bat          # Windows
# ./run.sh         # Linux / macOS

# Terminal 2 — UI (port 8501, proxies /api → :8010)
cd UI
.\run.bat          # Windows
# ./run.sh         # Linux / macOS
```

| URL | Service |
| --- | --- |
| http://localhost:8501 | UI (add LLM key in Settings) |
| http://localhost:8010/docs | API Swagger |
| http://localhost:8002/sse | MCP (SSE) |

| Stack | Command |
| --- | --- |
| Full | `docker compose up --build` |
| Server only | `docker compose -f Server/docker-compose.yml --env-file Server/.env up --build` |
| UI only | `docker compose -f UI/docker-compose.yml --env-file UI/.env up --build` |

---

## Using the React UI (MOSIP ↔ Inji ↔ Direct)

1. Open http://localhost:8501 and add a BYOK LLM key under **Settings** (Groq, Anthropic, OpenAI, or xAI Grok).
2. In the sidebar (or Settings), pick **MOSIP**, **Inji**, or **Direct**.
3. **MOSIP / Inji** — RAG over that product’s docs/community/GitHub/code (`answer_mode=rag`).
4. **Direct** — white-label BYOK chat with **no** docs URLs or vector KB (`product=generic`, `answer_mode=direct`). Reuse this Server from any app that only needs “question → LLM answer” with the caller’s key.

Inji/MOSIP answers need those collections ingested; Direct mode does not.

### Direct / white-label API example

```http
POST /chat
Content-Type: application/json
X-Nexus-Product: generic

{
  "question": "Summarize the benefits of practice interviews",
  "language": "English",
  "llm_provider": "xai",
  "llm_api_key": "xai-...",
  "llm_model": "grok-3-mini",
  "product": "generic",
  "answer_mode": "direct",
  "system_prompt": "You are a helpful career coach. Be concise."
}
```

Brand the generic profile with `GENERIC_PRODUCT_NAME`, `GENERIC_PRODUCT_SHORT`, etc. (see Server `.env.example`).

---

## Using MCP / Claude Desktop (no UI)

Claude runs the LLM; Nexus MCP only retrieves. Full guide: [Server/docs/MCP_SERVER.md](Server/docs/MCP_SERVER.md).

**Tools:** `search_knowledge(query, product)`, `list_knowledge_sources(product)`, `list_products()`.

### Dual Claude Desktop entries (stdio, recommended)

Edit Claude Desktop → Settings → Developer → Config:

```json
{
  "mcpServers": {
    "mosip-nexus": {
      "command": "uv",
      "args": ["run", "python", "Server/mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "C:\\From MOSIP\\LABS\\MOSIPNexus\\Server",
        "PG_CONNECTION": "postgresql+psycopg://mosip:mosip@localhost:5433/mosipnexus",
        "MCP_TRANSPORT": "stdio",
        "MCP_DEFAULT_PRODUCT": "mosip"
      }
    },
    "inji-nexus": {
      "command": "uv",
      "args": ["run", "python", "Server/mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "C:\\From MOSIP\\LABS\\MOSIPNexus\\Server",
        "PG_CONNECTION": "postgresql+psycopg://mosip:mosip@localhost:5433/mosipnexus",
        "MCP_TRANSPORT": "stdio",
        "MCP_DEFAULT_PRODUCT": "inji"
      }
    }
  }
}
```

Use the **mosip-nexus** or **inji-nexus** server in Claude depending on the topic. You can still pass `product="inji"` on a MOSIP entry (and vice versa).

### Single SSE URL (Docker / remote)

```json
{
  "mcpServers": {
    "nexus": {
      "url": "http://localhost:8002/sse"
    }
  }
}
```

Ask Claude to search with `product="mosip"` or `product="inji"`.

---

## Layout

```text
MosipNexus/
├── Server/          # Backend — README + docs/ + k8s/ + Dockerfile
├── UI/              # React front-end — README + k8s/ + Dockerfile
├── docs/            # Shared product docs + Rancher guide
└── docker-compose.yml
```

## Further reading

- [System architecture](docs/ARCHITECTURE.md) · [API reference](docs/API_REFERENCE.md) · [Contributing](docs/CONTRIBUTING.md)
- Server guides: [Server/docs](Server/docs/README.md) (database, env, MCP, architecture)
- UI guides: [UI/docs](UI/docs/ARCHITECTURE.md)
- Rancher: [docs/MOSIP_Nexus_Rancher_Deployment_Guide.md](docs/MOSIP_Nexus_Rancher_Deployment_Guide.md)
- K8s: [Server/k8s](Server/k8s/README.md) → then [UI/k8s](UI/k8s/README.md)

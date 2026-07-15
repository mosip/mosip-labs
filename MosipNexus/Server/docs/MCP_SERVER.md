# Nexus MCP Server

How the **Model Context Protocol (MCP)** server works, how to run it for **MOSIP and Inji**, and how Claude Desktop (or any MCP client) uses it — **without the React UI**.

Source of truth: `Server/mcp_server/server.py`

---

## 1. What MCP is in this project

| Piece | Role |
| --- | --- |
| **MCP server** (`nexus-mcp`) | Loads embeddings + pgvector stores; exposes **tools** over MCP |
| **MCP client** (e.g. Claude Desktop) | Calls those tools; runs the **LLM on the client** (your Claude subscription) |
| **FastAPI / React UI** | Separate — they do **not** go through MCP |

- MCP does **retrieval only** (no server-side chat LLM).
- One MCP process can search **both** MOSIP and Inji collections via a `product` tool argument.
- Same Postgres / pgvector DB as the REST API.

```text
Claude Desktop (LLM + tool calling)
        │  MCP (stdio or SSE)
        ▼
Server/mcp_server/server.py  →  retrieval.retriever.retrieve(query, product=…)
        │
        ▼
PostgreSQL + pgvector  (mosip_* and/or inji_* collections)
```

---

## 2. Tools

| Tool | Purpose |
| --- | --- |
| `search_knowledge(query, product="")` | Hybrid retrieval for one product. `product` = `mosip` \| `inji`. Empty → `MCP_DEFAULT_PRODUCT`. |
| `list_knowledge_sources(product="")` | Live chunk counts + docs/community/GitHub URLs for that product. |
| `list_products()` | Lists available modes (slug, name, URLs, which is the MCP default). |

Server FastMCP name: `nexus`.

Instructions tell the client to pass `product="mosip"` or `product="inji"` and to cite source URLs from tool results only.

---

## 3. Default product

| Env | Default | Role |
| --- | --- | --- |
| `MCP_DEFAULT_PRODUCT` | `DEFAULT_PRODUCT` / `mosip` | Used when tools omit `product` |
| `DEFAULT_PRODUCT` | `mosip` | Shared with the REST API |

Pin a default per Claude Desktop entry (dual configs below) so Claude can use MOSIP or Inji without remembering the arg — or keep one server and always pass `product`.

---

## 4. Transports

| Env | Value | When to use |
| --- | --- | --- |
| `MCP_TRANSPORT` | `stdio` | Claude Desktop **spawns** the process (`command` + `args`) |
| `MCP_TRANSPORT` | `sse` | Remote / Docker: client connects with a **URL** |
| `MCP_PORT` | `8002` | SSE listen port |

Docker Compose: `http://localhost:8002/sse`

---

## 5. Claude Desktop — dual product (recommended)

### Option A — Two stdio entries (pinned defaults)

Best when Claude Desktop starts the MCP process itself. Each entry defaults to one product; tools still accept an explicit `product` override.

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

Adjust `PYTHONPATH` and `PG_CONNECTION` for your machine. Postgres must already contain ingested `mosip_*` / `inji_*` collections.

### Option B — One SSE server (product arg)

1. Start MCP with SSE (`docker compose` or `MCP_TRANSPORT=sse`).
2. Single Claude config:

```json
{
  "mcpServers": {
    "nexus": {
      "url": "http://localhost:8002/sse"
    }
  }
}
```

3. Ask Claude to call `search_knowledge` with `product="mosip"` or `product="inji"` (or `list_products` first).

### Option C — Two SSE ports (pinned defaults)

Run two processes if you want separate MCP URLs without relying on the tool arg:

```powershell
# Terminal 1 — MOSIP default
$env:PYTHONPATH = ".\Server"
$env:MCP_TRANSPORT = "sse"
$env:MCP_PORT = "8002"
$env:MCP_DEFAULT_PRODUCT = "mosip"
uv run python Server/mcp_server/server.py

# Terminal 2 — Inji default
$env:PYTHONPATH = ".\Server"
$env:MCP_TRANSPORT = "sse"
$env:MCP_PORT = "8003"
$env:MCP_DEFAULT_PRODUCT = "inji"
uv run python Server/mcp_server/server.py
```

```json
{
  "mcpServers": {
    "mosip-nexus": { "url": "http://localhost:8002/sse" },
    "inji-nexus": { "url": "http://localhost:8003/sse" }
  }
}
```

Production example (single SSE gateway — use `product` arg):

```json
{
  "mcpServers": {
    "nexus": {
      "url": "https://mosip-nexus.env.mosip.net/mcp/sse"
    }
  }
}
```

Restart Claude Desktop after editing config. Confirm tools: `search_knowledge`, `list_knowledge_sources`, `list_products`.

---

## 6. Run without Claude (smoke test)

```powershell
cd "C:\From MOSIP\LABS\MOSIPNexus"
$env:PYTHONPATH = ".\Server"
$env:MCP_TRANSPORT = "sse"
$env:MCP_PORT = "8002"
$env:MCP_DEFAULT_PRODUCT = "mosip"
uv run python Server/mcp_server/server.py
```

Compose: service `nexus-mcp` in `docker-compose.yml`.

---

## 7. UI vs REST vs MCP

| | React UI | REST `/chat` | MCP |
| --- | --- | --- | --- |
| Product mode | Sidebar / Settings → `X-Nexus-Product` | Header / body `product` | Tool arg `product` or `MCP_DEFAULT_PRODUCT` |
| LLM | BYOK in Settings | Caller `llm_api_key` | **Client** (Claude) |
| Retrieval | Via API | In API process | In MCP process |
| Needs pgvector? | Via API | Yes | Yes |

UI customisation never edits `mcp_server/`. MCP and API share `Server/retrieval/` and `Server/config/products.py`.

---

## 8. Extending after a new data source

1. Ensure `retrieve()` searches the new store for each product profile.
2. Update `list_knowledge_sources()` if you add a new labelled source type.
3. No Claude Desktop change unless you rename tools.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Tools missing / URL fail | Transport still `stdio` | Set `MCP_TRANSPORT=sse` for Docker/remote |
| First search “still initializing” | Warm-up not finished | Wait ~60s after start |
| Empty / “not indexed” | No ingest for that product | Ingest into `mosip_*` or `inji_*` collections |
| Wrong product answers | Omitted `product` + wrong default | Pass `product=` or set `MCP_DEFAULT_PRODUCT` |
| Claude invents facts without tools | Client skipped tools | Ask it to use `search_knowledge`; check MCP connected |
| OOM on MCP pod | HF model ~1.1 GB | ~2.5 GB+ memory (see Rancher guide) |

---

## 10. Related files

| Path | Role |
| --- | --- |
| `Server/mcp_server/server.py` | FastMCP app, tools, warm-up |
| `Server/config/products.py` | MOSIP / Inji profiles (URLs + collections) |
| `Server/retrieval/retriever.py` | Shared search (API + MCP) |
| `docker-compose.yml` → `nexus-mcp` | SSE on 8002 |
| [ENVIRONMENT.md](./ENVIRONMENT.md) | `MCP_*`, `MOSIP_*`, `INJI_*` |
| [DATABASE_SETUP.md](./DATABASE_SETUP.md) | Postgres / pgvector |

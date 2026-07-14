# MOSIP Nexus

A production-grade RAG chatbot that answers MOSIP questions using **five knowledge sources**: official documentation, community forum Q&A, GitHub issues, Confluence spaces, and MOSIP source code — with multilingual support, chat memory, source attribution, and confidence scoring.

## Documentation

| Document | Audience | Location |
| --- | --- | --- |
| [Developer Guide](docs/MOSIP_Nexus_Developer_Guide.docx) | Developers (zero GenAI background) | `docs/MOSIP_Nexus_Developer_Guide.docx` |
| [Business Presentation](docs/MOSIP_Nexus_Presentation.pptx) | Stakeholders, managers, org leaders | `docs/MOSIP_Nexus_Presentation.pptx` |
| [Rancher Deployment Guide](docs/MOSIP_Nexus_Rancher_Deployment_Guide.md) | Infrastructure / DevOps team | `docs/MOSIP_Nexus_Rancher_Deployment_Guide.md` |

> To regenerate these files after changes: `uv run python docs/generate_docs.py`

## Knowledge Base

| Source | Chunks | Description |
| --- | --- | --- |
| MOSIP Docs | 6,094 | All 449 pages from docs.mosip.io/1.2.0 |
| Community Forum | 11,236 | Q&A threads from community.mosip.io (accepted answers prioritised) |
| GitHub Issues | 2,513 | Closed issues from 86 MOSIP org repos |
| Confluence | 12,264 | QT, ENGG, and PMS spaces |
| Source Code | ~38,000 | Java/YAML/properties from all 86 repos (priority: error constants, service impls, controllers) |

> **Note**: `data/mosip_confluence.json` is not committed to this repository as Confluence pages
> may contain internal credentials and sensitive content. Anyone cloning will need to run
> `crawler/confluence_crawler.py` themselves using their own Confluence API token to index
> Confluence data. All other data files (`mosip_docs.json`, `mosip_community.json`,
> `mosip_github.json`, `mosip_code.json`) are committed and ready to use without re-crawling.

## Features

| Feature | Details |
| --- | --- |
| **Five knowledge sources** | Docs + Community + GitHub + Confluence + Code — all searchable in one query |
| **Multilingual** | Ask in any language (Tamil, Hindi, French, Arabic, …); replies in the same language (≥95% confidence) |
| **Chat memory** | Follow-up questions retain full conversation context |
| **Source attribution** | Every answer cites exact doc pages, forum threads, GitHub issues, or Confluence pages |
| **Duplicate detection** | Surfaces similar community threads before generating a new answer |
| **Community intelligence** | `[ACCEPTED ANSWER]` posts and high-voted replies ranked higher |
| **Confidence scoring** | 🟢 High / 🟡 Medium / 🔴 Low based on retrieval cosine distance |
| **No hallucination guard** | LLM instructed to return "not available" when context is irrelevant |
| **BYOK — Bring Your Own Key** | Users supply their own Groq / Anthropic / OpenAI API key via the Settings page. No server-side LLM cost for user queries. |
| **Claude Desktop / MCP** | Connect Claude Desktop directly — it calls `search_mosip` for retrieval and uses your own Claude subscription for the LLM. Zero API cost to the app owner. |
| **Query intelligence** | Automatic query classification: error-code format, environment-debug format, code-class format, or general. Each gets a specialised system prompt and retrieval strategy. |
| **Hybrid retrieval** | SQL exact-match for error constants + sibling co-retrieval from the same source file + MMR vector search — error code answers always include the defining constant. |
| **Production / demo separation** | Demo, test, mock, and sample packages are ranked below production code so the LLM cites real implementations, not sample apps. |
| **Incremental updates** | `run_update.py` re-crawls only changed/new content across docs, community, GitHub, Confluence, and Jira |
| **LangSmith observability** | Full trace visibility — zero code changes, just env vars |

## Tech Stack

| Component | Choice |
| --- | --- |
| Framework | LangChain 1.x (LCEL) |
| LLM | **BYOK** — Groq / Anthropic / OpenAI (user-supplied key via Settings page); Groq server key for ingestion pipeline only |
| MCP | `mcp` + FastMCP — SSE transport for Claude Desktop integration (port 8002) |
| Embeddings | HuggingFace `intfloat/multilingual-e5-base` (768-dim, 100+ languages) |
| Vector DB | pgvector (PostgreSQL extension — ACID, SQL filtering, pg_dump backups) |
| Crawlers | `requests` + `BeautifulSoup` + Discourse API + GitHub REST API + Atlassian REST API |
| Observability | LangSmith (optional, free tier) |
| UI | Streamlit multi-page (chat + settings) |
| Package manager | `uv` |
| Python | 3.13 |

## Project Structure

```text
MosipNexus/
├── config/
│   └── settings.py              # All constants, env bindings, and tuneable params
├── crawler/
│   ├── docs_crawler.py          # Sitemap crawler → mosip_docs.json (tables converted to prose)
│   ├── community_crawler.py     # Discourse API crawler → mosip_community.json
│   ├── github_crawler.py        # GitHub Issues API (auto-discovers 86 repos) → mosip_github.json
│   ├── code_crawler.py          # GitHub Tree API for source files → mosip_code.json
│   ├── confluence_crawler.py    # Atlassian REST API → mosip_confluence.json (tables converted to prose)
│   ├── jira_crawler.py          # Atlassian Jira API → mosip_jira.json (optional)
│   ├── utils.py                 # Shared crawler utilities (table_to_prose)
│   └── state.py                 # Crawl state persistence for incremental updates
├── ingestion/
│   └── store.py                 # Chunk, embed, upsert into pgvector collections
├── retrieval/
│   ├── retriever.py             # Hybrid retrieval: MMR + SQL exact-match + sibling co-retrieval + production/demo separation
│   └── dedup.py                 # Duplicate question detection
├── chain/
│   ├── query_engine.py          # LCEL RAG chain — BYOK multi-provider, query classification, specialised system prompts
│   └── summarizer.py            # Long thread summarisation
├── memory/
│   └── session.py               # Session-level chat history
├── notifications/
│   └── email_notifier.py        # Optional email alerts for unanswerable questions
├── mcp_server/
│   └── server.py                # FastMCP server — exposes search_mosip + list_knowledge_sources tools (port 8002)
├── app/
│   ├── app.py                   # Streamlit chat UI
│   └── pages/
│       └── settings.py          # Settings page — LLM provider, API key (BYOK), model selector
├── run_update.py                 # Incremental update runner
├── data/                         # Crawled JSON files (committed — skips re-crawl for new cloners)
└── .env                          # Local secrets (gitignored)
```

## Setup

### 1. Set up PostgreSQL with pgvector

PostgreSQL must be running with the `pgvector` extension installed before ingestion.

```sql
-- Run as a PostgreSQL superuser
CREATE DATABASE mosipnexus;
CREATE USER mosip WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE mosipnexus TO mosip;
\c mosipnexus
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO mosip;
```

On Rancher/Kubernetes, use the `pgvector/pgvector:pg16` Docker image — it ships with the extension pre-installed.

### 2. Install dependencies

From the `MosipNexus/` directory:

```powershell
cd MosipNexus
uv sync
```

### 3. Configure environment

Create `MosipNexus/.env` with the following variables:

```env
# Required — PostgreSQL connection string
PG_CONNECTION="postgresql+psycopg://mosip:your_password@localhost:5432/mosipnexus"

# Optional — used only by the ingestion pipeline (thread summariser).
# NOT used for user queries — users bring their own key via the Settings page (BYOK)
# or connect via Claude Desktop + MCP (no API key needed at all).
GROQ_API_KEY="your_groq_api_key"          # free at console.groq.com

# Optional — avoids HuggingFace rate limits on model downloads
HF_TOKEN="your_hf_token"

# Optional — LangSmith observability (free at smith.langchain.com)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY="<YOUR_LANGCHAIN_API_KEY>"
LANGCHAIN_PROJECT=mosip-nexus

# Optional — GitHub (authenticates for 5,000 req/hr vs 60 unauthenticated)
GITHUB_TOKEN="<YOUR_GITHUB_TOKEN>"

# Optional — Confluence (Atlassian API token from id.atlassian.com)
CONFLUENCE_URL=https://your-org.atlassian.net/wiki
CONFLUENCE_USER=your_email@example.com
CONFLUENCE_TOKEN="<YOUR_CONFLUENCE_TOKEN>"
CONFLUENCE_SPACE_KEYS=QT,ENGG,PMS

# Optional — Jira
JIRA_URL=https://your-org.atlassian.net
JIRA_USER=your_email@example.com
JIRA_TOKEN="your_jira_token"
JIRA_PROJECT_KEYS=MOSIP,MISP

# Optional — Email alerts for unanswerable questions
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFY_EMAIL=mosip-team@example.com
```

### 4. Crawl all knowledge sources

Run crawlers once to generate the JSON data files. Each crawler is independent and can be run in parallel.

```powershell
# Docs — ~449 pages from docs.mosip.io (~5 min)
uv run python MosipNexus/crawler/docs_crawler.py

# Community forum — Q&A threads from community.mosip.io (~20–30 min)
uv run python MosipNexus/crawler/community_crawler.py

# GitHub issues — 86 repos, up to 500 closed issues each (~15 min with token)
uv run python MosipNexus/crawler/github_crawler.py

# Source code — Java/YAML/properties across all 86 repos (~30–60 min)
uv run python MosipNexus/crawler/code_crawler.py

# Confluence — requires CONFLUENCE_URL/USER/TOKEN in .env
uv run python MosipNexus/crawler/confluence_crawler.py

# Jira — optional, requires JIRA_* in .env
uv run python MosipNexus/crawler/jira_crawler.py
```

### 5. Build the vector index

Embeds all crawled data and stores in pgvector. Uses `intfloat/multilingual-e5-base` (CPU-only — plan for 2–6 hours depending on which sources you have).

```powershell
uv run python MosipNexus/ingestion/store.py
```

Progress is shown per batch (100 chunks each). Re-running automatically clears and rebuilds each collection (`pre_delete_collection=True` on the first batch).

### 6. Launch the app

```powershell
uv run streamlit run MosipNexus/app/app.py
```

Open [http://localhost:8501](http://localhost:8501).

## Claude Desktop / MCP Integration

MOSIP Nexus exposes a Model Context Protocol (MCP) server that Claude Desktop can connect to. When connected, Claude calls `search_mosip` for retrieval and uses your own Claude subscription for the LLM — zero API cost for the app owner.

### Connecting Claude Desktop

**Step 1** — Open Claude Desktop → Settings → Developer → Edit Config

**Step 2** — Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mosip-nexus": {
      "url": "http://localhost:8002/sse"
    }
  }
}
```

*(For production: replace `localhost:8002` with your deployed URL, e.g. `https://mosip-nexus.env.mosip.net/mcp/sse`)*

**Step 3** — Restart Claude Desktop. Verify `mosip-nexus` appears under Developer → MCP Servers.

**Step 4** — Ask Claude any MOSIP question. It automatically calls `search_mosip` and answers using your Claude subscription.

### Available MCP Tools

| Tool | Description |
| --- | --- |
| `search_mosip(query)` | Search all five knowledge sources simultaneously. Returns top chunks with source URLs. |
| `list_knowledge_sources()` | Show live record counts for each indexed source. |

---

## Usage

- Type any MOSIP question in the chat box
- Ask in any language — the assistant detects and replies in that language for the whole session
- If a similar community thread exists, it is surfaced before the generated answer
- Sources (doc pages, forum threads, GitHub issues, Confluence pages) are shown below each answer
- Confidence badge (🟢/🟡/🔴) reflects how well the retrieved context matched your query
- Click **New Chat** in the sidebar to reset the session

## How It Works

```text
User question
      │
      ▼
Duplicate detection — similar community thread exists?
      │ yes → surface existing thread, then continue
      │ no
      ▼
Pure greeting? ──yes──► Direct friendly reply (no RAG)
      │ no
      ▼
Condense follow-up with chat history (LLM)
      │
      ▼
MMR search across all 5 pgvector collections
(docs + community + github + confluence + code)
      │
      ▼
Score confidence from best-chunk cosine distance
      │
      ▼
Generate answer grounded in retrieved context (Groq Llama 3.3)
      │
      ▼
[NO_DOC_SOURCE] detected? ──yes──► "Not available in MOSIP sources"
      │ no
      ▼
Return answer + sources + confidence badge + related threads
```

## Incremental Updates

After the initial full crawl, use `run_update.py` to fetch only what has changed:

```powershell
uv run python MosipNexus/run_update.py
```

This compares the current crawl against `data/crawl_state.json` and re-embeds only new or changed content. Much faster than a full rebuild.

## Rebuilding from Scratch

If you change the embedding model or chunking parameters, reset the pgvector collections and crawl state before re-running:

```powershell
# Reset crawl state so all content is treated as new
Remove-Item MosipNexus/data/crawl_state.json

# Re-run ingestion — pre_delete_collection=True clears each pgvector collection on first batch
uv run python MosipNexus/ingestion/store.py
```

To wipe collections manually via SQL (e.g., before a schema change):

```sql
DELETE FROM langchain_pg_embedding;
DELETE FROM langchain_pg_collection;
```

## Production Deployment (Rancher / Kubernetes)

### Build the Docker image

The image is built and pushed to Docker Hub automatically by
`.github/workflows/mosip-nexus-docker-publish.yml` on every push to `master`
or `develop` that touches files under `MosipNexus/`. Pushes to `master` are
tagged `latest` + `<short-sha>`; pushes to `develop` are tagged `develop` +
`develop-<short-sha>`. `k8s/03-deployment-api.yaml` and `k8s/04-deployment-ui.yaml`
already point to `mohanachandran45/mosip-nexus:latest` with `imagePullPolicy: Always`,
so a Rancher rollout restart picks up the newest `master` build automatically.

To build manually instead (e.g. for a different registry):

```powershell
# From MosipNexus/ directory
docker build -t mosip-nexus:latest .
docker tag mosip-nexus:latest your-registry/mosip-nexus:1.0.0
docker push your-registry/mosip-nexus:1.0.0
```

Update the `image:` field in `k8s/03-deployment-api.yaml` and `k8s/04-deployment-ui.yaml` to point to your registry.

### Deploy to Rancher

```powershell
# 1. Fill in real values in k8s/02-secret.yaml (DO NOT commit with real values)
# 2. Apply all manifests in order
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-postgres.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/03-deployment-api.yaml
kubectl apply -f k8s/04-deployment-ui.yaml
kubectl apply -f k8s/05-services.yaml
kubectl apply -f k8s/06-ingress.yaml
kubectl apply -f k8s/07-cronjob.yaml
```

### First-time ingestion on the cluster

Copy `data/*.json` into the `nexus-data` PVC (via a temporary pod — see the
[Rancher Deployment Guide](docs/MOSIP_Nexus_Rancher_Deployment_Guide.md), Step 9),
then apply the bootstrap Job — it runs automatically, no `kubectl exec` needed:

```powershell
kubectl apply -f k8s/08-initial-ingest-job.yaml
kubectl logs -n mosip-nexus job/nexus-initial-ingest -f
```

This runs `ingestion/store.py` (full ingest from the committed seed files)
followed by `run_update.py` (bootstraps Confluence/Jira from their live APIs,
if configured in `k8s/02-secret.yaml`).

### Trigger a manual knowledge update

```powershell
kubectl create job --from=cronjob/nexus-updater nexus-updater-manual \
  -n mosip-nexus
```

### Local testing with Docker Compose

```powershell
# Requires .env with GROQ_API_KEY set
docker compose up --build
# UI  → http://localhost:8501
# API → http://localhost:8000/docs
```

## LangSmith Observability

When `LANGCHAIN_TRACING_V2=true` is set, every LangChain call (condenser, QA chain, retriever) is automatically traced at [smith.langchain.com](https://smith.langchain.com) under the `mosip-nexus` project. No code changes required.

Traces show: input → retrieved chunks → prompt sent → LLM output → latency per step.

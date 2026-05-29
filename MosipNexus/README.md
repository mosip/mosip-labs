# MOSIP Nexus

A production-grade RAG chatbot that answers MOSIP questions using **five knowledge sources**: official documentation, community forum Q&A, GitHub issues, Confluence spaces, and MOSIP source code — with multilingual support, chat memory, source attribution, and confidence scoring.

## Documentation

| Document | Audience | Location |
|---|---|---|
| [Developer Guide](docs/MOSIP_Nexus_Developer_Guide.docx) | Developers (zero GenAI background) | `docs/MOSIP_Nexus_Developer_Guide.docx` |
| [Business Presentation](docs/MOSIP_Nexus_Presentation.pptx) | Stakeholders, managers, org leaders | `docs/MOSIP_Nexus_Presentation.pptx` |

> To regenerate these files after changes: `uv run python docs/generate_docs.py`

## Knowledge Base

| Source | Chunks | Description |
|---|---|---|
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
|---|---|
| **Five knowledge sources** | Docs + Community + GitHub + Confluence + Code — all searchable in one query |
| **Multilingual** | Ask in any language (Tamil, Hindi, French, Arabic, …); replies in the same language (≥95% confidence) |
| **Chat memory** | Follow-up questions retain full conversation context |
| **Source attribution** | Every answer cites exact doc pages, forum threads, GitHub issues, or Confluence pages |
| **Duplicate detection** | Surfaces similar community threads before generating a new answer |
| **Community intelligence** | `[ACCEPTED ANSWER]` posts and high-voted replies ranked higher |
| **Confidence scoring** | 🟢 High / 🟡 Medium / 🔴 Low based on retrieval cosine distance |
| **No hallucination guard** | LLM instructed to return "not available" when context is irrelevant |
| **Incremental updates** | `run_update.py` re-crawls only changed pages and new issues |
| **LangSmith observability** | Full trace visibility — zero code changes, just env vars |

## Tech Stack

| Component | Choice |
|---|---|
| Framework | LangChain 1.x (LCEL) |
| LLM | Groq — `llama-3.3-70b-versatile` |
| Embeddings | HuggingFace `intfloat/multilingual-e5-base` (768-dim, 100+ languages) |
| Vector DB | ChromaDB (persistent SQLite, no server needed) |
| Crawlers | `requests` + `BeautifulSoup` + Discourse API + GitHub REST API + Atlassian REST API |
| Observability | LangSmith (optional, free tier) |
| UI | Streamlit |
| Package manager | `uv` |
| Python | 3.13 |

## Project Structure

```
MosipNexus/
├── config/
│   └── settings.py              # All constants, env bindings, and tuneable params
├── crawler/
│   ├── docs_crawler.py          # Sitemap crawler → mosip_docs.json
│   ├── community_crawler.py     # Discourse API crawler → mosip_community.json
│   ├── github_crawler.py        # GitHub Issues API (auto-discovers 86 repos) → mosip_github.json
│   ├── code_crawler.py          # GitHub Tree API for source files → mosip_code.json
│   ├── confluence_crawler.py    # Atlassian REST API → mosip_confluence.json
│   ├── jira_crawler.py          # Atlassian Jira API → mosip_jira.json (optional)
│   └── state.py                 # Crawl state persistence for incremental updates
├── ingestion/
│   └── store.py                 # Chunk, embed, upsert into ChromaDB collections
├── retrieval/
│   ├── retriever.py             # MMR search across all collections + confidence scoring
│   └── dedup.py                 # Duplicate question detection
├── chain/
│   ├── query_engine.py          # Main LCEL RAG chain (condense → retrieve → answer)
│   └── summarizer.py            # Long thread summarisation
├── memory/
│   └── session.py               # Session-level chat history
├── notifications/
│   └── email_notifier.py        # Optional email alerts for unanswerable questions
├── app/
│   └── app.py                   # Streamlit chat UI
├── run_update.py                 # Incremental update runner
├── data/                         # Crawled JSON files (committed — skips re-crawl for new cloners)
├── chroma_db/                    # Generated vector store (gitignored — rebuild with ingestion/store.py)
└── .env                          # Local secrets (gitignored)
```

## Setup

### 1. Install dependencies

From the `MosipNexus/` directory:

```powershell
cd MosipNexus
uv sync
```

### 2. Configure environment

Create `MosipNexus/.env` with the following variables:

```env
# Required
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

### 3. Crawl all knowledge sources

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

### 4. Build the vector index

Embeds all crawled data and stores in ChromaDB. Uses `intfloat/multilingual-e5-base` (CPU-only — plan for 2–6 hours depending on which sources you have).

```powershell
uv run python MosipNexus/ingestion/store.py
```

Progress is shown per batch (100 chunks each). Delete `MosipNexus/chroma_db/` before re-running to avoid duplicate embeddings.

### 5. Launch the app

```powershell
uv run streamlit run MosipNexus/app/app.py
```

Open [http://localhost:8501](http://localhost:8501).

## Usage

- Type any MOSIP question in the chat box
- Ask in any language — the assistant detects and replies in that language for the whole session
- If a similar community thread exists, it is surfaced before the generated answer
- Sources (doc pages, forum threads, GitHub issues, Confluence pages) are shown below each answer
- Confidence badge (🟢/🟡/🔴) reflects how well the retrieved context matched your query
- Click **New Chat** in the sidebar to reset the session

## How It Works

```
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
MMR search across all 5 ChromaDB collections
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

If you change the embedding model or chunking parameters, delete both the vector store and the crawl state before re-running:

```powershell
Remove-Item -Recurse -Force MosipNexus/chroma_db
Remove-Item MosipNexus/data/crawl_state.json
uv run python MosipNexus/ingestion/store.py
```

## LangSmith Observability

When `LANGCHAIN_TRACING_V2=true` is set, every LangChain call (condenser, QA chain, retriever) is automatically traced at [smith.langchain.com](https://smith.langchain.com) under the `mosip-nexus` project. No code changes required.

Traces show: input → retrieved chunks → prompt sent → LLM output → latency per step.

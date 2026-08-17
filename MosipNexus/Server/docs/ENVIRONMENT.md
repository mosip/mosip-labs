# Server environment variables

Variables are loaded by `config/settings.py`:

1. `load_dotenv(Server/.env)` — package-local file preferred
2. `load_dotenv()` — process cwd / parent `.env` may override
3. Process environment (Docker / Kubernetes secrets) always wins over missing file keys

Prefer importing from `config.settings` instead of calling `os.getenv` in application code.

Template: [../.env.example](../.env.example)  
Rancher: `Server/k8s/02-secret.yaml`

---

## Database & pooling

| Variable | Default | Purpose |
| --- | --- | --- |
| `PG_CONNECTION` | local `mosipnexus` URL | SQLAlchemy + pgvector DSN (`postgresql+psycopg://…`) |
| `PG_POOL_SIZE` | `10` | Base connection pool size |
| `PG_MAX_OVERFLOW` | `20` | Extra connections beyond pool size |
| `PG_POOL_TIMEOUT` | `30` | Seconds to wait for a free connection |
| `PG_POOL_RECYCLE` | `1800` | Recycle connections after N seconds |

---

## Product identity

Reuse the same Server binary for MOSIP, Inji, or white-label **direct BYOK** (no docs KB).

### Crawl / ingest defaults (`PRODUCT_*`)

Used by crawlers and batch ingest (one active crawl target per process).

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRODUCT_NAME` | `MOSIP Nexus` | Display / API title for crawl tooling |
| `PRODUCT_SHORT` | `MOSIP` | Short label in prompts and MCP text |
| `PRODUCT_SLUG` | `mosip` | Prefix for JSON files and default collection names |
| `DEFAULT_PRODUCT` | `mosip` | Request default when client omits `X-Nexus-Product` |

### Runtime chat profiles (`MOSIP_*` / `INJI_*` / `GENERIC_*`)

Interactive chat and search select a product **per request** via:

- Header: `X-Nexus-Product: mosip` | `inji` | `generic`
- Body: `POST /chat` fields `product`, optional `answer_mode` (`rag` | `direct`), optional `system_prompt`

| Variable | Default | Purpose |
| --- | --- | --- |
| `MOSIP_*` / `INJI_*` | product URLs + collections | RAG knowledge profiles |
| `GENERIC_PRODUCT_NAME` | `Nexus` | White-label title |
| `GENERIC_DEFAULT_ANSWER_MODE` | `direct` | Skip retrieval; BYOK LLM only |
| `GENERIC_RETRIEVAL_ENABLED` | `false` | No vector warmup unless you ingest |

See [DIRECT_BYOK.md](./DIRECT_BYOK.md). The UI stores mode in localStorage and sends `X-Nexus-Product` on every API call.

---

## Paths & collections

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATA_DIR` | `Server/data` | Crawled JSON + `crawl_state.json` |
| `DOCS_COLLECTION` | `{slug}_docs` | pgvector collection name |
| `COMMUNITY_COLLECTION` | `{slug}_community` | |
| `GITHUB_COLLECTION` | `{slug}_github` | |
| `CODE_COLLECTION` | `{slug}_code` | |
| `CONFLUENCE_COLLECTION` | `{slug}_confluence` | |
| `JIRA_COLLECTION` | `{slug}_jira` | |

---

## Crawl / knowledge targets

| Variable | Default (MOSIP) | Purpose |
| --- | --- | --- |
| `DOCS_BASE_URL` | `https://docs.mosip.io/1.2.0` | Docs root |
| `DOCS_SITEMAP_URL` | `{DOCS_BASE_URL}/sitemap.xml` | Sitemap entry |
| `COMMUNITY_BASE_URL` | `https://community.mosip.io` | Discourse forum |
| `COMMUNITY_NEW_TOPIC_PATH` | `/new-topic` | UI deep-link path |
| `COMMUNITY_MAX_PAGES` | `50` | Max `/latest.json` pages |
| `COMMUNITY_MIN_POSTS` | `1` | Skip thin topics |
| `CRAWL_DELAY_SECS` | `0.4` | Polite delay between HTTP calls |
| `HTTP_USER_AGENT` | `{PRODUCT_SHORT}NexusBot/1.0` | Crawler User-Agent |
| `GITHUB_ORG` | `mosip` | Org for repo discovery |
| `GITHUB_TOKEN` | _(empty)_ | Raises GitHub API rate limit |
| `GITHUB_API_BASE` | `https://api.github.com` | |
| `GITHUB_REPOS` | curated list | Fallback when no token |
| `GITHUB_REPO_EXCLUDE` | test/docs repos | Skip list (comma-separated names) |
| `GITHUB_USEFUL_LANGUAGES` | Java, Python, … | Language filter for discovery |
| `GITHUB_MAX_ISSUES` | `500` | Cap per repo (full crawl) |
| `CODE_INCLUDE_EXTENSIONS` | `.java,.yaml,…` | Code file extensions |
| `CODE_EXCLUDE_PATTERNS` | `test,target/,…` | Path skip patterns |
| `CODE_PRIORITY_PATTERNS` | `ErrorConstants,…` | Prefer these filenames |
| `CODE_MAX_FILE_BYTES` | `80000` | Skip huge blobs |
| `CONFLUENCE_URL` / `USER` / `TOKEN` | _(empty)_ | Optional Atlassian wiki |
| `CONFLUENCE_SPACE_KEYS` | `MOSIP` | Comma-separated spaces |
| `JIRA_URL` / `USER` / `TOKEN` | _(empty)_ | Optional Jira |
| `JIRA_PROJECT_KEYS` | `MOSIP` | Comma-separated projects |

---

## Embeddings & chunking

| Variable | Default | Purpose |
| --- | --- | --- |
| `EMBED_MODEL` | `intfloat/multilingual-e5-base` | HuggingFace embedding model (768-dim) |
| `CHUNK_SIZE` | `900` | Text splitter chunk size |
| `CHUNK_OVERLAP` | `150` | Overlap between chunks |

Changing embed/chunk settings changes `PIPELINE_VERSION` and forces a full re-ingest via `run_update.py`.

---

## Retrieval & confidence

Defaults favour **BYOK token cost** (fewer chunks). Raise `RETRIEVAL_*` /
`MAX_CONTEXT_*` if you need maximum recall on a server-paid key.

| Variable | Default | Purpose |
| --- | --- | --- |
| `RETRIEVAL_K` | `4` | Docs/community MMR `k` |
| `RETRIEVAL_FETCH_K` | `16` | MMR candidate pool |
| `MAX_CONTEXT_DOCS` | `8` | Max chunks considered for packing |
| `MAX_CONTEXT_CHARS` | `12000` | Hard char budget for packed RAG context (~3–4k tokens) |
| `RETRIEVAL_PARALLELISM` | `4` | Parallel collection searches |
| `EMBED_CACHE_SIZE` | `512` | LRU query-embedding cache |
| `GITHUB_RETRIEVAL_K` | `3` | GitHub collection `k` |
| `CODE_RETRIEVAL_K` | `4` | Code collection `k` (boosted for error/code queries) |
| `DEDUP_THRESHOLD` | `0.88` | Community near-duplicate similarity |
| `CONFIDENCE_HIGH` | `0.75` | Relevance ≥ → `high` |
| `CONFIDENCE_MEDIUM` | `0.55` | Relevance ≥ → `medium` else `low` |

---

## BYOK token budget (chat LLM)

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_MAX_HISTORY_MESSAGES` | `6` | Prior messages sent to answer/condense (≈3 turns) |
| `LLM_MAX_HISTORY_CHARS` | `600` | Truncate each history message |
| `LLM_MAX_OUTPUT_TOKENS` | `1200` | Cap completion length |
| `WEB_SEARCH_MAX_RESULTS` | `2` | DuckDuckGo hits on knowledge-base miss |
| `MAX_WEB_CONTEXT_CHARS` | `3500` | Packed web-snippet budget |

Also: greetings/meta answers use **no LLM**; follow-up condensation is skipped when the question looks standalone.

---

## API concurrency & sessions

| Variable | Default | Purpose |
| --- | --- | --- |
| `MAX_CONCURRENT_CHATS` | `32` | In-process `/chat` semaphore |
| `UVICORN_WORKERS` | `1` | Prefer 1 (HF model ~1 GB each) |
| `UVICORN_LIMIT_CONCURRENCY` | `64` | Uvicorn connection cap |
| `SESSION_TTL_SECONDS` | `3600` | Idle session soft-clear |
| `SESSION_MAX_COUNT` | `5000` | Soft-clear oldest beyond this |

---

## Logging

| Variable | Default | Purpose |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `LOG_FORMAT` | `text` | `text` (human) or `json` (one JSON object per line) |
| `LOG_ACCESS` | `true` | Emit HTTP access lines (`nexus.access`); `/health` is DEBUG-only when 2xx |

Loggers: `nexus`, `nexus.api`, `nexus.access`, `nexus.rag`, `nexus.sessions`, `nexus.feedback`, `nexus.stats`, `nexus.notify`, `nexus.mcp`.  
API responses include `X-Request-Id` (echoes client header or a new UUID). Never log API keys or SMTP passwords.

---

## LLM (server-side optional)

Chat endpoints require **caller BYOK** (`llm_api_key`). Server keys are for ingestion helpers / fallbacks only.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | _(empty)_ | Backend Groq (summarizer / internal), **not** chat BYOK |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Default Groq model id |

---

## Email notifications

| Variable | Default | Purpose |
| --- | --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | `587` STARTTLS or `465` SSL |
| `SMTP_USER` | _(empty)_ | Login |
| `SMTP_PASSWORD` | _(empty)_ | App password / token |
| `NOTIFY_EMAIL` | _(empty)_ | Destination for escalations |

All four of host/user/password/`NOTIFY_EMAIL` must be set for sends to succeed.

---

## Observability & language

| Variable | Default | Purpose |
| --- | --- | --- |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | _(empty)_ | LangSmith API key (env, not in settings export) |
| `LANGCHAIN_PROJECT` | `{slug}-nexus` | LangSmith project name |
| `MIN_LANG_DETECT_CHARS` | `20` | Min chars before language detection |
| `LANG_DETECT_CONFIDENCE` | `0.95` | Detector confidence threshold |

---

## MCP

| Variable | Default | Purpose |
| --- | --- | --- |
| `MCP_TRANSPORT` | `stdio` | `stdio` (local) or `sse` (remote / Docker) |
| `MCP_PORT` | `8002` | SSE listen port |
| `MCP_DEFAULT_PRODUCT` | `DEFAULT_PRODUCT` / `mosip` | Used when tools omit `product=` (`mosip` \| `inji`) |

---

## Other

| Variable | Purpose |
| --- | --- |
| `HF_TOKEN` | Optional HuggingFace token to avoid download rate limits (used by HF libs, not bound in `settings.py`) |

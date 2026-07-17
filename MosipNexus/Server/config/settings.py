"""
Central configuration for Nexus Server.

All tuneable constants and environment bindings live here.
Import this module everywhere instead of reading ``os.getenv()`` directly.

Environment loading order
-------------------------
1. ``load_dotenv(Server/.env)`` — prefers the package-local ``.env`` next to
   this package root (``Server/.env``), so running from another cwd still works.
2. ``load_dotenv()`` with no path — allows a process cwd / parent ``.env`` to
   supply additional keys (does not override already-set variables by default
   in python-dotenv).
3. Process environment (Docker Compose, Kubernetes ``nexus-env`` Secret, CI)
   is already present before dotenv runs and takes precedence for keys that
   were set by the orchestrator.

Helpers ``_csv`` / ``_csv_set`` parse comma-separated env values into lists/sets.
Section comments below group bindings by concern (product, Postgres, crawl
targets, retrieval, SMTP, etc.). See ``docs/ENVIRONMENT.md`` for the full
catalog.

Product-specific values (MOSIP vs Inji, docs/community URLs, GitHub org/repos)
are driven by environment variables so the same server code can serve multiple
products. On Rancher/Kubernetes, set these in the nexus-env Secret.
"""

from __future__ import annotations

import hashlib as _hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

# Prefer Server/.env (this package); also allow process env / parent .env overrides
_SERVER_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_SERVER_ROOT / ".env")
load_dotenv()


def _csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


def _csv_set(name: str, default: str = "") -> set[str]:
    return set(_csv(name, default))


# ── Multi-product crawl context ────────────────────────────────────────────────
# Set ACTIVE_PRODUCT=inji (or any slug) before running crawlers / ingestion to
# automatically resolve INJI_* prefixed env vars instead of the MOSIP defaults.
# The API server itself never sets this — it uses products.py for routing.
_ACTIVE = os.getenv("ACTIVE_PRODUCT", "").lower().replace("-", "_").replace(" ", "_")
_PREFIX = f"{_ACTIVE.upper()}_" if _ACTIVE else ""


def _penv(name: str, default: str = "") -> str:
    """Resolve env var with optional product-prefix override.

    With ACTIVE_PRODUCT=inji, ``_penv("DOCS_BASE_URL", ...)`` checks:
      1. ``INJI_DOCS_BASE_URL``  — product-specific override
      2. ``DOCS_BASE_URL``       — generic override
      3. ``default``             — built-in default
    """
    if _PREFIX:
        val = os.getenv(_PREFIX + name, "")
        if val:
            return val
    return os.getenv(name, default)


def _pcsv(name: str, default: str = "") -> list[str]:
    """Like _csv but respects the active product prefix."""
    raw = _penv(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


# ── Product identity (MOSIP / Inji / custom) ───────────────────────────────────
# Change these to reuse the same server for another product (e.g. Inji).
# When ACTIVE_PRODUCT=inji, these resolve INJI_* prefixed vars automatically.
_default_slug  = _ACTIVE or "mosip"
PRODUCT_NAME  = _penv("PRODUCT_NAME", f"{_default_slug.title()} Nexus")
PRODUCT_SHORT = _penv("PRODUCT_SHORT", _default_slug.upper())
# Prefix for JSON files and pgvector collection names (e.g. mosip → mosip_docs)
PRODUCT_SLUG  = _penv("PRODUCT_SLUG", _default_slug).lower().replace(" ", "_")

# ── Paths ──────────────────────────────────────────────────────────────────────
# Server/ is the package root (PYTHONPATH points here).
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DOCS_FILE      = DATA_DIR / f"{PRODUCT_SLUG}_docs.json"
COMMUNITY_FILE = DATA_DIR / f"{PRODUCT_SLUG}_community.json"
ESIGNET_FILE   = DATA_DIR / "esignet_docs.json"

# ── pgvector connection ────────────────────────────────────────────────────────
# Format: postgresql+psycopg://user:password@host:port/dbname
# On Rancher: set PG_CONNECTION in the nexus-env Secret.
PG_CONNECTION = os.getenv(
    "PG_CONNECTION",
    "postgresql+psycopg://mosip:mosip@localhost:5432/mosipnexus",
)

# SQLAlchemy pool — sized for parallel /chat retrieval across collections
PG_POOL_SIZE = int(os.getenv("PG_POOL_SIZE", "10"))
PG_MAX_OVERFLOW = int(os.getenv("PG_MAX_OVERFLOW", "20"))
PG_POOL_TIMEOUT = int(os.getenv("PG_POOL_TIMEOUT", "30"))
PG_POOL_RECYCLE = int(os.getenv("PG_POOL_RECYCLE", "1800"))

# ── Crawl targets (env-driven — MOSIP defaults; override for Inji etc.) ────────
# With ACTIVE_PRODUCT=inji, INJI_DOCS_BASE_URL is checked before DOCS_BASE_URL.
DOCS_BASE_URL = _penv("DOCS_BASE_URL", "https://docs.mosip.io/1.2.0")
DOCS_SITEMAP_URL = _penv(
    "DOCS_SITEMAP_URL",
    f"{DOCS_BASE_URL.rstrip('/')}/sitemap.xml",
)
COMMUNITY_BASE_URL = _penv("COMMUNITY_BASE_URL", "https://community.mosip.io")
ESIGNET_BASE_URL   = os.getenv("ESIGNET_BASE_URL", "https://docs.esignet.io")  # MOSIP-only
# Comma-separated list of website URLs to crawl (any public site, same-origin per entry)
WEBSITE_URLS       = _pcsv("WEBSITE_URLS", "https://www.mosip.io")
WEBSITE_FILE       = DATA_DIR / f"{PRODUCT_SLUG}_website.json"
WEBSITE_COLLECTION = _penv("WEBSITE_COLLECTION", f"{PRODUCT_SLUG}_website")
# Used by UI "Post to Community" deep-link (also returned from GET /config)
COMMUNITY_NEW_TOPIC_PATH = _penv("COMMUNITY_NEW_TOPIC_PATH", "/new-topic")

# ── Embeddings ─────────────────────────────────────────────────────────────────
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-base")  # 768-dim

# ── pgvector collection names ──────────────────────────────────────────────────
DOCS_COLLECTION      = _penv("DOCS_COLLECTION", f"{PRODUCT_SLUG}_docs")
COMMUNITY_COLLECTION = _penv("COMMUNITY_COLLECTION", f"{PRODUCT_SLUG}_community")
ESIGNET_COLLECTION   = os.getenv("ESIGNET_COLLECTION", "esignet_docs")  # MOSIP-only

# ── Chunking ───────────────────────────────────────────────────────────────────
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# ── Pipeline version ───────────────────────────────────────────────────────────
# Hash of parameters that, if changed, require a full re-embed from scratch.
PIPELINE_VERSION = _hashlib.md5(
    f"{EMBED_MODEL}|{CHUNK_SIZE}|{CHUNK_OVERLAP}|{PRODUCT_SLUG}".encode()
).hexdigest()[:8]

# ── Retrieval ──────────────────────────────────────────────────────────────────
# Defaults tuned for BYOK token cost (not max recall). Raise for research-heavy deploys.
RETRIEVAL_K       = int(os.getenv("RETRIEVAL_K", "4"))
RETRIEVAL_FETCH_K = int(os.getenv("RETRIEVAL_FETCH_K", "16"))
MAX_CONTEXT_DOCS  = int(os.getenv("MAX_CONTEXT_DOCS", "8"))
# Hard char budget for packed RAG context (~3–4k tokens at ~4 chars/token)
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))
# Parallel collection searches after a single query embedding
RETRIEVAL_PARALLELISM = int(os.getenv("RETRIEVAL_PARALLELISM", "4"))
# Cache identical query embeddings (helps bursty repeated questions)
EMBED_CACHE_SIZE = int(os.getenv("EMBED_CACHE_SIZE", "512"))

DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.88"))

CONFIDENCE_HIGH   = float(os.getenv("CONFIDENCE_HIGH", "0.75"))
CONFIDENCE_MEDIUM = float(os.getenv("CONFIDENCE_MEDIUM", "0.55"))

# ── BYOK token budget (chat LLM prompts) ───────────────────────────────────────
# How many prior messages to send to the answer LLM / condenser (pairs of Q/A)
LLM_MAX_HISTORY_MESSAGES = int(os.getenv("LLM_MAX_HISTORY_MESSAGES", "6"))
# Truncate each history message (assistant answers are the main token hog)
LLM_MAX_HISTORY_CHARS = int(os.getenv("LLM_MAX_HISTORY_CHARS", "600"))
# Cap completion length — answers stay useful without runaway generations
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1200"))
# DuckDuckGo fallback — fewer/shorter hits → fewer prompt tokens
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "2"))
MAX_WEB_CONTEXT_CHARS = int(os.getenv("MAX_WEB_CONTEXT_CHARS", "3500"))

# ── API concurrency ────────────────────────────────────────────────────────────
# Cap in-flight /chat (and other heavy) handlers so the process does not OOM
# or starve the embedding lock under a stampede.
MAX_CONCURRENT_CHATS = int(os.getenv("MAX_CONCURRENT_CHATS", "32"))
# In-memory sessions expire after idle TTL (multi-worker needs sticky sessions
# or an external store — keep UVICORN_WORKERS=1 unless you add Redis).
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
SESSION_MAX_COUNT = int(os.getenv("SESSION_MAX_COUNT", "5000"))
# Prefer 1 worker: HF model is ~1 GB RAM each; sessions are process-local.
UVICORN_WORKERS = int(os.getenv("UVICORN_WORKERS", "1"))
UVICORN_LIMIT_CONCURRENCY = int(os.getenv("UVICORN_LIMIT_CONCURRENCY", "64"))

# ── MCP server ─────────────────────────────────────────────────────────────────
MCP_PORT = int(os.getenv("MCP_PORT", "8002"))
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")  # stdio | sse

# ── LLM ───────────────────────────────────────────────────────────────────────
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ── Email notifications (optional) ────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL  = os.getenv("NOTIFY_EMAIL", "")

# ── LangSmith (optional observability) ────────────────────────────────────────
LANGSMITH_TRACING = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", f"{PRODUCT_SLUG}-nexus")

# ── Language detection ─────────────────────────────────────────────────────────
MIN_LANG_DETECT_CHARS  = int(os.getenv("MIN_LANG_DETECT_CHARS", "20"))
LANG_DETECT_CONFIDENCE = float(os.getenv("LANG_DETECT_CONFIDENCE", "0.95"))

# ── Community crawler ──────────────────────────────────────────────────────────
COMMUNITY_MAX_PAGES = int(os.getenv("COMMUNITY_MAX_PAGES", "50"))
COMMUNITY_MIN_POSTS = int(os.getenv("COMMUNITY_MIN_POSTS", "1"))
CRAWL_DELAY_SECS    = float(os.getenv("CRAWL_DELAY_SECS", "0.4"))

# ── GitHub crawler ─────────────────────────────────────────────────────────────
GITHUB_TOKEN      = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE   = os.getenv("GITHUB_API_BASE", "https://api.github.com")
GITHUB_FILE       = DATA_DIR / f"{PRODUCT_SLUG}_github.json"
GITHUB_COLLECTION = _penv("GITHUB_COLLECTION", f"{PRODUCT_SLUG}_github")
GITHUB_RETRIEVAL_K = int(os.getenv("GITHUB_RETRIEVAL_K", "3"))
GITHUB_MAX_ISSUES  = int(os.getenv("GITHUB_MAX_ISSUES", "500"))
GITHUB_ORG         = _penv("GITHUB_ORG", "mosip")

# Comma-separated repo names (not org/name) to always skip
GITHUB_REPO_EXCLUDE = _csv_set(
    "GITHUB_REPO_EXCLUDE",
    "documentation,mosip-acceptance-tests,mosip-functional-tests,"
    "performance-test-scripts,mosip-ref-impl,mosip-data,.github",
)

# Comma-separated languages; repos outside this set are skipped during discovery
GITHUB_USEFUL_LANGUAGES = _csv_set(
    "GITHUB_USEFUL_LANGUAGES",
    "Java,Python,Shell,TypeScript,JavaScript,Kotlin,Scala",
)

# Fallback repo list (org/name) when GITHUB_TOKEN is absent — comma-separated
_DEFAULT_REPOS = (
    "mosip/id-authentication,mosip/registration,mosip/registration-client,"
    "mosip/commons,mosip/partner-management-services,mosip/resident-services,"
    "mosip/keymanager,mosip/admin-ui,mosip/mosip-config,mosip/mosip-infra,"
    "mosip/mosip-helm,mosip/bio-utils,mosip/admin-services,mosip/print,"
    "mosip/mosip-openid-bridge"
)
GITHUB_REPOS = _pcsv("GITHUB_REPOS", _DEFAULT_REPOS)

# ── Code crawler ───────────────────────────────────────────────────────────────
CODE_FILE       = DATA_DIR / f"{PRODUCT_SLUG}_code.json"
CODE_COLLECTION = _penv("CODE_COLLECTION", f"{PRODUCT_SLUG}_code")
CODE_RETRIEVAL_K = int(os.getenv("CODE_RETRIEVAL_K", "4"))

CODE_INCLUDE_EXTENSIONS = _csv_set(
    "CODE_INCLUDE_EXTENSIONS",
    ".java,.yaml,.yml,.properties,.sql,.xml",
)
CODE_EXCLUDE_PATTERNS = _csv_set(
    "CODE_EXCLUDE_PATTERNS",
    "test,Test,IT.java,generated,target/,node_modules/,__pycache__,.mvn,vendor",
)
CODE_PRIORITY_PATTERNS = _csv_set(
    "CODE_PRIORITY_PATTERNS",
    "ErrorConstants,ExceptionConstants,StatusCode,ErrorCode,"
    "ServiceImpl,Controller,Handler,Exception",
)
CODE_MAX_FILE_BYTES = int(os.getenv("CODE_MAX_FILE_BYTES", "80000"))

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()  # text | json
LOG_ACCESS = os.getenv("LOG_ACCESS", "true").lower() in ("1", "true", "yes", "on")

# ── Confluence crawler (optional) ──────────────────────────────────────────────
CONFLUENCE_URL        = _penv("CONFLUENCE_URL", "")
CONFLUENCE_USER       = _penv("CONFLUENCE_USER", "")
CONFLUENCE_TOKEN      = _penv("CONFLUENCE_TOKEN", "")
CONFLUENCE_SPACE_KEYS = _pcsv("CONFLUENCE_SPACE_KEYS", "MOSIP")
CONFLUENCE_FILE       = DATA_DIR / f"{PRODUCT_SLUG}_confluence.json"
CONFLUENCE_COLLECTION = _penv("CONFLUENCE_COLLECTION", f"{PRODUCT_SLUG}_confluence")

# ── Jira crawler (optional) ────────────────────────────────────────────────────
JIRA_URL          = _penv("JIRA_URL", "")
JIRA_USER         = _penv("JIRA_USER", "")
JIRA_TOKEN        = _penv("JIRA_TOKEN", "")
JIRA_PROJECT_KEYS = _pcsv("JIRA_PROJECT_KEYS", "MOSIP")
JIRA_FILE         = DATA_DIR / f"{PRODUCT_SLUG}_jira.json"
JIRA_COLLECTION   = _penv("JIRA_COLLECTION", f"{PRODUCT_SLUG}_jira")

# ── HTTP headers ───────────────────────────────────────────────────────────────
HTTP_HEADERS = {
    "User-Agent": os.getenv(
        "HTTP_USER_AGENT",
        f"Mozilla/5.0 (compatible; {PRODUCT_SHORT}NexusBot/1.0)",
    )
}


def public_config(product: str | None = None) -> dict:
    """Safe subset of settings exposed to the UI via GET /config.

    Returns:
        Active product branding/URLs plus a ``products`` catalog for mode switching.
        No secrets or DSNs.
    """
    from config.products import public_config_payload

    return public_config_payload(product)

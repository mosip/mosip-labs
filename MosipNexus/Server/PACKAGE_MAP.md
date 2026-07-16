# Package documentation index
#
# Prefer these guides over scavenging git history:
#
#   docs/ARCHITECTURE.md     — request flow, RAG, DB, MCP
#   docs/ENVIRONMENT.md      — every important env var
#   docs/DATABASE_LAYER.md   — Alembic + models + repos
#   docs/DATABASE_SETUP.md   — Postgres prerequisites
#   docs/ADDING_DATA_SOURCES.md
#   docs/MCP_SERVER.md
#
# Code layout (documented packages):
#
#   api/           FastAPI routes
#   chain/         RAG ask() + summarizer
#   config/        settings.py (single env source of truth)
#   controllers/   chat / session / feedback / stats (API → db.crud)
#   errors.py      domain exceptions (shared; api/errors.py = HTTP handlers)
#   crawler/       external content → data/*.json
#   db/            SQLAlchemy models + repositories
#   ingestion/     JSON → pgvector
#   mcp_server/    Claude Desktop tools
#   memory/        SessionMemory view object
#   notifications/ SMTP helpers
#   retrieval/     hybrid search + dedup
#   alembic/       migrations (app tables only)
#   run_update.py  incremental crawl + ingest

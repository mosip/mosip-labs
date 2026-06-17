-- Runs inside the mosipnexus database on first container startup.
-- pgvector/pgvector:pg16 has the extension pre-installed; we just enable it.
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO mosip;

#!/usr/bin/env bash
# dump-vectors-to-s3.sh — Snapshot the local vector DB and upload to S3.
#
# Run this locally after a successful full ingestion to publish a snapshot that
# the initial-ingest Job (07-initial-ingest-job.yaml) will restore from during
# deployment. This replaces the 4–8 hour re-embed step with a ~10 minute restore.
#
# Prerequisites:
#   - pg_dump available locally (brew install libpq / apt install postgresql-client)
#   - aws CLI configured (aws configure, or set AWS_* env vars)
#   - Local PostgreSQL accessible (default: localhost:5436, matches docker-compose.yml)
#
# Usage:
#   bash Server/k8s/dump-vectors-to-s3.sh
#
# Environment overrides:
#   PG_HOST      default: localhost
#   PG_PORT      default: 5436
#   PG_USER      default: mosip
#   PG_DB        default: mosipnexus
#   S3_BUCKET    required (or set S3_VECTORS_BUCKET in environment)
#   S3_PREFIX    default: nexus
#   DATA_DIR     default: Server/data (where crawl_state.json lives)

set -euo pipefail

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5436}"
PG_USER="${PG_USER:-mosip}"
PG_DB="${PG_DB:-mosipnexus}"
S3_BUCKET="${S3_BUCKET:-${S3_VECTORS_BUCKET:-}}"
S3_PREFIX="${S3_PREFIX:-nexus}"
DATA_DIR="${DATA_DIR:-Server/data}"

if [ -z "$S3_BUCKET" ]; then
  echo "ERROR: S3_BUCKET (or S3_VECTORS_BUCKET) must be set." >&2
  echo "  export S3_BUCKET=your-bucket-name" >&2
  exit 1
fi

if [ -z "${PGPASSWORD:-}" ]; then
  echo "ERROR: PGPASSWORD must be set." >&2
  echo "  export PGPASSWORD=your_db_password" >&2
  exit 1
fi

DATE=$(date +%Y%m%d_%H%M%S)
DATED_KEY="${S3_PREFIX}/nexus_vectors_${DATE}.dump.gz"
LATEST_KEY="${S3_PREFIX}/nexus_vectors_latest.dump.gz"
STATE_DATED_KEY="${S3_PREFIX}/nexus_vectors_${DATE}_crawl_state.json"
STATE_LATEST_KEY="${S3_PREFIX}/nexus_vectors_latest_crawl_state.json"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MOSIP Nexus — vector snapshot upload"
echo "  DB:     ${PG_USER}@${PG_HOST}:${PG_PORT}/${PG_DB}"
echo "  Target: s3://${S3_BUCKET}/${LATEST_KEY}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: dump and stream directly to S3 (no local temp file) ────────────────
echo ""
echo "[1/3] Dumping and uploading vectors..."
pg_dump \
  -h "$PG_HOST" \
  -p "$PG_PORT" \
  -U "$PG_USER" \
  -d "$PG_DB" \
  -F c \
| gzip \
| aws s3 cp - "s3://${S3_BUCKET}/${DATED_KEY}"

echo "      Uploaded: s3://${S3_BUCKET}/${DATED_KEY}"

# ── Step 2: tag as latest ──────────────────────────────────────────────────────
echo ""
echo "[2/3] Tagging as latest..."
aws s3 cp "s3://${S3_BUCKET}/${DATED_KEY}" "s3://${S3_BUCKET}/${LATEST_KEY}"
echo "      Latest:   s3://${S3_BUCKET}/${LATEST_KEY}"

# ── Step 3: upload crawl_state.json alongside the dump ────────────────────────
echo ""
echo "[3/3] Uploading crawl_state.json..."
CRAWL_STATE="${DATA_DIR}/crawl_state.json"
if [ -f "$CRAWL_STATE" ]; then
  aws s3 cp "$CRAWL_STATE" "s3://${S3_BUCKET}/${STATE_DATED_KEY}"
  aws s3 cp "$CRAWL_STATE" "s3://${S3_BUCKET}/${STATE_LATEST_KEY}"
  echo "      Uploaded: s3://${S3_BUCKET}/${STATE_LATEST_KEY}"
else
  echo "      WARNING: ${CRAWL_STATE} not found — skipping."
  echo "               The restore job will still work; run_update will do a full delta."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done. Snapshot tagged as:"
echo "    s3://${S3_BUCKET}/${LATEST_KEY}"
echo ""
echo "  Set in 02-secret.yaml / Server/.env:"
echo "    S3_VECTORS_BUCKET=${S3_BUCKET}"
echo "    S3_VECTORS_KEY=${LATEST_KEY}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vector Snapshot Workflow

How engineering publishes a knowledge-base snapshot to S3, and how Rancher deployment
restores it in ~10 minutes instead of running a 4–8 hour full re-embed.

---

## Overview

```
Engineer machine                   S3 bucket                   Rancher cluster
──────────────────                 ─────────                   ───────────────
Full local ingest
  run_update.py              →  dump-vectors-to-s3.sh  →  07-initial-ingest-job
  (4–8 hrs, done once)          pg_dump | gzip | s3 cp     pg_restore (~10 min)
                                 crawl_state.json           nexus-data PVC
                                                                ↓
                                                         nightly 06-cronjob
                                                         (picks up delta only)
```

The snapshot contains the full pgvector database. Deployment restores it directly
into a fresh PostgreSQL instance. The nightly CronJob then keeps the KB fresh by
processing only content that changed since the snapshot date.

---

## Part 1 — Local setup and full ingestion (engineering, one-time)

### 1.1 Prerequisites

- Python 3.13 + `uv` — see [Server/README.md](../Server/README.md)
- PostgreSQL 16 + pgvector running locally — see [Server/docs/DATABASE_SETUP.md](../Server/docs/DATABASE_SETUP.md)
- All environment variables set in `Server/.env` — see [Server/docs/ENVIRONMENT.md](../Server/docs/ENVIRONMENT.md)
- AWS CLI configured with write access to the S3 snapshot bucket

Minimum `Server/.env` for full ingestion:

```ini
# Database
PG_CONNECTION=postgresql+psycopg://mosip:your_password@localhost:5436/mosipnexus
POSTGRES_PASSWORD=your_password

# LLM (used by ingestion summarizer)
GROQ_API_KEY=gsk_...

# Optional but recommended — raises GitHub crawl rate limit 60 → 5,000 req/hr
GITHUB_TOKEN=ghp_...

# Optional — Confluence and Jira knowledge sources
CONFLUENCE_URL=https://your-org.atlassian.net/wiki
CONFLUENCE_USER=your_email@example.com
CONFLUENCE_TOKEN=your_confluence_api_token
CONFLUENCE_SPACE_KEYS=QT,ENGG,PMS,MSD

JIRA_URL=https://your-org.atlassian.net
JIRA_USER=your_email@example.com
JIRA_TOKEN=your_jira_api_token
JIRA_PROJECT_KEYS=MOSIP,MISP
```

### 1.2 Start local PostgreSQL

```powershell
# From Server/ directory — starts postgres + API via Docker Compose
docker compose up -d postgres

# Verify pgvector is ready
docker compose exec postgres pg_isready -U mosip -d mosipnexus
```

### 1.3 Run full ingestion

```powershell
# From Server/ directory
uv run python run_update.py
```

This crawls all configured knowledge sources (docs, community, GitHub, Confluence, Jira,
source code) and embeds everything into pgvector. Expected runtime: **4–8 hours** on
first run. Subsequent runs (delta only) take 5–15 minutes.

Monitor progress in the terminal — it logs per-source chunk counts as it goes.

### 1.4 Verify the ingestion

```powershell
# Check collection chunk counts
uv run python -c "
from db.engine import get_engine
from sqlalchemy import text
with get_engine().connect() as conn:
    rows = conn.execute(text(
        'SELECT collection_id, count(*) FROM langchain_pg_embedding GROUP BY 1'
    ))
    for r in rows:
        print(r)
"
```

Or hit the local API health endpoint:

```powershell
# Start the API first if not running
docker compose up -d api

curl http://localhost:8000/health
```

Expected output shows non-zero chunk counts for each collection.

---

## Part 2 — Push snapshot to S3

### 2.1 Prerequisites

```powershell
# Install pg_dump (if not already available)
# Windows: bundled with PostgreSQL installer, or:
winget install PostgreSQL.PostgreSQL

# Verify AWS CLI is configured
aws sts get-caller-identity
```

The IAM user must have `s3:PutObject` and `s3:ListBucket` on the snapshot bucket.
See the [bucket setup section](#s3-bucket-setup) below if the bucket doesn't exist yet.

### 2.2 Create the S3 bucket (first time only)

```bash
# Create the bucket in your region
aws s3api create-bucket \
  --bucket mosip-nexus-vectors \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

# Block all public access
aws s3api put-public-access-block \
  --bucket mosip-nexus-vectors \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Auto-delete dated snapshots older than 30 days (the "latest" copies are kept)
aws s3api put-bucket-lifecycle-configuration \
  --bucket mosip-nexus-vectors \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-old-snapshots",
      "Status": "Enabled",
      "Filter": {"Prefix": "nexus/nexus_vectors_2"},
      "Expiration": {"Days": 30}
    }]
  }'
```

### 2.3 Run the dump script

Run from the **repo root** (not from `Server/`):

```powershell
# Set credentials
$env:PGPASSWORD = "your_local_db_password"
$env:S3_BUCKET  = "mosip-nexus-vectors"

# Optional overrides (defaults match docker-compose.yml)
# $env:PG_HOST = "localhost"
# $env:PG_PORT = "5436"
# $env:PG_USER = "mosip"
# $env:PG_DB   = "mosipnexus"

bash Server/k8s/dump-vectors-to-s3.sh
```

The script:
1. Streams `pg_dump | gzip` directly to S3 — no local disk space needed
2. Saves a dated copy: `nexus/nexus_vectors_20260721_140000.dump.gz`
3. Tags it as `latest`: `nexus/nexus_vectors_latest.dump.gz`
4. Uploads `Server/data/crawl_state.json` alongside it (so deployment knows what's already indexed)

Expected output:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MOSIP Nexus — vector snapshot upload
  DB:     mosip@localhost:5436/mosipnexus
  Target: s3://mosip-nexus-vectors/nexus/nexus_vectors_latest.dump.gz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/3] Dumping and uploading vectors...
      Uploaded: s3://mosip-nexus-vectors/nexus/nexus_vectors_20260721_140000.dump.gz

[2/3] Tagging as latest...
      Latest:   s3://mosip-nexus-vectors/nexus/nexus_vectors_latest.dump.gz

[3/3] Uploading crawl_state.json...
      Uploaded: s3://mosip-nexus-vectors/nexus/nexus_vectors_latest_crawl_state.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2.4 Update the deployment secret

Tell DevOps which bucket and key to use in `Server/.env` (for `seal-secrets.sh`):

```ini
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-south-1
S3_VECTORS_BUCKET=mosip-nexus-vectors
S3_VECTORS_KEY=nexus/nexus_vectors_latest.dump.gz
```

---

## Part 3 — Deployment (DevOps, using the snapshot)

### 3.1 Seal the secret

```bash
# From repo root — produces Server/k8s/02-sealed-secret.yaml (gitignored)
bash Server/k8s/seal-secrets.sh
```

### 3.2 Apply manifests in order

See the full Rancher guide: [MOSIP_Nexus_Rancher_Deployment_Guide.md](./MOSIP_Nexus_Rancher_Deployment_Guide.md)

Quick reference:

```bash
kubectl apply -f Server/k8s/00-namespace.yaml
kubectl apply -f Server/k8s/letsencrypt-prod-clusterissuer.yaml   # once per cluster
kubectl apply -f Server/k8s/01-postgres.yaml
kubectl apply -f Server/k8s/02-sealed-secret.yaml
kubectl apply -f Server/k8s/03-deployment-api.yaml
kubectl apply -f Server/k8s/04-service-api.yaml
kubectl apply -f Server/k8s/05-ingress-api.yaml
kubectl apply -f Server/k8s/06-cronjob.yaml
kubectl apply -f Server/k8s/08-postgres-backup.yaml
kubectl apply -f Server/k8s/09-hpa.yaml
kubectl apply -f Server/k8s/10-monitoring.yaml
kubectl apply -f UI/k8s/01-deployment-ui.yaml
kubectl apply -f UI/k8s/02-service-ui.yaml
kubectl apply -f UI/k8s/03-ingress-ui.yaml

# Last — restore vectors from S3 (~10 minutes)
kubectl apply -f Server/k8s/07-initial-ingest-job.yaml
kubectl wait --for=condition=complete job/nexus-initial-ingest \
  -n mosip-nexus --timeout=3600s
```

### 3.3 What happens during the restore job

```
Init 1 — wait-for-postgres:
  Polls pg_isready until PostgreSQL is accepting connections.

Init 2 — download-vectors:
  aws s3 cp s3://<bucket>/<key>  →  /vectors/nexus_vectors.dump.gz  (EmptyDir)
  aws s3 cp <state_key>          →  /vectors/crawl_state.json        (if exists)

Main  — restore-vectors:
  gunzip nexus_vectors.dump.gz
  pg_restore -h nexus-postgres -U mosip -d mosipnexus -F c --no-owner --no-acl
  cp crawl_state.json → nexus-data PVC
```

### 3.4 After restore

- pgvector is fully populated — queries work immediately
- `crawl_state.json` in the PVC records what was indexed at snapshot time
- The first nightly `run_update` run syncs only content new since the snapshot date
- No manual data copying or re-embedding needed

---

## Part 4 — Refreshing the snapshot

Publish a new snapshot whenever:

- A major new knowledge source is added (new Confluence space, new GitHub org)
- Embedding model or chunk size parameters change (requires full re-ingest anyway)
- The snapshot is more than 3 months old (prevents long delta catch-up on new deployments)

Steps:
1. Run `run_update.py` locally to ensure the local DB is fully up to date
2. Re-run `dump-vectors-to-s3.sh` — overwrites the `latest` key
3. Notify DevOps that a new snapshot is available (no manifest changes needed — `S3_VECTORS_KEY` already points to `latest`)

---

## IAM policy reference

**Engineering machine** (full write):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::mosip-nexus-vectors",
      "arn:aws:s3:::mosip-nexus-vectors/nexus/*"
    ]
  }]
}
```

**Cluster (restore job)** — read-only is sufficient:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::mosip-nexus-vectors",
      "arn:aws:s3:::mosip-nexus-vectors/nexus/*"
    ]
  }]
}
```

Consider separate IAM users (or IRSA roles on EKS) so the cluster never holds write credentials.

---

## Related docs

| Document | What it covers |
|---|---|
| [Server/README.md](../Server/README.md) | Local dev setup, folder structure |
| [Server/docs/ENVIRONMENT.md](../Server/docs/ENVIRONMENT.md) | All environment variables |
| [Server/docs/DATABASE_SETUP.md](../Server/docs/DATABASE_SETUP.md) | Local PostgreSQL + pgvector setup |
| [MOSIP_Nexus_Rancher_Deployment_Guide.md](./MOSIP_Nexus_Rancher_Deployment_Guide.md) | Full Rancher deployment guide |
| [Server/k8s/dump-vectors-to-s3.sh](../Server/k8s/dump-vectors-to-s3.sh) | Snapshot upload script |
| [Server/k8s/07-initial-ingest-job.yaml](../Server/k8s/07-initial-ingest-job.yaml) | S3 restore Job manifest |

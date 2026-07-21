# MOSIP Nexus AI — Rancher Deployment Guide

Infrastructure Requirements and Step-by-Step Setup | MOSIP Nexus AI — v1.0

---

## 1. Overview

This document covers the infrastructure requirements and step-by-step deployment of MOSIP Nexus AI on a Rancher Kubernetes cluster. MOSIP Nexus AI consists of four runtime components — a FastAPI backend (`Server/`), a React chat UI (`UI/` — HTTP client only, served by nginx), an optional FastMCP server for Claude Desktop (`Server/mcp_server/`), and a PostgreSQL database with the pgvector extension — plus a nightly CronJob that keeps the knowledge base up to date.

All Kubernetes manifests are included in the repository under `Server/k8s/` (API, DB, secrets, jobs) and `UI/k8s/` (React/nginx). MCP is included in `docker-compose.yml`; for Rancher, deploy an equivalent Deployment/Service for `mcp_server/server.py` (port 8002, `MCP_TRANSPORT=sse`) or expose it via Ingress if Claude Desktop must reach it remotely. See [MCP_SERVER.md](../Server/docs/MCP_SERVER.md).

---

## 2. Infrastructure Requirements

### 2.1 Compute — Node Specifications

| Tier | CPU | RAM | Suitable For |
| --- | --- | --- | --- |
| **Minimum (single node)** | 8 cores | 16 GB | Internal pilot, development |
| **Recommended (production)** | 8 cores × 2 nodes | 32 GB × 2 nodes | High availability, rolling restarts |

**Why these numbers:**

Each pod running the HuggingFace embedding model (`multilingual-e5-base`) loads approximately 1.1 GB of model weights into RAM (measured from the cached model files, not estimated). During the nightly knowledge update, the embedding process is CPU-intensive. The table below shows the resource footprint at steady state and during the nightly update.

| Component | CPU (steady) | RAM (steady) | Notes |
| --- | --- | --- | --- |
| nexus-postgres (pgvector) | 0.25 cores | 512 MB | Stores all vector embeddings |
| nexus-api (FastAPI) | 0.5 cores | ~2.5 GB | HF embedding model loaded in memory |
| nexus-ui (React / nginx) | 0.05–0.5 cores | ~64–256 MB | **No** HF model — proxies `/api` to FastAPI |
| nexus-mcp (FastMCP / Claude Desktop) | 0.25 cores | ~2.5 GB | HF model loaded; tools `search_knowledge`, `list_knowledge_sources`; port 8002 SSE |
| **Total — steady state (API+UI+DB)** | **~1.0 cores** | **~3.5–4 GB** | Add ~2.5 GB RAM if MCP is deployed |
| nexus-updater (nightly CronJob) | 1–4 cores | 4–8 GB | Runs ~15 min nightly, not always active |
| **Total — during nightly update** | **~5 cores** | **~8–13 GB** | Depends on whether MCP is co-located |

### 2.2 Storage Requirements

| Volume | Size | Purpose |
| --- | --- | --- |
| postgres-data PVC | 20 GB | pgvector embeddings (~70,000 chunks across all knowledge sources) |
| nexus-data PVC | 10 GB | Crawled JSON files and crawl state (used by nightly CronJob only) |
| nexus-db-backups PVC | 20 GB | Daily pg_dump files, 7-day retention |
| Node disk (per node) | 50 GB minimum | OS, Kubernetes, and Docker image (~3.5 GB image) |

### 2.3 Docker Image Size

Measured from the actual built image (`docker image inspect`), not estimated:

| Layer | Size (raw layer diff) |
| --- | --- |
| Debian + Python 3.13 base | ~220 MB |
| `uv sync` — LangChain, PyTorch CPU, transformers, psycopg, etc. | ~5.7 GB |
| Application source code (`COPY . .`) | ~1 MB |
| HuggingFace model bake-in (`multilingual-e5-base` + warm-up cache) | ~1.2 GB |
| **Total built image size** | **~3.5 GB** |

> Layer sizes don't sum linearly to the total — BuildKit deduplicates shared
> content across layers (e.g. files touched by multiple `RUN` steps), so the
> final image is smaller than the raw layers added together. The bottom-line
> total above is what `docker images`/`docker image inspect` reports for the
> image actually pulled onto each Rancher node.

### 2.4 Software Prerequisites

| Requirement | Version | Notes |
| --- | --- | --- |
| Rancher | 2.7 or later | Or any Kubernetes 1.28+ cluster |
| nginx Ingress Controller | Any current | Included with Rancher by default |
| cert-manager | v1.13+ | For automatic TLS via Let's Encrypt. Install via Rancher UI → Apps → cert-manager |
| Sealed Secrets controller | Latest | For encrypting secrets safe for git. `kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml` |
| Rancher Monitoring *(optional)* | Any | Enables Prometheus alert rules and HPA metrics. Rancher UI → Apps → Monitoring → Install |
| Storage class | Any ReadWriteOnce | `local-path` works for single-node; use Longhorn/NFS for multi-node |
| Container registry | Any | Docker Hub, GitHub Container Registry, or MOSIP Harbor |
| kubectl | Latest | For applying manifests |
| kubeseal CLI | Latest | Required to run `seal-secrets.sh`. `curl -L https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/kubeseal-linux-amd64 -o /usr/local/bin/kubeseal && chmod +x /usr/local/bin/kubeseal` |
| Docker | 24+ | For building and pushing the image |

### 2.5 Network Requirements

| Item | Requirement |
| --- | --- |
| Exposed ports | 80 / 443 via nginx Ingress (no direct NodePort needed) |
| Internal cluster networking | Standard pod-to-pod networking (no special config) |
| DNS entries | `nexus.mosip.io` → React UI, `nexus-api.mosip.io` → FastAPI |
| Egress — required | `api.groq.com` (LLM inference), `huggingface.co` (model download during build) |
| Egress — optional | `docs.mosip.io`, `community.mosip.io`, GitHub, Confluence (for knowledge crawlers) |

### 2.6 API Keys and Credentials Required

| Credential | Where to Get | Required? |
| --- | --- | --- |
| `PG_CONNECTION` | Set from PostgreSQL deployment | **Required** (API, MCP, ingest) |
| `GROQ_API_KEY` | console.groq.com (free) | Required for **ingestion summarizer** only — chat is BYOK / Claude |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` / `NOTIFY_EMAIL` | Your mail provider | Recommended — enables failure alert emails from the nightly updater |
| `PRODUCT_NAME` / `PRODUCT_SHORT` / `PRODUCT_SLUG` | Your choice | Optional (defaults MOSIP); set for Inji or rebranding |
| `DOCS_BASE_URL` / `COMMUNITY_BASE_URL` / `GITHUB_ORG` | Product docs/org | Optional overrides for crawl targets |
| `GITHUB_TOKEN` | github.com → Settings → Developer settings | Optional (raises rate limit from 60 to 5,000 req/hr) |
| `CONFLUENCE_TOKEN` | id.atlassian.com → Security → API tokens | Optional (Confluence knowledge source) |
| `LANGCHAIN_API_KEY` | smith.langchain.com (free) | Optional (observability tracing) |
| `MCP_TRANSPORT` / `MCP_PORT` | — | Set `sse` / `8002` when deploying MCP for Claude Desktop URL access |

UI pods need `NEXUS_API_URL=http://nexus-api:8000` (already in `04-deployment-ui.yaml`). They do **not** need `PG_CONNECTION` for chat.

---

### 2.7 Claude Desktop / MCP (optional)

MCP exposes **retrieval tools only** — Claude's own model answers the user.

| Tool | Description |
| --- | --- |
| `search_knowledge` | Search pgvector knowledge base (replaces older `search_mosip` name) |
| `list_knowledge_sources` | Live collection counts + configured URLs |

Client config (after exposing MCP SSE on your cluster or via port-forward):

```json
{
  "mcpServers": {
    "mosip-nexus": {
      "url": "https://<your-mcp-host>/sse"
    }
  }
}
```

Full detail: [MCP_SERVER.md](../Server/docs/MCP_SERVER.md).

---

## 3. Pre-Deployment Checklist

Before starting, confirm the following:

- [ ] Rancher cluster is running with at least 8 CPU cores and 16 GB RAM available
- [ ] nginx Ingress Controller is installed and active
- [ ] cert-manager is installed (`kubectl get pods -n cert-manager`)
- [ ] A `ClusterIssuer` named `letsencrypt-prod` exists (template commented in `Server/k8s/05-ingress-api.yaml`)
- [ ] Sealed Secrets controller is installed (`kubectl get pods -n kube-system | grep sealed-secrets`)
- [ ] kubeseal CLI is installed on the build machine (`kubeseal --version`)
- [ ] A storage class supporting ReadWriteOnce PVCs is available (`kubectl get storageclass`)
- [ ] Container registry is accessible from the build machine and from the cluster
- [ ] DNS entries for `nexus.mosip.io` and `nexus-api.mosip.io` point to the Rancher load balancer IP
- [ ] `GROQ_API_KEY` is obtained from console.groq.com
- [ ] `kubectl` is configured and can reach the cluster (`kubectl get nodes` succeeds)
- [ ] Docker is installed on the build machine

---

## 4. Step-by-Step Rancher Deployment

All commands below run from the repo root unless stated otherwise.

---

### Step 1 — Build and Push Docker Images

There are **two** images:

| Image | Dockerfile | Used by |
| --- | --- | --- |
| `nexus-server` | `Server/Dockerfile` | API, MCP, CronJob, ingest Job (HF model baked in) |
| `nexus-ui` | `UI/Dockerfile` | React SPA + nginx (lightweight — no embeddings) |

```powershell
# Server image (15–30 min first build — HF model download)
docker build -t nexus-server:v1.0.0 -f Server/Dockerfile Server
docker tag nexus-server:v1.0.0 your-registry.io/mosip/nexus-server:v1.0.0
docker push your-registry.io/mosip/nexus-server:v1.0.0

# UI image (fast)
docker build -t nexus-ui:v1.0.0 -f UI/Dockerfile UI
docker tag nexus-ui:v1.0.0 your-registry.io/mosip/nexus-ui:v1.0.0
docker push your-registry.io/mosip/nexus-ui:v1.0.0
```

Update `image:` in all manifests to point to your registry and tag. Never use `:latest` — pin every manifest to a specific version tag so rollbacks are possible.

---

### Step 2 — If Registry is Private, Configure Image Pull Secret

```powershell
kubectl create secret docker-registry registry-credentials `
  --docker-server=your-registry.io `
  --docker-username=your-username `
  --docker-password=your-password `
  --namespace mosip-nexus
```

Add `imagePullSecrets` to each deployment:

```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: registry-credentials
```

Skip this step if using a public registry.

---

### Step 3 — Create the Namespace

```powershell
kubectl apply -f Server/k8s/00-namespace.yaml
```

Verify:

```powershell
kubectl get namespace mosip-nexus
```

---

### Step 4 — Deploy PostgreSQL with pgvector

The `Server/k8s/01-postgres.yaml` file creates:

- A `pgvector/pgvector:pg16` StatefulSet (pre-installed pgvector extension)
- A 20 GB PersistentVolumeClaim for data
- A headless Service for stable DNS inside the cluster
- A ConfigMap with an init SQL script that enables the vector extension

```powershell
kubectl apply -f Server/k8s/01-postgres.yaml
```

Wait for PostgreSQL to be ready (takes ~60 seconds):

```powershell
kubectl rollout status statefulset/nexus-postgres -n mosip-nexus
```

Verify the pgvector extension was installed:

```powershell
kubectl exec -n mosip-nexus nexus-postgres-0 -- `
  psql -U mosip -d mosipnexus -c "\dx"
# Should show "vector" in the list of installed extensions
```

> **StorageClass Note:** If the PVC stays in `Pending` state, set the `storageClassName` field in `Server/k8s/01-postgres.yaml` to match your Rancher storage class. Find available classes with: `kubectl get storageclass`

---

### Step 5 — Configure Secrets (Sealed Secrets workflow)

`Server/k8s/02-secret.yaml` is a **template only** — never fill in real values there.
Populate `Server/.env` with real values and run the sealing script to produce
an encrypted `SealedSecret` that is safe to apply and commit to git.

```powershell
# Fill real values into Server/.env (this file is gitignored)
# Minimum required:
#   GROQ_API_KEY=gsk_...
#   POSTGRES_PASSWORD=your_strong_db_password
#   PG_CONNECTION=postgresql+psycopg://mosip:<password>@nexus-postgres:5432/mosipnexus

# Seal the .env into an encrypted SealedSecret
bash Server/k8s/seal-secrets.sh
# Produces Server/k8s/02-sealed-secret.yaml (encrypted, safe to commit)
```

Apply the sealed secret:

```powershell
kubectl apply -f Server/k8s/02-sealed-secret.yaml
```

> **Note:** The Sealed Secrets controller decrypts it automatically. `02-sealed-secret.yaml` is cluster-specific — regenerate it when rotating credentials or deploying to a new cluster. It is listed in `.gitignore` to prevent accidental cross-environment reuse.

---

### Step 6 — Deploy the API and UI

```powershell
kubectl apply -f Server/k8s/03-deployment-api.yaml
kubectl apply -f UI/k8s/01-deployment-ui.yaml
```

Watch the pods come up:

```powershell
kubectl get pods -n mosip-nexus -w
```

Expected output after ~2 minutes:

```text
NAME                          READY   STATUS    RESTARTS   AGE
nexus-api-xxx                 1/1     Running   0          2m
nexus-ui-xxx                  1/1     Running   0          2m
nexus-postgres-0              1/1     Running   0          5m
```

> **Note:** The `initialDelaySeconds: 60` on the liveness probe gives pods time to load the embedding model before health checks begin. Do not reduce this value.

---

### Step 7 — Apply Services and Ingress

Update the hostnames in `Server/k8s/05-ingress-api.yaml` and `UI/k8s/03-ingress-ui.yaml` if your domain differs from `nexus.mosip.io` / `nexus-api.mosip.io`.

```powershell
kubectl apply -f Server/k8s/04-service-api.yaml
kubectl apply -f UI/k8s/02-service-ui.yaml
kubectl apply -f Server/k8s/05-ingress-api.yaml
kubectl apply -f UI/k8s/03-ingress-ui.yaml
```

Verify ingress and TLS certificate:

```powershell
kubectl get ingress -n mosip-nexus
kubectl get certificate -n mosip-nexus
```

cert-manager issues the Let's Encrypt certificate automatically within 1–2 minutes. Status should show `READY = True`. If it stays `False`, run `kubectl describe certificaterequest -n mosip-nexus` to see the reason.

> **Prerequisite:** A `ClusterIssuer` named `letsencrypt-prod` must exist before applying the ingress. A commented YAML template is included at the bottom of `Server/k8s/05-ingress-api.yaml` — apply it once per cluster.

---

### Step 8 — Set Up the Nightly Update CronJob

The CronJob runs `run_update.py` every night at 02:00 UTC (07:30 IST). It crawls only new or changed content since the last run, which takes 5–15 minutes. A 10 GB PVC (`nexus-data`) stores the crawled JSON files and crawl state between runs.

The manifest includes `activeDeadlineSeconds: 21600` (6-hour hard limit). If a run hangs, the job is terminated and marked failed so Prometheus alerts fire rather than silently blocking the next scheduled run. If SMTP variables are set in the secret, a failure email is also sent to `NOTIFY_EMAIL`.

```powershell
kubectl apply -f Server/k8s/06-cronjob.yaml
```

Verify:

```powershell
kubectl get cronjob -n mosip-nexus
```

---

### Step 9 — Set Up Autoscaling and Monitoring

```powershell
# HPA — scales nexus-api between 1 and 4 replicas on CPU/memory
kubectl apply -f Server/k8s/09-hpa.yaml

# Daily PostgreSQL backup CronJob (03:30 UTC, 7-day retention)
kubectl apply -f Server/k8s/08-postgres-backup.yaml

# Prometheus ServiceMonitor + alert rules (requires Rancher Monitoring)
kubectl apply -f Server/k8s/10-monitoring.yaml
```

> Skip `10-monitoring.yaml` if the Rancher Monitoring stack is not installed. The API and CronJobs will still work — only Prometheus alerting is affected.

---

### Step 10 — First-Time Knowledge Ingestion

The pgvector database is empty on first deployment. First, copy the crawled
data files into the `nexus-data` PVC (these already exist — committed to the
repo, no crawling needed for docs/community/github/code):

```powershell
# Create a temporary transfer pod with the nexus-data PVC mounted
kubectl run -n mosip-nexus data-transfer --image=alpine --restart=Never `
  --overrides='{"spec":{"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"nexus-data"}}],"containers":[{"name":"data-transfer","image":"alpine","command":["sleep","3600"],"volumeMounts":[{"name":"data","mountPath":"/data"}]}]}}'

# Wait for the pod to start
kubectl wait pod/data-transfer -n mosip-nexus --for=condition=Ready --timeout=60s

# Copy data files from your local machine to the PVC
kubectl cp data/mosip_docs.json mosip-nexus/data-transfer:/data/
kubectl cp data/mosip_community.json mosip-nexus/data-transfer:/data/
kubectl cp data/mosip_github.json mosip-nexus/data-transfer:/data/
kubectl cp data/mosip_code.json mosip-nexus/data-transfer:/data/

# Clean up the transfer pod
kubectl delete pod data-transfer -n mosip-nexus
```

Then apply the one-time bootstrap Job:

```powershell
kubectl apply -f Server/k8s/07-initial-ingest-job.yaml
```

This runs `ingestion/store.py` (full ingest of docs/community/github/code from the files you copied — no live re-crawl) followed immediately by `run_update.py` (bootstraps Confluence/Jira from their live APIs if `CONFLUENCE_TOKEN`/`JIRA_TOKEN` are set in the sealed secret). Total runtime: 2–6 hours, mostly the embedding step.

Watch progress:

```powershell
kubectl logs -n mosip-nexus job/nexus-initial-ingest -f
```

Wait for completion before proceeding:

```powershell
kubectl wait --for=condition=complete job/nexus-initial-ingest \
  -n mosip-nexus --timeout=7200s
```

> **Re-running:** Jobs are immutable — re-applying after completion is a no-op. To re-run (e.g. after changing `EMBED_MODEL`/`CHUNK_SIZE`), delete it first: `kubectl delete job nexus-initial-ingest -n mosip-nexus`, then re-apply.

---

### Step 11 — Verify the Deployment

Check all pods are healthy:

```powershell
kubectl get pods -n mosip-nexus
```

Check the API health endpoint:

```powershell
kubectl exec -n mosip-nexus deploy/nexus-api -- `
  curl -s http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "collections": {
    "docs": 6094,
    "community": 11236,
    "github": 2513,
    "code": 38000
  },
  "active_sessions": 0
}
```

Verify TLS certificate and autoscaler:

```powershell
kubectl get certificate -n mosip-nexus
kubectl get hpa -n mosip-nexus
kubectl get cronjobs -n mosip-nexus
```

Access the application (HTTPS):

- React UI → `https://nexus.mosip.io`
- FastAPI Swagger → `https://nexus-api.mosip.io/docs`

Test a query:

```powershell
curl -X POST https://nexus-api.mosip.io/chat `
  -H "Content-Type: application/json" `
  -d '{"question": "What is MOSIP?", "language": "English"}'
```

---

## 5. Post-Deployment Operations

### 5.1 Trigger a Manual Knowledge Update

```powershell
kubectl create job --from=cronjob/nexus-updater nexus-update-manual -n mosip-nexus
```

Monitor the update:

```powershell
kubectl logs -n mosip-nexus -l job-name=nexus-update-manual -f
```

### 5.2 Update the Application to a New Version

```powershell
# Build and push new images
docker build -t your-registry.io/mosip/nexus-server:v1.1.0 -f Server/Dockerfile Server
docker build -t your-registry.io/mosip/nexus-ui:v1.1.0 -f UI/Dockerfile UI
docker push your-registry.io/mosip/nexus-server:v1.1.0
docker push your-registry.io/mosip/nexus-ui:v1.1.0

# Rolling update with zero downtime
kubectl set image deployment/nexus-api nexus-api=your-registry.io/mosip/nexus-server:v1.1.0 -n mosip-nexus
kubectl set image deployment/nexus-ui nexus-ui=your-registry.io/mosip/nexus-ui:v1.1.0 -n mosip-nexus

# Verify rollout
kubectl rollout status deployment/nexus-api -n mosip-nexus
kubectl rollout status deployment/nexus-ui -n mosip-nexus
```

### 5.3 View Application Logs

```powershell
# API logs
kubectl logs -n mosip-nexus deploy/nexus-api -f

# UI logs
kubectl logs -n mosip-nexus deploy/nexus-ui -f

# CronJob logs (last run)
kubectl logs -n mosip-nexus -l app=nexus-updater -f
```

### 5.4 Scale the API

The HPA (`09-hpa.yaml`) manages scaling automatically between 1–4 replicas based on CPU (>70%) and memory (>80%). Manual scaling overrides the HPA temporarily — the HPA reconciles back within a few minutes.

```powershell
# Manual override (HPA will reconcile)
kubectl scale deployment nexus-api -n mosip-nexus --replicas=2

# Check current HPA state
kubectl get hpa nexus-api -n mosip-nexus
```

### 5.5 Rotate Secrets

After updating `Server/.env`, re-seal and re-apply:

```powershell
bash Server/k8s/seal-secrets.sh
kubectl apply -f Server/k8s/02-sealed-secret.yaml
kubectl rollout restart deployment/nexus-api -n mosip-nexus
```

### 5.6 Restore PostgreSQL from Backup

Backups are stored in the `nexus-db-backups` PVC. To restore:

```powershell
# Shell into the backup pod
kubectl run -n mosip-nexus restore-shell --image=pgvector/pgvector:pg16 --restart=Never `
  --overrides='{"spec":{"volumes":[{"name":"bak","persistentVolumeClaim":{"claimName":"nexus-db-backups"}}],"containers":[{"name":"restore-shell","image":"pgvector/pgvector:pg16","command":["sleep","3600"],"volumeMounts":[{"name":"bak","mountPath":"/backups"}]}]}}'

# List available dumps
kubectl exec -n mosip-nexus restore-shell -- ls /backups

# Restore (replace the filename with the desired dump)
kubectl exec -n mosip-nexus restore-shell -- `
  pg_restore -h nexus-postgres -U mosip -d mosipnexus -F c /backups/mosipnexus_20260720_033001.dump

kubectl delete pod restore-shell -n mosip-nexus
```

### 5.7 Rebuild the Vector Database from Scratch

If the embedding model or chunking parameters change, all vectors must be regenerated:

```powershell
# Clear all vectors in pgvector
kubectl exec -n mosip-nexus nexus-postgres-0 -- `
  psql -U mosip -d mosipnexus `
  -c "DELETE FROM langchain_pg_embedding; DELETE FROM langchain_pg_collection;"

# Delete crawl state so all content is treated as new
kubectl exec -n mosip-nexus deploy/nexus-api -- `
  rm -f /app/MosipNexus/data/crawl_state.json

# Re-run full ingestion
kubectl exec -n mosip-nexus deploy/nexus-api -- `
  uv run python ingestion/store.py
```

---

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| Pod stuck in `Pending` | PVC not bound | Check storage class: `kubectl describe pvc -n mosip-nexus` |
| Pod stuck in `CrashLoopBackOff` | Missing secret or wrong DB password | `kubectl logs <pod> -n mosip-nexus` to see the error |
| `/health` returns `degraded` | pgvector unreachable or empty | Check postgres pod is running; verify PG_CONNECTION in secret |
| `502 Bad Gateway` from Ingress | Pod not yet ready | Wait for liveness probe to pass (up to 90 seconds after start) |
| TLS certificate stuck `READY = False` | DNS not yet propagated or wrong ClusterIssuer name | `kubectl describe certificaterequest -n mosip-nexus`; confirm DNS with `nslookup nexus.mosip.io` |
| Sealed secret decryption error | Wrong cluster or controller not running | Regenerate: run `seal-secrets.sh` against the target cluster |
| Nightly CronJob not running | CronJob schedule or timezone mismatch | `kubectl describe cronjob nexus-updater -n mosip-nexus` |
| CronJob hangs indefinitely | `activeDeadlineSeconds` not applied (old manifest) | Reapply `06-cronjob.yaml`; the 6-hour deadline kills and surfaces the failure |
| No failure email from CronJob | SMTP vars not set in secret | Add `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `NOTIFY_EMAIL` and re-seal |
| HPA not scaling | metrics-server not running | `kubectl top pods -n mosip-nexus`; install metrics-server if missing |
| Ingestion runs but chunk count is 0 | data/ files not copied to PVC | Repeat Step 10 data copy section |
| UI fails to load assets | Ingress / path rewrite | Confirm SPA fallback and `/api` proxy in nginx / ingress |
| Model download during pod start | HF model not baked in Server image | Rebuild: `docker build --no-cache -t nexus-server -f Server/Dockerfile Server` |
| Claude Desktop cannot connect to MCP | Wrong transport or path | Deploy MCP with `MCP_TRANSPORT=sse`, `MCP_PORT=8002`; client URL must end with `/sse`. See [MCP_SERVER.md](../Server/docs/MCP_SERVER.md) |
| MCP tool still named `search_mosip` | Outdated image/docs | Current tool is `search_knowledge` — rebuild/redeploy Server image |
| UI chat fails but API `/health` OK | nginx `/api` proxy or API service | Confirm `nexus-api:8000` reachable from UI pod; check nginx.conf proxy |

---

## 7. Kubernetes Manifest Summary

| File | What It Creates |
| --- | --- |
| `Server/k8s/00-namespace.yaml` | `mosip-nexus` namespace |
| `Server/k8s/01-postgres.yaml` | pgvector StatefulSet, PVC (20 GB), Service, init ConfigMap |
| `Server/k8s/02-secret.yaml` | Template only — never fill with real values; use `seal-secrets.sh` instead |
| `Server/k8s/02-sealed-secret.yaml` | Encrypted SealedSecret generated by `seal-secrets.sh` — apply this |
| `Server/k8s/03-deployment-api.yaml` | FastAPI (`PYTHONPATH=Server`, port 8000), `imagePullPolicy: IfNotPresent` |
| `Server/k8s/04-service-api.yaml` | ClusterIP for API (:8000) |
| `Server/k8s/05-ingress-api.yaml` | nginx Ingress → `nexus-api.mosip.io` with TLS via cert-manager |
| `Server/k8s/06-cronjob.yaml` | Nightly update CronJob (02:00 UTC), `activeDeadlineSeconds: 21600`, data PVC (10 GB) |
| `Server/k8s/07-initial-ingest-job.yaml` | One-time bootstrap Job — full ingest + Confluence/Jira population |
| `Server/k8s/08-postgres-backup.yaml` | Daily pg_dump CronJob (03:30 UTC), backup PVC (20 GB), 7-day retention |
| `Server/k8s/09-hpa.yaml` | HorizontalPodAutoscaler — nexus-api, 1–4 replicas, CPU 70% / memory 80% |
| `Server/k8s/10-monitoring.yaml` | ServiceMonitor + PrometheusRule (6 alert rules) — requires Rancher Monitoring |
| `Server/k8s/seal-secrets.sh` | Script: seals `Server/.env` into `02-sealed-secret.yaml` via kubeseal |
| `UI/k8s/01-deployment-ui.yaml` | React + nginx (`nexus-ui` image, port 80), `imagePullPolicy: IfNotPresent` |
| `UI/k8s/02-service-ui.yaml` | ClusterIP for UI (:80) |
| `UI/k8s/03-ingress-ui.yaml` | nginx Ingress → `nexus.mosip.io` with TLS via cert-manager |
| *(optional)* MCP Deployment | Mirror Compose `nexus-mcp`: `python mcp_server/server.py`, `MCP_TRANSPORT=sse`, port 8002 |

---

Document prepared: July 2026 | MOSIP Nexus AI — Infrastructure and Deployment

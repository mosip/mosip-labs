# Server Kubernetes manifests

Apply from the **repo root**. Fill secrets before applying `02-secret.yaml`.

## Apply order

```powershell
kubectl apply -f Server/k8s/00-namespace.yaml
kubectl apply -f Server/k8s/01-postgres.yaml
# edit Server/k8s/02-secret.yaml first
kubectl apply -f Server/k8s/02-secret.yaml
kubectl apply -f Server/k8s/03-deployment-api.yaml
kubectl apply -f Server/k8s/04-service-api.yaml
kubectl apply -f Server/k8s/05-ingress-api.yaml      # optional
kubectl apply -f Server/k8s/06-cronjob.yaml
kubectl apply -f Server/k8s/07-initial-ingest-job.yaml
```

Then deploy the UI: [UI/k8s/README.md](../../UI/k8s/README.md).

## Files

| File | Purpose |
| --- | --- |
| `00-namespace.yaml` | Shared namespace `mosip-nexus` |
| `01-postgres.yaml` | pgvector StatefulSet + PVC |
| `02-secret.yaml` | Env for API, MCP, ingest, cron (`PRODUCT_*`, URLs, tokens) |
| `03-deployment-api.yaml` | FastAPI (`nexus-server` image) |
| `04-service-api.yaml` | ClusterIP `:8000` |
| `05-ingress-api.yaml` | Host `nexus-api.mosip.io` |
| `06-cronjob.yaml` | Nightly `run_update.py` + data PVC |
| `07-initial-ingest-job.yaml` | One-time ingest Job |
| `postgres-init.sql` | Used by Compose / Postgres init |

Guides: [Server docs](../docs/README.md) · [Rancher](../../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md)

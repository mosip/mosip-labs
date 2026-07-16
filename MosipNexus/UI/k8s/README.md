# UI Kubernetes manifests

**Prerequisite:** apply [Server/k8s](../../Server/k8s/README.md) first (namespace, secret, API service).

The React UI (nginx) proxies browser `/api/*` to `http://nexus-api:8000` inside the cluster.

## Apply order

```powershell
kubectl apply -f UI/k8s/01-deployment-ui.yaml
kubectl apply -f UI/k8s/02-service-ui.yaml
kubectl apply -f UI/k8s/03-ingress-ui.yaml     # optional
```

## Files

| File | Purpose |
| --- | --- |
| `01-deployment-ui.yaml` | nginx + React (`nexus-ui` image) |
| `02-service-ui.yaml` | ClusterIP `:8501` |
| `03-ingress-ui.yaml` | Host `nexus.mosip.io` |

Customise UI manifests here without editing `Server/k8s/`.

Ops guide: [Rancher Deployment Guide](../../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md).

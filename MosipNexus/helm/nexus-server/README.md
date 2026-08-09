# nexus-server

Helm chart for the MOSIP Nexus Server — RAG API, crawlers, ingestion, pgvector,
and the scheduled jobs around it. A values-driven equivalent of the raw
manifests in [`../../Server/k8s/`](../../Server/k8s/README.md); both
deployment paths remain valid alternatives.

## TL;DR

Use [`../../deploy/nexus-server`](../../deploy/nexus-server/README.md)'s
`install.sh` — it wraps this chart, installs from the published repo, and
handles the `nexus-env` Secret for you (interactive prompt, never a values
file or `--set`). That's the documented path; see [Secrets](#secrets) below
for why this chart has no built-in way to create that Secret itself.

```console
cd ../../deploy/nexus-server && ./install.sh
```

To render/install this chart directly (e.g. for local `helm template`
testing), you need a Secret named `nexus-env` (or whatever
`secret.existingSecret` you set) to already exist in the target namespace —
this chart never creates one:

```console
helm repo add mosip https://mosip.github.io/mosip-helm
helm repo update
helm install nexus-server mosip/nexus-server \
  --namespace mosip-nexus --create-namespace \
  --set secret.existingSecret=nexus-env
```

## Prerequisites

- Kubernetes 1.24+, Helm 3.8+
- A default StorageClass (or set `postgres.storage.storageClassName` /
  `updater.pvc.storageClassName` / `backup.pvc.storageClassName`)
- One of:
  - An **Istio** mesh with an existing `Gateway` (default `api.routing.mode: istio`) — set `api.routing.istio.gateway` to it
  - An **nginx-ingress** controller + cert-manager (`api.routing.mode: nginx`)
- For `metrics.enabled: true`: the Prometheus Operator CRDs (`ServiceMonitor`, `PrometheusRule`) — e.g. Rancher Monitoring

## Installing

```console
cd ../../deploy/nexus-server && ./install.sh
```

See [Secrets](#secrets) for why `install.sh`, not a bare `helm install`, is
the supported path.

One install serves **both** MOSIP and Inji — the client picks the product
per-request (`X-Nexus-Product` header / `product` field), there's no
per-deployment MOSIP-only-vs-Inji-only mode to override here.

## Uninstalling

```console
helm uninstall nexus-server --namespace mosip-nexus
```

This does **not** delete PVCs (`postgres-data`, `nexus-data`, `nexus-db-backups`)
by default — they outlive the release so re-installing doesn't lose data.
Delete them manually if you really want a clean slate.

## Secrets

This chart has **no built-in way to create the `nexus-env` Secret** — it only
ever references one that already exists (`secret.existingSecret`, default
`nexus-env`), via `envFrom: secretRef` on the `nexus-api` container. There is
deliberately no chart-managed alternative (no `secret.create` toggle, no
`secret.env` values): a values file or `--set` are both bad places for a real
password — they end up in shell history, process listings, local disk, or CI
logs.

The expected keys mirror [`Server/.env.example`](../../Server/.env.example)
and [`../../Server/k8s/02-secret.yaml`](../../Server/k8s/02-secret.yaml).
Produce the Secret one of these ways:

1. **[`../../deploy/nexus-server/install.sh`](../../deploy/nexus-server/README.md#secrets---always-dynamic-never-helm-owned)**
   (the supported path) — creates it directly with `kubectl`, prompting
   interactively for `POSTGRES_PASSWORD` the first time only.
2. [`../../Server/k8s/seal-secrets.sh`](../../Server/k8s/seal-secrets.sh)
   (sealed-secrets) or an ExternalSecret, if you're managing it outside this
   chart entirely.

## Routing: Istio vs nginx-ingress

All routing config lives together under `api.routing` — the mode switch and
both modes' settings in one block. `api.routing.mode` picks exactly one of two
mutually exclusive templates:

| `api.routing.mode` | Renders | Uses | Requires |
| --- | --- | --- | --- |
| `istio` (default) | `VirtualService` | `api.routing.istio.*` (`gateway`, `hosts`, `prefix`) | An existing Istio `Gateway` in the cluster |
| `nginx` | `Ingress` + cert-manager annotations | `api.routing.ingress.*` (`host`, `className`, `tls`, …) | nginx-ingress controller, `letsencrypt-prod` ClusterIssuer (see `clusterIssuer.create`) |

## Key parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `namespace` | `mosip-nexus` | Namespace for all resources (create with `--create-namespace`) |
| `storageClassName` | `""` (cluster default) | Default StorageClass for all three PVCs (postgres/updater/backup). Each PVC's own `*.storageClassName` overrides this individually |
| `image.repository` / `image.tag` | `nexus-server` / `v1.0.0` | API + jobs image |
| `api.workers` / `api.limitConcurrency` | `1` / `64` | uvicorn flags |
| `api.autoscaling.enabled` | `true` | HPA 1–4 replicas, CPU 70% / memory 80% |
| `postgres.enabled` | `true` | Set `false` to use an external pgvector instance (set the existingSecret's `PG_CONNECTION` accordingly) |
| `updater.enabled` / `updater.schedule` | `true` / `0 2 * * *` | Nightly `run_update.py` CronJob |
| `updater.pvc.accessModes` | `[ReadWriteOnce]` | Set to `[ReadWriteMany]` on nfs-csi/nfs-client/Longhorn-RWX to avoid the CronJob pod getting stuck if scheduled on a different node between runs |
| `backup.enabled` / `backup.schedule` | `true` / `30 3 * * *` | Nightly `pg_dump` CronJob, 7-day retention |
| `backup.pvc.accessModes` | `[ReadWriteOnce]` | Same reasoning as `updater.pvc.accessModes` |
| `initialIngest.enabled` | `false` | One-time S3 vector-snapshot restore, runs as a `post-install` hook |
| `metrics.enabled` | `false` | ServiceMonitor + PrometheusRule (needs Prometheus Operator CRDs) |
| `api.routing.mode` | `istio` | `istio` or `nginx` — see above |
| `clusterIssuer.create` | `false` | Cluster-scoped Let's Encrypt issuer, only relevant for `api.routing.mode: nginx` |

See `values.yaml` for the full, commented list.

## Publishing

CI lints and publishes this chart via [`.github/workflows/mosip-nexus-chart-lint-publish.yml`](../../../.github/workflows/mosip-nexus-chart-lint-publish.yml)
(repo root, outside `MosipNexus/`) — a `mosip/kattu` reusable workflow, the
same one other MOSIP repos and `github-activity-tracker` (this repo's other
labs project) use. `CHARTS_DIR: ./MosipNexus/helm` discovers and
publishes both `nexus-server` and `nexus-ui` in one job. Runs on
`release: published`, pushes to `master`/`develop` touching `helm/**`,
`pull_request` (paths: `MosipNexus/helm/**`), or manual `workflow_dispatch`.
Publishes to `https://mosip.github.io/mosip-helm` (`gh-pages` branch of
`mosip/mosip-helm`) alongside every other MOSIP module chart. `CHART_PUBLISH`
defaults to `YES` on push/release, `NO` on manual dispatch (lint-only dry run
unless you explicitly opt in), and is always forced to `NO` on `pull_request`
— PR runs lint-only and never receive the publishing credentials.

## Related

- [Root README](../../README.md) · [Server README](../../Server/README.md)
- [Rancher deployment guide](../../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md)
- Raw manifests (alternative path): [`../../Server/k8s/`](../../Server/k8s/README.md)
- Deploy scripts (wraps this chart): [`../../deploy/nexus-server`](../../deploy/nexus-server/README.md)
- UI chart: [`../nexus-ui`](../nexus-ui/README.md)

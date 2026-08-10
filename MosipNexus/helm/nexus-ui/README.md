# nexus-ui

Helm chart for the MOSIP Nexus UI (React + nginx). A values-driven equivalent
of the raw manifests in [`../../UI/k8s/`](../../UI/k8s/README.md); that
directory is untouched and remains a valid alternative deployment path.

**Prerequisite:** install [`../nexus-server`](../nexus-server/README.md)
first, into the same namespace — this chart's nginx proxies same-origin
`/api/*` to the `nexus-api` Service created by that chart.

## TL;DR

From a local checkout (chart source):

```console
helm install nexus-ui . --namespace mosip-nexus --create-namespace
```

Or from the published chart, once CI has run (see [Publishing](#publishing)):

```console
helm repo add mosip https://mosip.github.io/mosip-helm
helm repo update
helm install nexus-ui mosip/nexus-ui --namespace mosip-nexus --create-namespace
```

## Prerequisites

- Kubernetes 1.24+, Helm 3.8+
- `../nexus-server` already installed in the same namespace
- One of:
  - An **Istio** mesh with an existing `Gateway` (default `routing.mode: istio`)
  - An **nginx-ingress** controller + cert-manager (`routing.mode: nginx`)

## Installing / Uninstalling

```console
helm install nexus-ui . --namespace mosip-nexus --create-namespace
helm uninstall nexus-ui --namespace mosip-nexus
```

## Routing: Istio vs nginx-ingress

All routing config lives together under `routing` — the mode switch and both
modes' settings in one block. Same switch as `nexus-server` — set
independently per chart if you need to:

| `routing.mode` | Renders | Uses | Requires |
| --- | --- | --- | --- |
| `istio` (default) | `VirtualService` | `routing.istio.*` (`gateway`, `hosts`, `prefix`) | An existing Istio `Gateway` |
| `nginx` | `Ingress` + cert-manager annotations | `routing.ingress.*` (`host`, `className`, `tls`, …) | nginx-ingress controller, a ClusterIssuer (see `../nexus-server`'s `clusterIssuer.create`) |

## Key parameters

Namespace isn't a chart parameter — every resource uses `.Release.Namespace`, so install this into the same namespace as nexus-server (`-n <ns>`, same as it was installed with).

| Parameter | Default | Description |
| --- | --- | --- |
| `image.repository` / `image.tag` | `nexus-ui` / `v1.0.0` | UI image |
| `routing.mode` | `istio` | `istio` or `nginx` |
| `routing.ingress.host` | `nexus.mosip.net` | Used when `routing.mode: nginx` |
| `routing.istio.hosts` | `[nexus.mosip.net]` | Used when `routing.mode: istio` |

See `values.yaml` for the full, commented list.

## Publishing

CI lints and publishes this chart via [`.github/workflows/mosip-nexus-chart-lint-publish.yml`](../../../.github/workflows/mosip-nexus-chart-lint-publish.yml)
(repo root, outside `MosipNexus/`) — see [Server chart → Publishing](../nexus-server/README.md#publishing)
for the full details. Both `nexus-server` and `nexus-ui` are discovered and
published together from the single `helm/` directory (`CHARTS_DIR: ./MosipNexus/helm`).

## Related

- [Root README](../../README.md) · [UI README](../../UI/README.md)
- Server chart: [`../nexus-server`](../nexus-server/README.md)
- Raw manifests (alternative path): [`../../UI/k8s/`](../../UI/k8s/README.md)
- Deploy scripts (wraps this chart): [`../../deploy/nexus-ui`](../../deploy/nexus-ui/README.md)

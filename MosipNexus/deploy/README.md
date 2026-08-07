# Deploy scripts

`install.sh` / `delete.sh` / `restart.sh` automation wrapping the Helm charts
in [`../helm/nexus-server`](../helm/nexus-server/README.md) and
[`../helm/nexus-ui`](../helm/nexus-ui/README.md). Mirrors the
`deploy/<component>/` convention used across other MOSIP repos (e.g.
keymanager, id-repository) — one subfolder per deployable Helm release.

## Order

```bash
cd deploy/nexus-server && ./install.sh
cd ../nexus-ui         && ./install.sh
```

`nexus-server` first — `nexus-ui` proxies `/api/*` to the `nexus-api` Service
it creates, in the same `mosip-nexus` namespace.

## Components

| Directory | Wraps | README |
| --- | --- | --- |
| `nexus-server/` | `helm/nexus-server` | [nexus-server/README.md](nexus-server/README.md) |
| `nexus-ui/` | `helm/nexus-ui` | [nexus-ui/README.md](nexus-ui/README.md) |

## Differences from the upstream MOSIP `deploy/` pattern

- No `copy_cm.sh` — Nexus doesn't consume MOSIP's shared platform ConfigMaps
  (`global`, `config-server-share`, …); it's a standalone app with its own
  `secret.env`.
- Charts are referenced by **local path**, not `helm install ... mosip/<chart>`
  from a published repo. This is deliberate even though CI now publishes both
  charts to `https://mosip.github.io/mosip-helm` (see [Server chart → Publishing](../helm/nexus-server/README.md#publishing))
  — these scripts are meant for deploying whatever's checked out locally
  (dev iteration, a feature branch), not a released version.
- `install.sh` uses `helm upgrade --install` (idempotent, safe to re-run)
  rather than a plain `helm install`.

## Related

- Raw `kubectl apply -f` manifests (alternative path, no scripts): [Server/k8s](../Server/k8s/README.md), [UI/k8s](../UI/k8s/README.md)
- [Rancher deployment guide](../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md)

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
- `install.sh` installs from the **published** Helm repo (`helm repo add
  mosip https://mosip.github.io/mosip-helm`), added/updated automatically —
  not a local chart checkout. The chart version is pinned (`CHART_VERSION`
  env var, defaults to the current chart version) so a routine redeploy
  can't silently pick up an incompatible newer chart — bump it deliberately.
- `install.sh` uses `helm upgrade --install` (idempotent, safe to re-run)
  rather than a plain `helm install`.
- `nexus-server`'s `install.sh` never lets Helm own the `nexus-env` Secret
  (`secret.create=false` + `secret.existingSecret`). It's created directly
  with `kubectl`, prompting for `POSTGRES_PASSWORD` interactively the first
  time and skipping creation on every later run — so `helm uninstall` /
  `./delete.sh` can never delete it. See [nexus-server/README.md](nexus-server/README.md#secrets---always-dynamic-never-helm-owned).

## Related

- Raw `kubectl apply -f` manifests (alternative path, no scripts): [Server/k8s](../Server/k8s/README.md), [UI/k8s](../UI/k8s/README.md)
- [Rancher deployment guide](../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md)

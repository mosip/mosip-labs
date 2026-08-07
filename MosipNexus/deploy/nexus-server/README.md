# Nexus Server — deploy scripts

Thin automation wrapper around [`../../helm/nexus-server`](../../helm/nexus-server/README.md).
Mirrors the `deploy/<component>/install.sh` / `delete.sh` / `restart.sh`
convention used across other MOSIP repos, with two deliberate differences:

- No `copy_cm.sh` step — Nexus doesn't consume MOSIP's shared platform
  ConfigMaps (`global`, `config-server-share`, …); all config lives in the
  chart's own `secret.env`.
- `install.sh` references the chart by **local path**, not the published Helm
  repo (`helm install ... mosip/nexus-server`) — deliberate, so these scripts
  always deploy whatever's checked out locally. See [chart README → Publishing](../../helm/nexus-server/README.md#publishing)
  for the published-chart path instead.

## Install / upgrade

```bash
./install.sh                                    # uses current kubeconfig, chart defaults
./install.sh /path/to/kubeconfig                 # explicit kubeconfig
./install.sh /path/to/kubeconfig my-secrets.yaml # + local values override (real secrets, storageClassName, routing.mode=nginx, ...)
```

Creates the `mosip-nexus` namespace if it doesn't already exist, then
`helm upgrade --install`s the release (safe to re-run; this is intentionally
idempotent, unlike a plain `helm install`).

`my-secrets.yaml` should stay **local and gitignored** — never commit real
API keys or passwords. See [chart README → Secrets](../../helm/nexus-server/README.md#secrets)
for the alternative (externally managed Secret via sealed-secrets).

## Restart

```bash
./restart.sh [kubeconfig]
```

Rolling-restarts the `nexus-api` Deployment only (e.g. after rotating a
Secret). Does not touch postgres.

## Uninstall

```bash
./delete.sh [kubeconfig]
```

Interactive-confirm before deleting the `nexus-server` helm release. Leaves
the namespace and all PVCs (`postgres-data`, `nexus-data`, `nexus-db-backups`)
in place — delete those manually if you actually want a clean slate.

## Related

- [Chart README](../../helm/nexus-server/README.md) — full parameter reference
- [nexus-ui deploy scripts](../nexus-ui/README.md) — install after this one

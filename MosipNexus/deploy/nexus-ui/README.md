# Nexus UI — deploy scripts

Thin automation wrapper around [`../../helm/nexus-ui`](../../helm/nexus-ui/README.md).
Mirrors the `deploy/<component>/install.sh` / `delete.sh` / `restart.sh`
convention used across other MOSIP repos. Installs from the **published**
Helm repo (`helm repo add mosip https://mosip.github.io/mosip-helm`, chart
`mosip/nexus-ui`), added/updated automatically on every run, at a **pinned
version** (`CHART_VERSION` env var, defaults to the chart's current
version) — a routine redeploy always gets exactly that version, not
whatever's newest. Bump it deliberately: `CHART_VERSION=1.1.0 ./install.sh`.

**Run [`deploy/nexus-server`](../nexus-server/README.md) first** — this
chart's nginx proxies same-origin `/api/*` to the `nexus-api` Service that
release creates, in the same `mosip-nexus` namespace.

## Install / upgrade

```bash
./install.sh                                    # uses current kubeconfig, chart defaults
./install.sh /path/to/kubeconfig                 # explicit kubeconfig
./install.sh /path/to/kubeconfig my-values.yaml  # + local values override (e.g. routing.mode=nginx)
```

Warns (but doesn't block) if the `nexus-api` Service isn't found yet. Safe to
re-run — uses `helm upgrade --install`.

## Restart

```bash
./restart.sh [kubeconfig]
```

## Uninstall

```bash
./delete.sh [kubeconfig]
```

Interactive-confirm before deleting the `nexus-ui` helm release. Doesn't
touch the `nexus-server` release or the shared namespace.

## Related

- [Chart README](../../helm/nexus-ui/README.md) — full parameter reference
- [nexus-server deploy scripts](../nexus-server/README.md) — install this first

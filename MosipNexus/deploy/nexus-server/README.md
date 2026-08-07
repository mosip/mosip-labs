# Nexus Server — deploy scripts

Thin automation wrapper around [`../../helm/nexus-server`](../../helm/nexus-server/README.md).
Mirrors the `deploy/<component>/install.sh` / `delete.sh` / `restart.sh`
convention used across other MOSIP repos, with two deliberate differences:

- No `copy_cm.sh` step — Nexus doesn't consume MOSIP's shared platform
  ConfigMaps (`global`, `config-server-share`, …); all config lives in the
  chart's own `secret.env`.
- `install.sh` installs from the **published** Helm repo
  (`helm repo add mosip https://mosip.github.io/mosip-helm`, chart
  `mosip/nexus-server`), added/updated automatically on every run.

## Install / upgrade

```bash
./install.sh                                                       # uses current kubeconfig
./install.sh /path/to/kubeconfig                                   # explicit kubeconfig
./install.sh /path/to/kubeconfig my-secrets.env my-values.yaml      # + optional overrides
```

Creates the `mosip-nexus` namespace if it doesn't already exist, then
`helm upgrade --install`s the release (safe to re-run; this is intentionally
idempotent, unlike a plain `helm install`).

### Secrets — always dynamic, never Helm-owned

`POSTGRES_PASSWORD`/`PG_CONNECTION` are never written to a values file or
passed via `--set` (shell history, CI logs). The first time you run
`install.sh`, if the `nexus-env` Secret doesn't already exist in the
namespace:

- interactively prompts (hidden input) for a PostgreSQL password — or set the
  `POSTGRES_PASSWORD` env var to skip the prompt (e.g. for CI). A password is
  **never** auto-generated; if the shell isn't interactive and the env var
  isn't set, the script errors out rather than silently making one up
- derives `PG_CONNECTION` from it automatically (password is percent-encoded,
  so special characters are safe)
- creates the Secret directly with `kubectl create secret generic` —
  **not** via Helm (`secret.create=false` + `secret.existingSecret=nexus-env`
  are always passed), so `helm uninstall` / `./delete.sh` never deletes it —
  this is what the Deployment's `envFrom: secretRef` actually reads at runtime

Re-running `install.sh` (redeploy, upgrade) checks whether `nexus-env`
already exists first — if so, nothing is prompted or overwritten. To rotate
the password, `kubectl -n mosip-nexus delete secret nexus-env` first, then
re-run `install.sh`.

Optional, non-required `secret.env` keys (`GITHUB_TOKEN`, `GROQ_API_KEY`,
`SMTP_*`, `AWS_*`, …) can be supplied via a local, gitignored dotenv file
(`KEY=value` lines, same keys as [`../../Server/.env.example`](../../Server/.env.example))
passed as the second argument — only read the first time the Secret is
created. Non-secret overrides (`storageClassName`, `image.tag`,
`api.routing.mode`, …) go in a normal Helm values file, the third argument.

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

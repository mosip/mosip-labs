# Nexus Server — deploy scripts

Thin automation wrapper around [`../../helm/nexus-server`](../../helm/nexus-server/README.md).
Mirrors the `deploy/<component>/install.sh` / `delete.sh` / `restart.sh`
convention used across other MOSIP repos, with two deliberate differences:

- No `copy_cm.sh` step — Nexus doesn't consume MOSIP's shared platform
  ConfigMaps (`global`, `config-server-share`, …); all config lives in the
  chart's own `secret.env`.
- `install.sh` installs from the **published** Helm repo
  (`helm repo add mosip https://mosip.github.io/mosip-helm`, chart
  `mosip/nexus-server`), added/updated automatically on every run, at a
  **pinned version** (`CHART_VERSION` env var, defaults to the chart's
  current version) — a routine redeploy always gets exactly that version,
  not whatever's newest. Bump it deliberately: `CHART_VERSION=1.1.0 ./install.sh`.

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

- interactively prompts (hidden input) for a PostgreSQL password — this is
  the **only** way to supply it. There is no env var shortcut and it's never
  auto-generated; if the shell isn't a real TTY, the script errors out
  rather than silently making one up or reading it from the environment
- derives `PG_CONNECTION` from it automatically (password is percent-encoded,
  so special characters are safe)
- creates the Secret directly with `kubectl create secret generic` —
  **not** via Helm (`secret.create=false` + `secret.existingSecret=nexus-env`
  are always passed), so `helm uninstall` / `./delete.sh` never deletes it —
  this is what the Deployment's `envFrom: secretRef` actually reads at runtime

Re-running `install.sh` (redeploy, upgrade) checks whether `nexus-env`
already exists first — if so, nothing is prompted or overwritten.

**Rotating the password:** a missing Secret does *not* mean an empty
database — Postgres only applies `POSTGRES_PASSWORD` on first bootstrap
(empty PGDATA), so an existing `postgres-data` PVC already has a role
password baked in that won't change just because the Secret does. Change
the *database's* password first, then the Secret, then restart the pod
holding stale connections:

```bash
kubectl -n mosip-nexus exec -it nexus-postgres-0 -- \
  psql -U mosip -d mosipnexus -c "ALTER ROLE mosip PASSWORD '<new password>';"
kubectl -n mosip-nexus delete secret nexus-env
./install.sh   # detects postgres-data already exists, asks you to confirm
               # you just changed it to match, then prompts for the SAME
               # password again — it derives/encodes PG_CONNECTION itself,
               # so you never hand-construct the connection string
./restart.sh
```

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

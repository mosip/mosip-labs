# AGENTS.md — MOSIP Nexus

Root-level instructions for AI coding agents. Component-specific detail lives in
[`Server/AGENTS.md`](Server/AGENTS.md) and [`UI/AGENTS.md`](UI/AGENTS.md) — read
whichever one covers the code you're editing in addition to this file.

## What this is

Production-grade RAG knowledge assistant serving **MOSIP** and **Inji** docs
(official docs, community forum, GitHub, Confluence, Jira, source code) from
**one server binary**. Product identity is chosen per-request (`X-Nexus-Product`
header / `product` field), not baked into a fork. A third `generic` profile
gives white-label BYOK chat with no RAG/vector KB.

## Repo layout

```text
MosipNexus/
├── Server/   # Python 3.13 FastAPI backend — RAG, crawlers, DB, MCP
│             # → Server/AGENTS.md
├── UI/       # React 19 + TypeScript + Vite frontend
│             # → UI/AGENTS.md
├── helm/     # Helm charts for both components (nexus-server, nexus-ui)
├── deploy/   # install.sh/delete.sh/restart.sh wrapping the helm/ charts
├── docs/     # Shared architecture / API / contributing docs
└── docker-compose.yml
```

Note: `MosipNexus/` itself is a subfolder of a larger `mosip-labs` monorepo —
`git rev-parse --show-toplevel` resolves one level above this directory.
CI workflows for this project live at that repo's root
(`../.github/workflows/mosip-nexus-*.yml`), not inside `MosipNexus/`.

## The one hard boundary

**`UI/` must never import from `Server/`.** They communicate only over HTTP
(`/api` via the Vite dev proxy, or nginx in Docker). If a change seems to need
UI code reaching into Server internals, it's the wrong shape — add/extend an
API endpoint instead.

## Running locally

```bash
# Server (from Server/) — installs .venv, deps, starts on :8010
./run.sh          # Linux/macOS
run.bat           # Windows

# UI (from UI/) — installs deps, starts Vite on :8501
./run.sh
run.bat

# Or full stack
docker compose up --build
```

Requires `Server/.env` (copy from `.env.example`) with at least `PG_CONNECTION`
set, and Postgres 16 + pgvector reachable.

- API Swagger: `http://localhost:8010/docs`
- MCP (SSE): `http://localhost:8002/sse`
- UI: `http://localhost:8501`

No CI runs Server tests or the UI build/typecheck — run those locally before
handing off work (see the component AGENTS.md files). CI does exist for
Docker image builds and Helm chart lint/publish, but it lives at the parent
`mosip-labs` repo root, not inside `MosipNexus/` — see
[`helm/nexus-server/README.md` → Publishing](helm/nexus-server/README.md#publishing)
if you're touching chart code.

## Helm chart gotchas

Two non-obvious things about `helm/nexus-server` and `helm/nexus-ui` that
aren't obvious from a first read of the templates:

- **Routing defaults to Istio, not nginx.** `routing.mode` (`api.routing.mode`
  in `nexus-server`, `routing.mode` in `nexus-ui`) defaults to `istio`, which
  renders a `VirtualService` against an existing Istio `Gateway` — not an
  `Ingress`. "Just add an ingress" instincts will silently do nothing on a
  default install unless you also set `routing.mode: nginx`. Worse: an
  invalid value (typo, wrong case) currently renders **neither** resource
  with **no error** — see chart README for the fix status.
- **Resource names are fixed, not release-templated.** `nexus-api`,
  `nexus-postgres`, `nexus-env`, etc. are hardcoded in every template, not
  derived from `{{ .Release.Name }}`. This is deliberate (matches the raw
  `k8s/` manifests, the Rancher guide, and Prometheus alert expressions
  exactly), but it means a second `helm install <other-name> .` in the same
  namespace **collides** with the first instead of creating a second
  instance — this chart is designed for one install per cluster/namespace.

## Conventions that span both components

- New env var → document in `Server/docs/ENVIRONMENT.md` and add to
  `Server/.env.example`, even if it's UI-facing (e.g. via `/config`).
- Prefer editing **Server** for RAG/DB/MCP logic; **UI** for presentation only
  — don't put business logic in the UI.
- Docstring conventions differ by language — see the component AGENTS.md files.

## Where to read more

- [`README.md`](README.md) — quick start, product-mode table, MCP setup.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system-wide component diagram.
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) — full HTTP + MCP endpoint map.
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — docstring conventions, doc regeneration.
- [`Server/AGENTS.md`](Server/AGENTS.md) — Server internals for agents.
- [`UI/AGENTS.md`](UI/AGENTS.md) — UI internals for agents.
- [`helm/nexus-server/README.md`](helm/nexus-server/README.md) / [`helm/nexus-ui/README.md`](helm/nexus-ui/README.md) — Helm charts.
- [`deploy/README.md`](deploy/README.md) — install/delete/restart scripts wrapping those charts.

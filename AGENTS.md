# AGENTS.md

## Repository Overview

`mosip-labs` is MOSIP's collection of experimental and incubating projects —
proof-of-concepts and integration demos built on top of the core MOSIP
(Modular Open Source Identity Platform) stack. Unlike most MOSIP repos, this
one is a **grab-bag of independent projects**, not a single service or a
family of tightly coupled modules. Each top-level project has its own stack,
its own build tooling, and its own lifecycle. There is no shared build file,
no shared dependency manifest, and no shared runtime at the repo root.

Because the projects are unrelated, this file is a hub: read it for
repo-wide facts (CI, branching, PR process), then follow the link to the
project you're actually touching for build/run/test detail.

## Projects in this repo

| Project | What it is | Stack | Guide |
| --- | --- | --- | --- |
| `MosipNexus/` | Production-grade RAG knowledge assistant for MOSIP/Inji docs, with a React UI and MCP (Claude Desktop) support | Python 3.13 FastAPI + React 19/TypeScript/Vite | [`MosipNexus/AGENTS.md`](MosipNexus/AGENTS.md) |
| `github-activity-tracker/` | Dashboard that syncs and visualizes GitHub org activity (commits, PRs, reviews, issues) across MOSIP repos | Node.js/Express backend + React/Vite frontend, Postgres | [`github-activity-tracker/AGENTS.md`](github-activity-tracker/AGENTS.md) |
| `ussd-proxy-service/` | Bridge service between a USSD gateway (Africa's Talking) and MOSIP Resident Services, for basic-phone identity access | Java 8, Spring Boot 2.3 | [`ussd-proxy-service/AGENTS.md`](ussd-proxy-service/AGENTS.md) |

`MosipNexus` already carries its own `AGENTS.md` tree (root plus
`Server/AGENTS.md` and `UI/AGENTS.md`) — this root file does not duplicate
that content, only points to it.

No project is empty or a placeholder; all three have real source, build
files, and (for `github-activity-tracker` and `MosipNexus`) working CI. None
looked abandoned at the time this file was written, though `ussd-proxy-service`
is visibly older (Java 8, Spring Boot 2.3, no automated tests) and gets far
less activity than the other two — treat changes there conservatively.

## Technology Stack

There is no repo-wide stack — each project picks its own (see the table
above). The only shared surface is:

- **CI**: GitHub Actions, defined once at `.github/workflows/` (repo root),
  not per-project.
- **Helm charts**: `github-activity-tracker/helm/` and `MosipNexus/helm/`
  are published to `https://mosip.github.io/mosip-helm`. `ussd-proxy-service`
  has no Helm chart — it ships a plain Dockerfile only.

## Build & Test Commands

There is no root-level build command — build each project from inside its
own directory. See the per-project `AGENTS.md` files linked above for exact
commands. Summary:

- `MosipNexus/Server` — `uv sync` / `pip install -r requirements.txt`, run
  via `./run.sh` or `run.bat`. `MosipNexus/UI` — `npm install`, `npm run dev`
  / `npm run build`. Full detail in `MosipNexus/AGENTS.md`.
- `github-activity-tracker/backend` — `npm install`, `npm start` / `npm run
  dev`. `github-activity-tracker/frontend` — `npm install`, `npm run dev` /
  `npm run build`. Detail in `github-activity-tracker/AGENTS.md`.
- `ussd-proxy-service` — Maven (`mvn clean install`, `mvn spring-boot:run`).
  Detail in `ussd-proxy-service/AGENTS.md`.

## Configuration

Every project keeps its own secrets and environment files local to its own
directory — there is no shared `.env` or config file at the repo root.
Never commit real tokens, API keys, or database passwords in place of the
`*.env.example` / `*-values.yaml` placeholders. See each project's guide for
which files hold local secrets (this matters more than usual here: as of
this writing, `ussd-proxy-service/src/main/resources/application.properties`
already has non-placeholder-looking values checked into version control —
do not copy that pattern into new code, and do not add further real
credentials to that file).

## Project Structure Notes

```text
mosip-labs/
├── .github/workflows/          # All CI for every project lives here, not per-project
├── MosipNexus/                 # RAG assistant — see MosipNexus/AGENTS.md
│   ├── Server/                 # FastAPI backend
│   ├── UI/                     # React frontend
│   └── helm/                   # nexus-server + nexus-ui charts
├── github-activity-tracker/    # GitHub activity dashboard — see github-activity-tracker/AGENTS.md
│   ├── backend/                # Express API + Postgres migrations
│   ├── frontend/                # React/Vite dashboard
│   └── helm/                   # gh-tracker-service + gh-tracker-ui charts
└── ussd-proxy-service/         # USSD-to-MOSIP bridge — see ussd-proxy-service/AGENTS.md
    └── src/main/java/...       # Spring Boot app (Maven, single module)
```

CI workflows are keyed by path, and the paths matter:

- `.github/workflows/chart-lint-publish.yml` lints/publishes only
  `github-activity-tracker/helm/**` changes.
- `.github/workflows/mosip-nexus-chart-lint-publish.yml` lints/publishes
  only `MosipNexus/helm/**` changes.
- `.github/workflows/push-trigger.yml` ("Maven Package upon a push") builds
  and Docker-packages `github-activity-tracker/backend`,
  `github-activity-tracker/frontend`, `MosipNexus/Server`, and
  `MosipNexus/UI` on every push to `master`, `develop`, `1.*`, `MOSIP*`, or
  `release*` — it has **no path filter**, so it runs on every such push
  regardless of which project changed. It does not build or package
  `ussd-proxy-service` at all — that project has no CI in this repo.
- `.github/workflows/update-reports.yml` is unrelated to any of the three
  projects above: a scheduled job (weekdays, cron) that runs against a
  separate `reporting` branch to refresh CSV/XLSX/Google Sheet exports via
  MinIO. It is not part of the normal PR/build flow for `develop`.

## Development Workflow

1. Work inside the one project directory your change belongs to. Do not
   introduce cross-project imports or shared code between `MosipNexus`,
   `github-activity-tracker`, and `ussd-proxy-service` — they are
   intentionally independent and deployed separately.
2. Branch from `develop` (the active integration branch for this repo, not
   `master`).
3. Build and, where the project has them, run tests locally before opening
   a PR — see the per-project guide for exact commands. `ussd-proxy-service`
   has no automated test suite in this repo; verify changes to it manually.
4. If you touch a Helm chart under `github-activity-tracker/helm/` or
   `MosipNexus/helm/`, expect the matching `chart-lint-publish` workflow to
   run lint automatically on your PR (publish only happens on `push`/
   `release`, never on `pull_request`).

## Pull Request Guidelines

- Target the `develop` branch.
- Keep code, build, and deployment changes scoped to one project — a PR
  that touches both `github-activity-tracker` and `ussd-proxy-service`,
  for example, is harder to review and to roll back independently.
  Repository-wide documentation changes (e.g. updating the root and
  per-project `AGENTS.md` files together) are exempt from this rule.
- Reference the tracking issue in the PR description.
- If your change affects a Helm chart's public interface (new required
  value, changed default), call that out explicitly in the PR body — chart
  consumers read `values.yaml` as the contract.

## Repository-Specific Considerations

- **This is not a monorepo in the usual sense.** Resist the instinct to
  factor out "shared" utilities between the three projects; none of the
  existing MOSIP conventions here assume that, and CI, Helm charts, and
  versioning are all per-project.
- **`ussd-proxy-service` is legacy relative to the other two**: Java 8,
  Spring Boot 2.3.12 (from 2020), no CI wiring in this repo, no test
  directory. Treat it as a maintenance/compliance surface, not a place to
  build new patterns — match its existing style rather than modernizing it
  in the same PR as a functional change.
- **`MosipNexus` already has thorough `AGENTS.md` coverage** (root +
  `Server/` + `UI/`); read those before making assumptions about it instead
  of re-deriving them from source.

## Agent rules

### Do

1. Read the project-specific `AGENTS.md` (or `MosipNexus/Server` /
   `MosipNexus/UI` guide) before editing inside that project.
2. Keep code, build, and deployment changes scoped to a single project
   per PR. Repository-wide documentation changes, such as coordinated
   root and project-specific `AGENTS.md` updates, are exempt from this
   rule.
3. Target `develop` when branching and opening PRs.
4. Use the placeholder/example env and values files (`*.env.example`,
   `*-values.yaml`) as the template for new configuration — never commit
   real secrets.
5. Verify claims about CI, build commands, or config against the actual
   workflow/build files in this repo rather than assuming another MOSIP
   repo's conventions apply here.

### Do not

1. Do not add shared code, shared build tooling, or cross-imports between
   `MosipNexus`, `github-activity-tracker`, and `ussd-proxy-service`.
2. Do not copy the checked-in, non-placeholder-looking values in
   `ussd-proxy-service/src/main/resources/application.properties` into new
   files, and do not add further real credentials to that file.
3. Do not assume `ussd-proxy-service` has CI, a Helm chart, or an automated
   test suite in this repo — it has none of the three.
4. Do not target `master` for PRs; this repo's active integration branch is
   `develop`.

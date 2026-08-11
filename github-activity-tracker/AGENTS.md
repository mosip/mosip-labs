# AGENTS.md

Guidance for the `github-activity-tracker` project inside the `mosip-labs`
monorepo. See [`../AGENTS.md`](../AGENTS.md) for repo-wide conventions
(branching, CI overview, PR scoping) — this file covers only what's specific
to this project.

## Repository Overview

`github-activity-tracker` syncs GitHub activity (commits, pull requests,
reviews, issues) for MOSIP organizations into a Postgres database and
presents it as a dashboard: per-user stats, leaderboards, team activity
trends, and role tracking. It is two independently deployable pieces:

- `backend/` — an Express API that talks to the GitHub API and Postgres,
  and exposes sync + query routes.
- `frontend/` — a React/Vite dashboard that consumes the backend API.

## Technology Stack

- **Backend**: Node.js, Express 4, `pg` (Postgres client), `axios` (GitHub
  API calls), `dayjs`/`luxon` for dates. Entry point `backend/app.js`.
- **Frontend**: React 18 + TypeScript, Vite, Tailwind CSS, Chart.js
  (`react-chartjs-2`), TanStack Query, `@supabase/supabase-js`,
  `lucide-react` icons.
- **Database**: Postgres 16 (`postgres:16-alpine` in Docker Compose), with
  hand-written SQL migrations under `backend/migrations/`.
- **Deployment**: Docker (per-component `Dockerfile`), Helm charts under
  `helm/gh-tracker-service/` and `helm/gh-tracker-ui/`.

## Build & Test Commands

There is no test suite in this project (no `test` script in either
`package.json`, no test files under `backend/` or `frontend/`). Verify
changes by running the app locally and exercising the affected routes/UI.

Backend (from `github-activity-tracker/backend/`):

```bash
npm install
npm start          # runs `node app.js`
npm run dev         # runs via nodemon, restarts on change
npm run migrate     # runs backend/migrations/runMigrations.js
npm run build        # copies app.js, package*.json, and source dirs into dist/
```

Frontend (from `github-activity-tracker/frontend/`):

```bash
npm install
npm run dev          # Vite dev server
npm run build         # production build
npm run lint          # eslint, zero warnings allowed (--max-warnings 0)
npm run preview       # preview the production build locally
```

Full stack via Docker Compose (from `github-activity-tracker/`):

```bash
docker compose up --build
```

This starts `db` (Postgres), `backend` (port 3000, runs migrations then
`node app.js`), and `frontend` (served on host port 80, container port
8080). To run migrations once against an already-running stack without
restarting the backend:

```bash
docker compose run --rm migrate
```

## Configuration

Two `.env.example` files exist and cover different scopes — copy the one
that matches how you're running the project, not both blindly:

- `github-activity-tracker/.env.example` — the **root** file, consumed by
  `docker-compose.yml` (`RDS_*` DB settings, `GITHUB_TOKEN`, `GITHUB_ORG`,
  `USER_ROLES`, `ALLOWED_ORIGINS`, plus commented `POSTGRES_*` values for
  the Postgres container itself). Copy to `github-activity-tracker/.env`
  for `docker compose up`.
- `github-activity-tracker/backend/.env.example` — the same `RDS_*` /
  `GITHUB_TOKEN` / `GITHUB_ORG` / `USER_ROLES` variables, scoped for running
  the backend directly with `npm start` outside Docker. Copy to
  `github-activity-tracker/backend/.env`.

`GITHUB_TOKEN` needs only the permissions required by the GitHub API calls
in `backend/` — these are all read queries (GraphQL requests sent over
HTTP `POST`, not write operations). Prefer a fine-grained token or GitHub
App with repository-scoped, read-only permissions instead of the broad
classic `repo` scope (create at `https://github.com/settings/tokens`).
Backend services read only `RDS_*` variables (not
`POSTGRES_*`); the `POSTGRES_*` variables in the root `.env.example` are for
the Docker Postgres container's own bootstrap, so both sets need to point at
the same database when running locally via Compose.

Helm deploys read from `deploy/gh-tracker-values.yaml` and
`deploy/gh-tracker-ui-values.yaml` — `deploy/README.md` explicitly warns to
fill in the required variables in both files before running `./install.sh`.

## Project Structure Notes

```text
github-activity-tracker/
├── backend/
│   ├── app.js                 # Express entry point
│   ├── routes/                 # One file per sync/query endpoint group
│   ├── services/                # Business logic behind each route
│   ├── migrations/              # Numbered SQL migrations + runMigrations.js
│   ├── config/                  # errorCodes.js, excludedGitHubLogins.js, syncConfig.js
│   ├── db/                      # dbPool.js, initLookupTables.js
│   └── utils/                    # githubClient.js, userRoleSql.js
├── frontend/
│   └── src/
│       ├── components/          # Dashboard widgets (charts, cards, tables)
│       └── lib/                  # api.ts, hooks.ts, organizations.ts, periods.ts
├── deploy/                      # install.sh / restart.sh / delete.sh wrapping the Helm charts
├── helm/
│   ├── gh-tracker-service/       # Backend chart
│   └── gh-tracker-ui/            # Frontend chart
└── docker-compose.yml
```

Migrations are plain numbered SQL files (`001_...` through `009_...` as of
this writing) run in order by `backend/migrations/runMigrations.js` — add a
new migration as the next number, don't edit an already-applied one.

## Development Workflow

1. Start Postgres (via `docker compose up db` or an external instance) and
   point `RDS_*` at it.
2. Run `npm run migrate` in `backend/` before starting the API for the
   first time, or after adding a new migration file.
3. Run backend (`npm run dev`) and frontend (`npm run dev`) separately for
   local iteration, or use `docker compose up --build` for the full stack.
4. Run `npm run lint` in `frontend/` before opening a PR — the CI-equivalent
   check has zero tolerance for warnings (`--max-warnings 0`).

## Pull Request Guidelines

- Target `develop` (see repo-wide [`../AGENTS.md`](../AGENTS.md)).
- If you change `backend/migrations/`, add a new file rather than editing
  an existing one — migrations already applied elsewhere must stay
  immutable.
- If you change `helm/gh-tracker-service/` or `helm/gh-tracker-ui/`,
  mention it in the PR body — `.github/workflows/chart-lint-publish.yml`
  lints those paths on every PR (publish to `gh-pages` only happens on
  `push`/`release`, not on `pull_request`).
- CI builds and Docker-packages both `backend/` and `frontend/` on pushes to
  `master`, `develop`, `1.*`, `MOSIP*`, and `release*` via
  `.github/workflows/push-trigger.yml` — there's no separate test gate, so
  a build failure there is the first signal something's broken.

## Repository-Specific Considerations

- The frontend's own `README.md` is the generic Vite/React template
  boilerplate — it has no project-specific instructions; use this file and
  the root `AGENTS.md` instead.
- `frontend/package.json` lists `pg` (a Postgres client) as a frontend
  dependency even though the frontend talks to the backend over HTTP, not
  directly to the database — don't take this as license to add direct DB
  access from frontend code; it should still go through `backend/`'s API.
- `GITHUB_ORG` and `USER_ROLES` are comma-separated lists read at backend
  startup (`USER_ROLES` seeds the `user_roles` table) — changing them
  requires a backend restart, not just a config file edit.

## Agent rules

### Do

1. Copy the `.env.example` that matches how you're running the project
   (root for Docker Compose, `backend/.env.example` for running the API
   directly) and fill in real values only in the untracked `.env` copy.
2. Add new SQL migrations as new numbered files under `backend/migrations/`.
3. Run `npm run lint` in `frontend/` before committing frontend changes.
4. Route all data access through `backend/`'s API from frontend code.

### Do not

1. Do not edit an already-numbered migration file that may already be
   applied elsewhere — add a new one instead.
2. Do not commit a real `GITHUB_TOKEN`, RDS password, or Helm
   `*-values.yaml` with production values filled in.
3. Do not add direct database access from `frontend/` code just because
   `pg` happens to be listed as a dependency there.
4. Do not assume there's a test suite to run — verify changes manually
   against the running app; none of `backend/` or `frontend/` has automated
   tests as of this writing.

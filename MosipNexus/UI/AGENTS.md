# AGENTS.md — UI

Instructions for AI coding agents working in `UI/`. See also the root
[`../AGENTS.md`](../AGENTS.md) for repo-wide rules (the UI/Server HTTP boundary
in particular).

React 19 + TypeScript + Vite front end for MOSIP Nexus. Presentation only —
talks to the Server exclusively over HTTP (`/api`). **Never import from
`../Server`.**

## Layout (`src/`)

| Path | Responsibility |
| --- | --- |
| `api/client.ts` | Typed fetch wrapper for the FastAPI backend. |
| `pages/ChatPage.tsx`, `pages/SettingsPage.tsx` | Main routed views. |
| `components/Sidebar.tsx` | Product switch (MOSIP/Inji/Direct), session list. |
| `components/MessageBubble.tsx` | Chat message rendering (markdown, confidence badges, sources). |
| `components/ExpertForm.tsx` | "Ask Expert" email escalation form. |
| `components/ErrorBanner.tsx`, `components/ErrorBoundary.tsx` | Error surfaces. |
| `lib/settings.ts` | BYOK LLM keys + preferences — persisted to `localStorage` only, never sent anywhere but the API request itself. |
| `lib/language.ts` | Language lock / script detection. |
| `lib/export.ts` | Export conversation as a styled downloadable HTML report. |
| `types.ts` | Shared TS types mirroring Server response shapes. |
| `styles.css` | MOSIP CSS design tokens; product logos switch with mode (`public/logos/mosip.png`, `inji.png`). |

## Running / building

```bash
npm ci            # or: npm install
npm run dev       # Vite dev server on :8501
npm run build     # tsc -p tsconfig.app.json --noEmit && vite build
npm run preview
```

Or `./run.sh` / `run.bat` — creates `.env` if missing, installs deps, starts Vite.

Node **≥ 20** required. Vite proxies `/api` → `VITE_DEV_API_PROXY` (default
`http://localhost:8010`) — start the Server first. In Docker, nginx proxies
`/api/` → `nexus-api:8000` (see `nginx.conf`).

## Tests

There is no test suite for the UI. `npm run build` (`tsc --noEmit` + `vite
build`) is the closest correctness signal — run it before handing off work.
No CI workflow is configured in this repo.

## Conventions

- JSDoc on exported symbols, e.g.:
  ```ts
  /** POST /chat — full RAG answer for one user question. */
  export async function chat(params: {...}): Promise<ChatResponse>
  ```
- Function components + hooks; `ErrorBoundary` is the only class component
  (React requires this for error boundaries).
- `package.json` is the dependency source of truth; `package-lock.json` locks
  exact versions for `npm ci`. `requirements.txt` here is a human-readable
  mirror of direct deps, not something to `pip install`.
- No linter/formatter config is checked in — match existing style.
- Product branding (name, docs/community URLs, logo, available sources) comes
  from the Server's `GET /config` — don't hardcode MOSIP/Inji strings in
  components; read from that response / `lib/settings.ts` instead.

## Where to read more

- [`README.md`](README.md) — features, branding, Docker.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — component tree, API client, settings/localStorage, nginx proxy.
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — npm scripts, env vars, folder map.
- [`../AGENTS.md`](../AGENTS.md) — repo-wide rules.

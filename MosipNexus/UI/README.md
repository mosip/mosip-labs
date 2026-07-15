# MOSIP Nexus UI (React)

React + TypeScript front end for MOSIP Nexus. It talks to the Server over HTTP only (`/api` → FastAPI via Vite proxy or nginx).

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Component tree, API client, settings/localStorage, nginx `/api` proxy, MOSIP CSS variables |
| [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) | npm scripts, env vars, Docker, folder map |

## Features

- **Product mode** — Switch **MOSIP** / **Inji** in the sidebar (logo, docs links, `X-Nexus-Product`)
- **Chat** — Markdown answers, confidence badges, source links, similar questions / threads
- **Settings (BYOK)** — Groq / Anthropic / OpenAI keys & models in **localStorage** only
- **Language** — Lock, script detection, “reply in …” instructions
- **Export** — Download the conversation as a styled HTML report
- **Ask Expert** — Email an expert on low-confidence / unanswered turns
- **Community** — Deep-link to post a new community topic
- **Claude Desktop** — MCP setup snippet in Settings (dual MOSIP / Inji entries)
- **UX** — Collapsible sidebar, typing indicator, scroll-to-latest

## Branding

Chrome uses a warm coral / light-slate UI palette. Product logos switch with mode
(`public/logos/mosip.png`, `inji.png`). CSS tokens live in `src/styles.css`.

## Local development

```powershell
copy .env.example .env
npm ci
# or: npm install
npm run dev
```

Or run **`run.bat`** (Windows) / **`./run.sh`** (Linux / macOS) — creates `.env` if missing, installs deps, starts Vite.

Node **≥ 20** required (see `engines` in `package.json`). Dependency lists:

| File | Role |
|------|------|
| `package.json` | Declared runtime + dev deps (source of truth) |
| `package-lock.json` | Exact versions for `npm ci` |
| `requirements.txt` | Human-readable mirror of direct deps |
Opens **http://localhost:8501**. Vite proxies `/api` → `VITE_DEV_API_PROXY` (default `http://localhost:8010`).

Start the Server first (`docker compose` or `uvicorn` on :8010 / :8000).

## Docker

```powershell
# Full stack from repo root
docker compose up --build
```

UI image: multi-stage Node build + **nginx** on port **8501**. Nginx proxies `/api/` to `http://nexus-api:8000/`.

## Layout

```text
UI/
├── docs/                # Architecture & development guides
├── src/                 # React app
├── public/
├── nginx.conf           # SPA + /api proxy
├── Dockerfile
├── package.json
├── package-lock.json
├── requirements.txt     # Direct deps mirror (install via npm)
└── k8s/
```

## Related

- [Server/README.md](../Server/README.md)
- [Root README](../README.md)

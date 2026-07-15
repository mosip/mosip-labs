# MOSIP Nexus UI — Development

## Prerequisites

- Node.js 22+ (Docker build uses `node:22-alpine`)
- Running Nexus Server (local `:8010` via compose publish, or `:8000` in-cluster)
- Copy env template: `copy .env.example .env` (PowerShell) from `UI/`

## npm scripts

| Script | Command | Purpose |
|--------|---------|---------|
| `npm run dev` | `vite` | Dev server on **http://localhost:8501**, HMR, `/api` proxy |
| `npm run build` | `tsc … --noEmit && vite build` | Typecheck + production bundle → `dist/` |
| `npm run preview` | `vite preview` | Serve `dist/` locally (no nginx `/api` unless you proxy yourself) |

```powershell
cd UI
copy .env.example .env
npm install
npm run dev
```

Start the Server before chatting (`docker compose` from repo root, or `uvicorn` on the proxy target).

## Environment variables

| Variable | Where | Default | Meaning |
|----------|-------|---------|---------|
| `VITE_DEV_API_PROXY` | `.env` / Vite | `http://localhost:8010` | Dev-only proxy target for `/api` |
| `VITE_NEXUS_API_URL` | `.env` / build | _(empty)_ | Absolute API base; leave empty to use same-origin `/api` |

Vite only exposes vars prefixed with `VITE_`. See `.env.example` for comments.

Docker build sets `VITE_NEXUS_API_URL=` so the browser always hits nginx `/api`.

## Docker

From repo root (recommended):

```powershell
docker compose up --build
```

UI Dockerfile (multi-stage):

1. **build** — `npm install` + `npm run build` → `dist/`
2. **runtime** — `nginx:1.27-alpine`, copies `nginx.conf` + `dist/`, listens **8501**

Nginx proxies `/api/` → `http://nexus-api:8000/`. Health: `GET /healthz`.

Standalone UI image build from `UI/`:

```powershell
docker build -t nexus-ui .
docker run --rm -p 8501:8501 nexus-ui
```

(API upstream must resolve as `nexus-api` or adjust `nginx.conf`.)

## Folder map

```text
UI/
├── docs/
│   ├── ARCHITECTURE.md      # Component tree, API, settings, nginx, palette
│   └── DEVELOPMENT.md       # This file
├── public/                  # Static assets copied as-is
├── src/
│   ├── api/
│   │   └── client.ts        # fetch wrapper + Server endpoints
│   ├── components/
│   │   ├── ExpertForm.tsx
│   │   ├── MessageBubble.tsx
│   │   └── Sidebar.tsx
│   ├── lib/
│   │   ├── export.ts        # HTML chat export
│   │   ├── language.ts      # Detect / instruct language
│   │   └── settings.ts      # localStorage BYOK settings
│   ├── pages/
│   │   ├── ChatPage.tsx
│   │   └── SettingsPage.tsx
│   ├── App.tsx              # Routes + config/settings ownership
│   ├── main.tsx             # React root + BrowserRouter
│   ├── styles.css           # MOSIP theme + layout
│   ├── types.ts             # Shared TypeScript types
│   └── vite-env.d.ts
├── k8s/                     # Kubernetes manifests (if present)
├── Dockerfile
├── nginx.conf
├── package.json
├── requirements.txt
├── run.bat
├── run.sh
├── vite.config.ts
├── tsconfig*.json
├── .env.example
└── README.md
```

## Tips

- Chat requires an LLM API key in **Settings** (stored under `nexus-ui-settings` in localStorage).
- Proxy rewrite strips `/api` so Server routes stay `/chat`, `/config`, etc.
- Prefer empty `VITE_NEXUS_API_URL` so cookies/CORS stay same-origin behind the proxy.

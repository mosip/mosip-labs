# MOSIP Nexus UI — Architecture

React + TypeScript SPA that talks to the Nexus Server over HTTP only. In development Vite proxies `/api`; in production nginx proxies `/api` to the FastAPI service.

## Component tree

```text
main.tsx
└── BrowserRouter
    └── App
        ├── Route "/" → ChatPage
        │   ├── Sidebar
        │   │   └── (New chat, Export, Language lock, Settings link)
        │   ├── message list
        │   │   └── MessageBubble (per turn)
        │   │       └── ExpertForm (low-confidence / web / unanswered)
        │   ├── composer (textarea + send)
        │   └── scroll-to-latest control
        └── Route "/settings" → SettingsPage
            └── BYOK provider / key / model / history turns
```

| Module | Role |
|--------|------|
| `App.tsx` | Loads product config, owns settings state + sidebar open flag, routes |
| `ChatPage.tsx` | Session, messages, language lock, chat send, similar-thread lookup, export |
| `SettingsPage.tsx` | LLM provider, API key, model, max history turns |
| `Sidebar.tsx` | Brand, actions, knowledge-source legend, language controls |
| `MessageBubble.tsx` | Markdown answer, confidence, sources, similar Qs, community CTA |
| `ExpertForm.tsx` | “Ask Expert” form → `POST /notify/expert` |

## API client (`src/api/client.ts`)

All browser calls go through `apiBase()`:

1. If `VITE_NEXUS_API_URL` is set → use that origin (no trailing slash).
2. Otherwise → same-origin `/api` (Vite proxy or nginx).

| Export | Method | Path | Notes |
|--------|--------|------|-------|
| `getConfig` | GET | `/config` | Falls back to MOSIP defaults on failure |
| `chat` | POST | `/chat` | Question, session, language, BYOK fields |
| `findSimilar` | POST | `/similar` | Returns `null` when `found` is false |
| `deleteSession` | DELETE | `/session/:id` | Best-effort; errors ignored |
| `notifyExpert` | POST | `/notify/expert` | Email + question context |
| `ApiError` | — | — | Typed HTTP / timeout / reachability errors |

Shared `request()` helper: JSON body, `Accept: application/json`, AbortController timeout (default 120s; shorter for config/session/similar).

## Settings & localStorage (`src/lib/settings.ts`)

| Item | Value |
|------|--------|
| Storage key | `nexus-ui-settings` |
| Shape | `SettingsState`: `llmProvider`, `llmApiKey`, `llmModel`, `maxHistoryTurns` |
| Defaults | Groq, empty key, `openai/gpt-oss-120b`, 10 turns |
| Lifecycle | `App` loads on mount via `loadSettings()`; persists on every change via `saveSettings()` |

Keys never leave the browser except as request headers/body to the Nexus API for the user’s chosen provider. They are not stored server-side by the UI.

Supporting tables: `PROVIDER_MODELS` (model pickers), `PROVIDER_META` (labels, key hints, console URLs).

## Nginx `/api` proxy

Production image serves `dist/` from nginx on port **8501** (`nginx.conf`):

- `location /` — SPA `try_files` → `index.html`
- `location /api/` — `proxy_pass http://nexus-api:8000/` (strips `/api` prefix via trailing-slash `proxy_pass`)
- Timeouts: connect 10s, read 180s (chat can be slow)
- `location /healthz` — plain `ok` for probes

Local Vite mirrors this: proxy `/api` → `VITE_DEV_API_PROXY` (default `http://localhost:8010`) with path rewrite `/api` → ``.

```text
Browser ──► /api/chat ──► nginx/Vite ──► FastAPI /chat
```

## Branding CSS variables (MOSIP palette)

Defined on `:root` in `src/styles.css`:

| Variable | Hex | Use |
|----------|-----|-----|
| `--brand-blue` | `#1b52a4` | Primary brand / CTAs (`--primary`) |
| `--brand-sky` | `#00a2e5` | Accent (`--accent`) |
| `--brand-yellow` | `#fec40d` | Amber line / highlights |
| `--brand-orange` | `#f58020` | Warnings (`--amber`) |
| `--brand-red` | `#d64246` | Danger / errors |
| `--brand-green` | `#098855` | Success / high confidence |

Neutrals: `--ink`, `--ink-muted`, `--paper`, `--line`. Semantic aliases (`--primary-soft`, `--ok-bg`, etc.) and layout tokens (`--radius`, `--shadow`, `--font-display` Outfit, `--font-body` Source Sans 3, `--sidebar-w`) complete the theme.

## Supporting libs

| File | Purpose |
|------|---------|
| `lib/language.ts` | Script heuristics + “reply in X” instruction parse; language lock UX |
| `lib/export.ts` | Build downloadable HTML chat report |
| `types.ts` | Shared DTOs aligned with Server JSON |

## Data flow (chat turn)

```text
User input
  → language instruction / script detect (optional lock prompt)
  → findSimilar (optional banner)
  → chat({ question, sessionId, language, llm* })
  → append user + assistant ChatMessage
  → MessageBubble renders markdown / sources / ExpertForm
```

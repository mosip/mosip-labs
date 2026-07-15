# HTTP API reference

Base URL (local compose): `http://localhost:8010`  
Interactive docs (examples included): `http://localhost:8010/docs` · `/redoc`  
Machine-readable: `http://localhost:8010/openapi.json`

Request/response models with **OpenAPI examples** live in
[`Server/api/schemas.py`](../Server/api/schemas.py). Routes are wired in
[`Server/api/main.py`](../Server/api/main.py).

---

## Error responses

All HTTP errors use a structured body (see [`Server/api/errors.py`](../Server/api/errors.py)):

```json
{
  "detail": {
    "code": "CAPACITY_EXCEEDED",
    "message": "Server is at capacity (too many parallel chats). Retry shortly, or raise MAX_CONCURRENT_CHATS.",
    "details": { "retry_after": 2 },
    "request_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11"
  }
}
```

| Code | Status | When |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Pydantic / query validation |
| `BAD_REQUEST` / `LLM_KEY_REQUIRED` / `INVALID_SESSION_ID` / `LLM_AUTH_FAILED` | 400 | Bad input or rejected LLM key |
| `SESSION_NOT_FOUND` / `TURN_NOT_FOUND` / `NOT_FOUND` | 404 | Missing session or turn |
| `UPSTREAM_ERROR` | 502 | LLM or retrieval upstream failure |
| `CAPACITY_EXCEEDED` | 503 | `MAX_CONCURRENT_CHATS` saturated (`Retry-After: 2`) |
| `INTERNAL_ERROR` | 500 | Unexpected server fault |

Pass `X-Request-Id` (or `X-Correlation-Id`) to have it echoed in `detail.request_id`.

---

## System

### `GET /config`

Public branding for the UI (no secrets).

**Response example**

```json
{
  "product_name": "MOSIP Nexus",
  "product_short": "MOSIP",
  "product_slug": "mosip",
  "docs_base_url": "https://docs.mosip.io/1.2.0",
  "community_base_url": "https://community.mosip.io",
  "community_new_topic_url": "https://community.mosip.io/new-topic",
  "github_org": "mosip"
}
```

| Field | Meaning |
| --- | --- |
| `product_*` | Display name / short label / slug for collections |
| `docs_base_url` | Official docs root |
| `community_new_topic_url` | Deep-link for “Post to Community” |
| `github_org` | Org crawled for issues/code |

### `GET /health`

| Field | Meaning |
| --- | --- |
| `status` | `ok` or `degraded` (HTTP **503** when degraded) |
| `collections` | Non-zero pgvector counts (`docs`, `community`, …) |
| `active_sessions` | Non-cleared Postgres sessions |

---

## Chat

### `POST /chat`

Main RAG turn. **Requires** `llm_api_key` (BYOK).

**Request example**

```json
{
  "question": "What does IDA-MLC-009 mean and how do I fix it?",
  "session_id": null,
  "language": "English",
  "llm_provider": "groq",
  "llm_api_key": "gsk_your_groq_api_key_here",
  "llm_model": "llama-3.3-70b-versatile",
  "notify_on_low_confidence": true
}
```

| Field | Meaning |
| --- | --- |
| `question` | User question |
| `session_id` | Prior UUID to continue; `null` starts a new session |
| `language` | Desired answer language |
| `llm_provider` | `groq` \| `anthropic` \| `openai` |
| `llm_api_key` | Caller key — never stored |
| `llm_model` | Optional model override |
| `notify_on_low_confidence` | Queue SMTP if confidence is low |

**Response example**

```json
{
  "answer": "**IDA-MLC-009** indicates a missing or invalid UIN/VID…",
  "sources": [
    {
      "source": "https://docs.mosip.io/1.2.0/id-authentication/error-codes",
      "title": "IDA Error Codes",
      "source_type": "docs",
      "tags": "",
      "accepted": false
    }
  ],
  "source_type": "mixed",
  "confidence": "high",
  "similar_questions": ["How to resolve IDA-MLC-002?"],
  "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11"
}
```

| Field | Meaning |
| --- | --- |
| `answer` | Markdown answer |
| `sources` | Citations (`source_type`: docs/community/github/code/…) |
| `confidence` | `high` \| `medium` \| `low` \| `n/a` |
| `session_id` | Pass back on the next turn |

**Errors:** `400` missing key · `503` concurrency limit (`Retry-After: 2`)

### `POST /batch`

Up to **10** questions sequentially in one session (same BYOK fields).

---

## Search

### `POST /search`

Vector search only (no LLM).

```json
{ "query": "packet manager status codes", "k": 5 }
```

Returns `{ "query", "total", "results": [{ "content", "source", "title", "source_type" }] }` — `content` truncated to 500 chars.

### `POST /similar`

Community near-duplicate check (threshold `DEDUP_THRESHOLD`).

```json
{ "question": "How do I configure ABIS host URL in MOSIP?" }
```

```json
{
  "found": true,
  "title": "ABIS host configuration in application properties",
  "source": "https://community.mosip.io/t/abis-host-url/5678",
  "similarity_score": 0.91,
  "message": "A similar community thread was found."
}
```

---

## Sessions

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/session` | `{ "session_id", "status": "created" }` |
| `GET` | `/session/{id}/history` | Alternating `user` / `assistant` messages |
| `GET` | `/sessions` | Active sessions list |
| `DELETE` | `/session/{id}` | Soft-clear → `{ "status": "cleared" }` |
| `POST` | `/export/{id}?format=json\|html` | JSON turns or HTML download |

---

## Feedback & analytics

### `POST /feedback`

```json
{
  "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
  "turn": 1,
  "rating": "positive",
  "comment": "Clear explanation with the right error code."
}
```

`turn` is **1-based**. Returns `{ "status": "recorded", "feedback_id": "…" }`.

### `GET /stats`

Aggregates from `query_events` + feedback (confidence / source_type / language distributions).

---

## Notifications

### `POST /notify/expert`

Queues SMTP (background). Requires Server `SMTP_*` + `NOTIFY_EMAIL`.

```json
{
  "question": "Our Synergy env fails ABIS callback but local works — why?",
  "language": "English",
  "user_email": "engineer@example.gov",
  "context": "Low-confidence answer suggested checking firewall…",
  "unanswered": false
}
```

Set `unanswered: true` when `/chat` returned `source_type=none`.

---

## MCP (separate process)

Not under FastAPI. See [Server/docs/MCP_SERVER.md](../Server/docs/MCP_SERVER.md).

| Transport | Endpoint |
| --- | --- |
| SSE | `http://localhost:8002/sse` |
| Tools | `search_knowledge`, `list_knowledge_sources` |

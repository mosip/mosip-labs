# White-label / direct BYOK reuse

Open-source adopters can run this Server **without** MOSIP or Inji documentation URLs.

## Modes

| Mode | `product` | `answer_mode` | Needs pgvector KB? |
| --- | --- | --- | --- |
| MOSIP RAG | `mosip` | `rag` (default) | Yes (`mosip_*`) |
| Inji RAG | `inji` | `rag` (default) | Yes (`inji_*`) |
| Direct BYOK | `generic` | `direct` (default) | **No** |

`generic` is a white-label profile: empty docs/community/GitHub by default. Chat calls the caller’s LLM with the provided `llm_api_key` (Groq, Anthropic, OpenAI, or xAI Grok).

## REST example

```bash
curl -s http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -H "X-Nexus-Product: generic" \
  -d '{
    "question": "Give three tips for a first interview",
    "language": "English",
    "llm_provider": "xai",
    "llm_api_key": "'"$XAI_API_KEY"'",
    "llm_model": "grok-3-mini",
    "product": "generic",
    "answer_mode": "direct",
    "system_prompt": "You are a helpful coach. Be concise and practical."
  }'
```

You can force direct mode on any product with `"answer_mode": "direct"` (skips retrieval).

## Branding env (optional)

| Variable | Default | Purpose |
| --- | --- | --- |
| `GENERIC_PRODUCT_NAME` | `Nexus` | Display name in `/config` and prompts |
| `GENERIC_PRODUCT_SHORT` | `Assistant` | Short label |
| `GENERIC_DEFAULT_ANSWER_MODE` | `direct` | Product default |
| `GENERIC_RETRIEVAL_ENABLED` | `false` | Set `true` only if you ingest `generic_*` collections |
| `GENERIC_DOCS_BASE_URL` etc. | empty | Optional links for your own UI |

## UI

Sidebar **Direct** mode sets `product=generic` and `answer_mode=direct`.

## MCP

MCP `search_knowledge` is for vector retrieval (MOSIP / Inji). Direct BYOK Q&A uses the REST `/chat` API from your application — not MCP search.

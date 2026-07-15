# Contributing & documentation map

## Where docs live

| Path | Purpose |
| --- | --- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System-wide architecture |
| [API_REFERENCE.md](./API_REFERENCE.md) | HTTP + MCP endpoint map |
| [Server/docs/](../Server/docs/) | Database, env, MCP, crawlers, Server architecture |
| [UI/docs/](../UI/docs/) | React architecture & local development |
| Code docstrings / JSDoc | Inline next to implementations |

## Docstring conventions

**Python (Server)** — Google-style for public functions:

```python
def retrieve(query: str, k: int = 8) -> tuple[list[Document], str]:
    """Search collections and return documents plus confidence.

    Args:
        query: User or condensed search string.
        k: Max chunks per primary collection.

    Returns:
        (documents, confidence) where confidence is high|medium|low.
    """
```

**TypeScript (UI)** — JSDoc on exported symbols:

```ts
/** POST /chat — full RAG answer for one user question. */
export async function chat(params: {...}): Promise<ChatResponse>
```

## Changing behaviour

1. Prefer editing **Server** for RAG/DB/MCP; **UI** for presentation only.
2. New app tables → SQLAlchemy model + Alembic revision (`Server/docs/DATABASE_LAYER.md`).
3. New crawl source → `Server/docs/ADDING_DATA_SOURCES.md`.
4. New env knobs → `Server/docs/ENVIRONMENT.md` + `.env.example`.

## Regenerating stakeholder docs

```powershell
cd docs
uv run --project ../Server python generate_docs.py
```

Produces `MOSIP_Nexus_Developer_Guide.docx` and `MOSIP_Nexus_Presentation.pptx`.

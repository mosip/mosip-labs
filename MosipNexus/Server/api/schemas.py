"""
Pydantic request/response schemas for the Nexus REST API.

Each model includes field descriptions and OpenAPI **examples** so Swagger UI
(`/docs`) and ReDoc show realistic payloads. Import these from ``api.main``
rather than redefining DTOs elsewhere.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Shared ─────────────────────────────────────────────────────────────────────

class SourceItem(BaseModel):
    """One citation attributed to an answer or search hit."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source": "https://docs.mosip.io/1.2.0/id-authentication/overview",
                    "title": "ID Authentication — Overview",
                    "source_type": "docs",
                    "tags": "",
                    "accepted": False,
                }
            ]
        }
    )

    source: str = Field(
        "",
        description="Canonical URL or file path of the source chunk.",
        examples=["https://docs.mosip.io/1.2.0/id-authentication/overview"],
    )
    title: str = Field(
        "",
        description="Human-readable title (page, issue, or file name).",
        examples=["ID Authentication — Overview"],
    )
    source_type: str = Field(
        "",
        description=(
            "Origin of the chunk: `docs`, `community`, `github`, `code`, "
            "`confluence`, `jira`, or `web`."
        ),
        examples=["docs"],
    )
    tags: str = Field(
        "",
        description="Optional community tags or labels (comma-separated).",
        examples=["ida,authentication"],
    )
    accepted: bool = Field(
        False,
        description="True when this community answer was marked accepted on the forum.",
        examples=[False],
    )


# ── System ─────────────────────────────────────────────────────────────────────

class ConfigResponse(BaseModel):
    """Public product branding returned by ``GET /config`` (safe for browsers)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_name": "MOSIP Nexus",
                    "product_short": "MOSIP",
                    "product_slug": "mosip",
                    "docs_base_url": "https://docs.mosip.io/1.2.0",
                    "community_base_url": "https://community.mosip.io",
                    "community_new_topic_url": "https://community.mosip.io/new-topic",
                    "github_org": "mosip",
                }
            ]
        }
    )

    product_name: str = Field(..., description="Full product display name shown in the UI.")
    product_short: str = Field(..., description="Short name used in copy (e.g. MOSIP, Inji).")
    product_slug: str = Field(..., description="Lowercase slug for files/collections (e.g. mosip).")
    docs_base_url: str = Field(..., description="Official documentation site root.")
    community_base_url: str = Field(..., description="Community forum root URL.")
    community_new_topic_url: str = Field(
        ...,
        description="Deep-link to create a new community topic (UI 'Post to Community').",
    )
    github_org: str = Field(..., description="GitHub organisation crawled for issues/code.")
    logo_url: str = Field(
        "/logos/mosip.png",
        description="UI path to the product logo asset.",
    )
    retrieval_enabled: bool = Field(
        True,
        description="Whether this product has a vector knowledge base for RAG.",
    )
    default_answer_mode: str = Field(
        "rag",
        description="Default answer mode when the client omits `answer_mode`: `rag` | `direct`.",
    )
    default_product: str = Field(
        "mosip",
        description="Server default product slug when the client omits a mode.",
    )
    active_product: str = Field(
        "mosip",
        description="Product selected for this config response (header/query).",
    )
    products: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Catalog of all product profiles the UI can switch between.",
    )
    answer_modes: list[str] = Field(
        default_factory=lambda: ["rag", "direct"],
        description="Supported answer modes for `/chat`.",
    )


class HealthResponse(BaseModel):
    """Liveness/readiness payload from ``GET /health``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "collections": {
                        "docs": 12840,
                        "community": 4521,
                        "github": 3102,
                        "code": 18900,
                    },
                    "active_sessions": 12,
                },
                {
                    "status": "degraded",
                    "collections": {"error": "Unable to read collection stats."},
                    "active_sessions": 0,
                },
            ]
        }
    )

    status: str = Field(
        ...,
        description="`ok` when DB + embedder are reachable; `degraded` on failure (HTTP 503).",
        examples=["ok"],
    )
    collections: dict[str, Any] = Field(
        ...,
        description=(
            "Non-zero pgvector collection row counts keyed by label "
            "(`docs`, `community`, `github`, `code`, …), or an `error` key when degraded."
        ),
    )
    active_sessions: int = Field(
        ...,
        description="Count of non-cleared chat sessions in Postgres.",
        examples=[12],
        ge=0,
    )


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Body for ``POST /chat`` — one RAG turn (BYOK required)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "What does IDA-MLC-009 mean and how do I fix it?",
                    "session_id": None,
                    "language": "English",
                    "llm_provider": "groq",
                    "llm_api_key": "gsk_your_groq_api_key_here",
                    "llm_model": "openai/gpt-oss-120b",
                    "notify_on_low_confidence": True,
                },
                {
                    "question": "Can you explain that error in Tamil?",
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "language": "Tamil",
                    "llm_provider": "anthropic",
                    "llm_api_key": "sk-ant-api03-xxxxxxxx",
                    "llm_model": "claude-haiku-4-5-20251001",
                    "notify_on_low_confidence": True,
                },
            ]
        }
    )

    question: str = Field(
        ...,
        min_length=1,
        description="Natural-language question about the product knowledge base.",
        examples=["What does IDA-MLC-009 mean and how do I fix it?"],
    )
    session_id: str | None = Field(
        None,
        description=(
            "UUID from a previous `/chat` or `/session` response. "
            "Omit or null to start a new conversation."
        ),
        examples=["a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11"],
    )
    language: str = Field(
        "English",
        description="Desired answer language (e.g. English, Tamil, Hindi).",
        examples=["English"],
    )
    llm_provider: str = Field(
        "groq",
        description="LLM backend: `groq` | `anthropic` | `openai` | `xai` | `grok`.",
        examples=["groq"],
    )
    llm_api_key: str | None = Field(
        None,
        description=(
            "Caller-owned API key (BYOK). Required for `/chat` and `/batch`. "
            "Never logged or stored on the server."
        ),
        examples=["gsk_your_groq_api_key_here"],
    )
    llm_model: str | None = Field(
        None,
        description="Optional model override for the chosen provider.",
        examples=["openai/gpt-oss-120b"],
    )
    notify_on_low_confidence: bool = Field(
        True,
        description=(
            "If true and confidence is low (non-chat/web/none), queue an optional "
            "SMTP alert to `NOTIFY_EMAIL`."
        ),
        examples=[True],
    )
    product: str | None = Field(
        None,
        description=(
            "Product mode: `mosip` | `inji` | `generic`. "
            "Overrides `X-Nexus-Product` when set. "
            "`generic` defaults to direct BYOK (no docs KB required)."
        ),
        examples=["mosip"],
    )
    answer_mode: str | None = Field(
        None,
        description=(
            "`rag` — retrieve from product collections then answer. "
            "`direct` — call the BYOK LLM only (no vector search). "
            "When omitted, uses the product default (`generic` → `direct`)."
        ),
        examples=["direct"],
    )
    system_prompt: str | None = Field(
        None,
        description=(
            "Optional system prompt for `answer_mode=direct` (white-label apps). "
            "Ignored for RAG mode."
        ),
        examples=["You are a helpful career coach. Be concise."],
    )


class TokenUsage(BaseModel):
    """LLM token counters for one chat turn (prompt + completion)."""

    prompt_tokens: int = Field(
        0,
        ge=0,
        description="Input / prompt tokens for this query (all LLM calls in the turn).",
        examples=[1840],
    )
    completion_tokens: int = Field(
        0,
        ge=0,
        description="Output / completion tokens for this query.",
        examples=[312],
    )
    total_tokens: int = Field(
        0,
        ge=0,
        description="prompt_tokens + completion_tokens (provider total when available).",
        examples=[2152],
    )


class ChatResponse(BaseModel):
    """Successful RAG answer from ``POST /chat`` (also nested in `/batch`)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answer": (
                        "**IDA-MLC-009** indicates a missing or invalid UIN/VID in the "
                        "authentication request.\n\n"
                        "1. Verify the UIN/VID is enrolled and active.\n"
                        "2. Check that the partner is authorised for the auth type.\n"
                        "3. Retry with a fresh challenge from IDA."
                    ),
                    "sources": [
                        {
                            "source": "https://docs.mosip.io/1.2.0/id-authentication/error-codes",
                            "title": "IDA Error Codes",
                            "source_type": "docs",
                            "tags": "",
                            "accepted": False,
                        },
                        {
                            "source": "https://community.mosip.io/t/ida-mlc-009-help/1234",
                            "title": "IDA-MLC-009 help thread",
                            "source_type": "community",
                            "tags": "ida,errors",
                            "accepted": True,
                        },
                    ],
                    "source_type": "mixed",
                    "confidence": "high",
                    "similar_questions": [
                        "How to resolve IDA-MLC-002?",
                        "UIN not found during authentication",
                    ],
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "token_usage": {
                        "prompt_tokens": 1840,
                        "completion_tokens": 312,
                        "total_tokens": 2152,
                    },
                }
            ]
        }
    )

    answer: str = Field(
        ...,
        description="Markdown-formatted answer grounded in retrieved context (or web/fallback).",
    )
    sources: list[SourceItem] = Field(
        ...,
        description="Deduplicated citations used (or related) to the answer.",
    )
    source_type: str = Field(
        ...,
        description=(
            "Dominant origin label: `docs`, `community`, `github`, `code`, `mixed`, "
            "`web`, `none`, `chat`, or `n/a`."
        ),
        examples=["mixed"],
    )
    confidence: str = Field(
        ...,
        description="Retriever confidence: `high` | `medium` | `low` | `n/a`.",
        examples=["high"],
    )
    similar_questions: list[str] = Field(
        ...,
        description="Related community-style questions suggested by the pipeline.",
        examples=[["How to resolve IDA-MLC-002?"]],
    )
    session_id: str = Field(
        ...,
        description="Session UUID — pass back on the next `/chat` call to keep context.",
        examples=["a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11"],
    )
    token_usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description=(
            "LLM tokens consumed for this query (condense + answer + any web synthesis). "
            "Zeros when no LLM call ran (e.g. meta answer)."
        ),
    )
    turn: int | None = Field(
        default=None,
        description="1-based turn number for this Q&A — pass to `POST /feedback` to rate it.",
        examples=[1],
    )
    cached: bool = Field(
        default=False,
        description=(
            "True when this answer was served from the system-level answer cache "
            "(a near-duplicate question was already answered with high confidence) "
            "instead of a fresh LLM call — `token_usage` will be all zeros."
        ),
    )


class BatchRequest(BaseModel):
    """Body for ``POST /batch`` — up to 10 sequential questions in one session."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "questions": [
                        "What is ID Authentication (IDA)?",
                        "Which error code means invalid OTP?",
                    ],
                    "session_id": None,
                    "language": "English",
                    "llm_provider": "openai",
                    "llm_api_key": "sk-proj-xxxxxxxx",
                    "llm_model": "gpt-4o-mini",
                }
            ]
        }
    )

    questions: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Ordered list of questions (max 10). Later items see prior answers.",
        examples=[["What is ID Authentication (IDA)?", "Which error code means invalid OTP?"]],
    )
    session_id: str | None = Field(
        None,
        description="Optional existing session UUID; created if omitted.",
    )
    language: str = Field("English", description="Answer language for all questions.")
    llm_provider: str = Field(
        "groq",
        description="`groq` | `anthropic` | `openai` | `xai` | `grok`.",
    )
    llm_api_key: str | None = Field(None, description="Required BYOK API key.")
    llm_model: str | None = Field(None, description="Optional model override.")
    product: str | None = Field(
        None,
        description="Optional product slug (`mosip` | `inji` | `generic`).",
    )
    answer_mode: str | None = Field(
        None,
        description="`rag` | `direct`. Omitting uses the product default.",
    )
    system_prompt: str | None = Field(
        None,
        description="Optional system prompt for direct mode.",
    )


class BatchResponse(BaseModel):
    """Results of ``POST /batch``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "total": 2,
                    "results": [
                        {
                            "answer": "IDA is the MOSIP module that authenticates residents…",
                            "sources": [],
                            "source_type": "docs",
                            "confidence": "high",
                            "similar_questions": [],
                            "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                        }
                    ],
                }
            ]
        }
    )

    session_id: str = Field(..., description="Shared session UUID for all answers.")
    total: int = Field(..., description="Number of answers in `results`.", examples=[2], ge=0)
    results: list[ChatResponse] = Field(..., description="One `ChatResponse` per input question, in order.")


# ── Search ─────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    """Body for ``POST /search`` — vector retrieval without LLM."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "packet manager status codes",
                    "k": 5,
                }
            ]
        }
    )

    query: str = Field(
        ...,
        min_length=1,
        description="Free-text search query over all indexed collections.",
        examples=["packet manager status codes"],
    )
    k: int = Field(
        5,
        ge=1,
        le=20,
        description="Max chunks to return after merge (1–20).",
        examples=[5],
    )


class SearchResult(BaseModel):
    """Single retrieved chunk (content truncated to 500 characters)."""

    content: str = Field(..., description="Chunk text (may be truncated).")
    source: str = Field(..., description="Source URL or path.")
    title: str = Field(..., description="Source title.")
    source_type: str = Field(..., description="`docs` | `community` | `github` | `code` | …")


class SearchResponse(BaseModel):
    """Payload for ``POST /search``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "packet manager status codes",
                    "total": 2,
                    "results": [
                        {
                            "content": "PacketManagerErrorCodes defines STATUS_…",
                            "source": "https://github.com/mosip/commons/blob/master/…/PacketManagerErrorCodes.java",
                            "title": "PacketManagerErrorCodes.java",
                            "source_type": "code",
                        },
                        {
                            "content": "Registration packet statuses are documented in…",
                            "source": "https://docs.mosip.io/1.2.0/registration/…",
                            "title": "Registration packet status",
                            "source_type": "docs",
                        },
                    ],
                }
            ]
        }
    )

    query: str = Field(..., description="Echo of the search query.")
    total: int = Field(..., description="Number of results returned.", ge=0)
    results: list[SearchResult] = Field(..., description="Ranked chunk snippets.")


class SimilarRequest(BaseModel):
    """Body for ``POST /similar`` — community near-duplicate check."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"question": "How do I configure ABIS host URL in MOSIP?"}
            ]
        }
    )

    question: str = Field(
        ...,
        min_length=1,
        description="Question to match against community question chunks.",
        examples=["How do I configure ABIS host URL in MOSIP?"],
    )


class SimilarResponse(BaseModel):
    """Result of community similarity search."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "found": True,
                    "title": "ABIS host configuration in application properties",
                    "source": "https://community.mosip.io/t/abis-host-url/5678",
                    "similarity_score": 0.91,
                    "message": "A similar community thread was found.",
                },
                {
                    "found": False,
                    "title": "",
                    "source": "",
                    "similarity_score": 0.0,
                    "message": "No similar community thread found.",
                },
            ]
        }
    )

    found: bool = Field(..., description="True when a thread exceeds `DEDUP_THRESHOLD`.")
    title: str = Field("", description="Matching thread title when `found` is true.")
    source: str = Field("", description="URL of the matching thread.")
    similarity_score: float = Field(
        0.0,
        description="Relevance score in [0, 1] (higher is closer).",
        examples=[0.91],
        ge=0.0,
        le=1.0,
    )
    message: str = Field("", description="Short human-readable outcome.")


# ── Sessions ───────────────────────────────────────────────────────────────────

class CreateSessionResponse(BaseModel):
    """Payload for ``POST /session``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "status": "created",
                }
            ]
        }
    )

    session_id: str = Field(..., description="New session UUID.")
    status: str = Field(..., description="Always `created` on success.", examples=["created"])


class HistoryMessage(BaseModel):
    """One message in session history."""

    role: str = Field(
        ...,
        description="`user` for questions, `assistant` for answers.",
        examples=["user"],
    )
    content: str = Field(..., description="Message text (markdown for assistant).")


class SessionHistoryResponse(BaseModel):
    """Payload for ``GET /session/{id}/history``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "language": "English",
                    "turns": 1,
                    "messages": [
                        {"role": "user", "content": "What does IDA-MLC-009 mean?"},
                        {
                            "role": "assistant",
                            "content": "**IDA-MLC-009** indicates a missing or invalid UIN/VID…",
                        },
                    ],
                }
            ]
        }
    )

    session_id: str = Field(..., description="Session UUID.")
    language: str = Field(..., description="Last recorded session language.")
    turns: int = Field(..., description="Number of Q&A pairs.", ge=0)
    messages: list[HistoryMessage] = Field(
        ...,
        description="Alternating user/assistant messages in chronological order.",
    )


class SessionSummary(BaseModel):
    """One row in ``GET /sessions``."""

    session_id: str = Field(..., description="Session UUID.")
    turns: int = Field(..., description="Number of completed Q&A turns.", ge=0)
    language: str = Field(..., description="Session language name.")


class SessionsResponse(BaseModel):
    """Payload for ``GET /sessions``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "active_sessions": 2,
                    "sessions": [
                        {
                            "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                            "turns": 3,
                            "language": "English",
                        },
                        {
                            "session_id": "b7e2d9f1-1111-2222-3333-444455556666",
                            "turns": 1,
                            "language": "Tamil",
                        },
                    ],
                }
            ]
        }
    )

    active_sessions: int = Field(..., description="Count of non-cleared sessions.", ge=0)
    sessions: list[SessionSummary] = Field(..., description="Active sessions (newest access first).")


class SessionDeleteResponse(BaseModel):
    """Payload for ``DELETE /session/{id}``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "status": "cleared",
                }
            ]
        }
    )

    session_id: str = Field(..., description="Cleared session UUID.")
    status: str = Field(..., description="Always `cleared` on success.", examples=["cleared"])


class SessionExportJson(BaseModel):
    """JSON shape for ``POST /export/{id}?format=json``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "language": "English",
                    "total_turns": 1,
                    "turns": [
                        {
                            "turn": 1,
                            "question": "What does IDA-MLC-009 mean?",
                            "answer": "**IDA-MLC-009** indicates…",
                            "sources": [
                                {
                                    "source": "https://docs.mosip.io/1.2.0/id-authentication/error-codes",
                                    "title": "IDA Error Codes",
                                    "source_type": "docs",
                                }
                            ],
                            "source_type": "docs",
                            "confidence": "high",
                            "similar_questions": [],
                            "language": "English",
                        }
                    ],
                }
            ]
        }
    )

    session_id: str
    language: str
    total_turns: int
    turns: list[dict[str, Any]]


class ExportFormat(str, Enum):
    """Export format query parameter for ``POST /export/{session_id}``."""

    json = "json"
    html = "html"


# ── Feedback & stats ───────────────────────────────────────────────────────────

class FeedbackRating(str, Enum):
    """Allowed values for answer feedback."""

    positive = "positive"
    negative = "negative"


class FeedbackRequest(BaseModel):
    """Body for ``POST /feedback``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                    "turn": 1,
                    "rating": "positive",
                    "comment": "Clear explanation with the right error code.",
                }
            ]
        }
    )

    session_id: str = Field(
        ...,
        description="Session that contains the rated turn.",
        examples=["a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11"],
    )
    turn: int = Field(
        ...,
        ge=1,
        description="1-based turn number (1 = first Q&A in the session).",
        examples=[1],
    )
    rating: FeedbackRating = Field(
        ...,
        description="`positive` if the answer helped; `negative` otherwise.",
    )
    comment: str = Field(
        "",
        description="Optional free-text comment stored with the rating.",
        examples=["Clear explanation with the right error code."],
    )


class FeedbackResponse(BaseModel):
    """Payload for ``POST /feedback``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "recorded",
                    "feedback_id": "c0ffee00-1111-2222-3333-444455556666",
                }
            ]
        }
    )

    status: str = Field(..., description="Always `recorded` on success.", examples=["recorded"])
    feedback_id: str = Field(..., description="UUID of the stored feedback row.")


class StatsResponse(BaseModel):
    """Payload for ``GET /stats``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total_queries": 1540,
                    "active_sessions": 18,
                    "total_feedback": 220,
                    "positive_feedback": 180,
                    "negative_feedback": 40,
                    "avg_sources_per_query": 3.42,
                    "confidence_distribution": {"high": 900, "medium": 480, "low": 160},
                    "source_type_distribution": {
                        "docs": 620,
                        "mixed": 410,
                        "community": 300,
                        "code": 140,
                        "web": 50,
                        "none": 20,
                    },
                    "language_distribution": {"English": 1200, "Tamil": 200, "Hindi": 140},
                }
            ]
        }
    )

    total_queries: int = Field(..., description="Rows in `query_events`.", ge=0)
    active_sessions: int = Field(..., description="Non-cleared chat sessions.", ge=0)
    total_feedback: int = Field(..., description="Total feedback rows.", ge=0)
    positive_feedback: int = Field(..., description="Count of positive ratings.", ge=0)
    negative_feedback: int = Field(..., description="Count of negative ratings.", ge=0)
    avg_sources_per_query: float = Field(
        ...,
        description="Mean `source_count` across query events (0 if none).",
        examples=[3.42],
    )
    confidence_distribution: dict[str, int] = Field(
        ...,
        description="Map of confidence label → count.",
    )
    source_type_distribution: dict[str, int] = Field(
        ...,
        description="Map of source_type label → count.",
    )
    language_distribution: dict[str, int] = Field(
        ...,
        description="Map of language name → count.",
    )


# ── Notifications ──────────────────────────────────────────────────────────────

class ExpertNotifyRequest(BaseModel):
    """Body for ``POST /notify/expert``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "Our Synergy env fails ABIS callback but local works — why?",
                    "language": "English",
                    "user_email": "engineer@example.gov",
                    "context": "Low-confidence answer suggested checking firewall rules…",
                    "unanswered": False,
                },
                {
                    "question": "Is there a public API for credential status lists?",
                    "language": "English",
                    "user_email": "partner@example.com",
                    "context": "",
                    "unanswered": True,
                },
            ]
        }
    )

    question: str = Field(
        ...,
        min_length=1,
        description="User question to escalate to the product team.",
    )
    language: str = Field("English", description="Language of the conversation.")
    user_email: str = Field(
        ...,
        min_length=3,
        description="Reply-to address so an expert can contact the user.",
        examples=["engineer@example.gov"],
    )
    context: str = Field(
        "",
        description="Optional snippet of the AI answer or extra debugging notes.",
    )
    unanswered: bool = Field(
        False,
        description=(
            "True when the knowledge base returned no answer (`source_type=none`); "
            "selects the unanswered email template."
        ),
    )


class NotifyResponse(BaseModel):
    """Payload for ``POST /notify/expert`` (queued immediately)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"ok": True, "message": "Notification queued."}
            ]
        }
    )

    ok: bool = Field(..., description="True when the notification was accepted for background send.")
    message: str = Field(..., description="Human-readable queue status.")

"""
MOSIP Nexus REST API

Exposes the full RAG pipeline as HTTP endpoints with Swagger UI.

Layering: routes validate request models and map HTTP errors; business logic
lives in ``controllers.*`` (chat, sessions, feedback, stats). Heavy endpoints
(``/chat``, ``/batch``, ``/search``) take an in-process slot via
``MAX_CONCURRENT_CHATS`` and return **503** when saturated.

Chat LLM keys are **BYOK** — callers must pass ``llm_api_key``. The server
does not fall back to ``GROQ_API_KEY`` for interactive chat.

Run:
    uv run uvicorn api.main:app --host 0.0.0.0 --port 8000

Swagger UI → http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import sys
import threading
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import BackgroundTasks, FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator

from api.errors import (
    CapacityError,
    UpstreamError,
    register_exception_handlers,
)
from api.middleware import ProductModeMiddleware, RequestLoggingMiddleware
from config.products import set_current_product
from api.schemas import (
    BatchRequest,
    BatchResponse,
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    CreateSessionResponse,
    ExpertNotifyRequest,
    ExportFormat,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    HistoryMessage,
    NotifyResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SessionDeleteResponse,
    SessionHistoryResponse,
    SessionSummary,
    SessionsResponse,
    SimilarRequest,
    SimilarResponse,
    SourceItem,
    StatsResponse,
    TokenUsage,
)
from config.settings import (
    MAX_CONCURRENT_CHATS,
    PRODUCT_NAME,
    PRODUCT_SHORT,
    public_config,
)
from config.logging_config import setup_logging
from controllers import chat as chat_ctrl
from controllers import feedback as feedback_ctrl
from controllers import sessions as sessions_ctrl
from controllers import stats as stats_ctrl
from notifications.email_notifier import (
    send_expert_request_notification,
    send_unanswered_notification,
)
from retrieval.dedup import find_similar_question
from retrieval.retriever import ensure_ready, get_collection_counts, retrieve, warmup as retriever_warmup

logger = logging.getLogger("nexus.api")

_chat_semaphore = threading.Semaphore(max(1, MAX_CONCURRENT_CHATS))

_OPENAPI_TAGS = [
    {
        "name": "System",
        "description": (
            "Public configuration and health. Safe for browsers and load balancers — "
            "no secrets in `/config`."
        ),
    },
    {
        "name": "Chat",
        "description": (
            "RAG Q&A. Requires a **bring-your-own** LLM API key (`llm_api_key`). "
            "Pass `session_id` to continue a conversation. May return **503** under load."
        ),
    },
    {
        "name": "Search",
        "description": (
            "Retrieval-only endpoints (no LLM). Use `/search` for chunk exploration and "
            "`/similar` to detect duplicate community questions."
        ),
    },
    {
        "name": "Session",
        "description": (
            "Postgres-backed chat sessions: create, list, history, soft-delete, and export."
        ),
    },
    {
        "name": "Feedback",
        "description": "Thumbs-up / thumbs-down ratings on individual answer turns.",
    },
    {
        "name": "Analytics",
        "description": "Aggregated usage from `query_events` and feedback tables.",
    },
    {
        "name": "Notifications",
        "description": (
            "Queue SMTP emails to `NOTIFY_EMAIL` (expert escalation or unanswered). "
            "Requires SMTP env configuration."
        ),
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Configure logging and warm the embedding model / pgvector stores."""
    setup_logging()
    logger.info(
        "Starting %s API (max_concurrent_chats=%s)",
        PRODUCT_NAME,
        MAX_CONCURRENT_CHATS,
    )
    try:
        retriever_warmup()
    except Exception:
        logger.exception("Retriever warmup failed — first request will retry lazily")
    yield
    logger.info("Shutting down %s API", PRODUCT_NAME)


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=f"{PRODUCT_NAME} API",
    description=(
        f"# {PRODUCT_NAME}\n\n"
        f"AI-powered **{PRODUCT_SHORT}** knowledge assistant. Search official docs, "
        "community forum, GitHub issues, Confluence, Jira, and source code via REST.\n\n"
        "## Authentication / LLM keys\n\n"
        "Interactive chat (`POST /chat`, `POST /batch`) is **BYOK** — send "
        "`llm_api_key` for Groq, Anthropic, or OpenAI. Keys are never stored.\n\n"
        "## Sessions\n\n"
        "Conversation history is persisted in Postgres. Create a session with "
        "`POST /session` or omit `session_id` on the first `/chat` call.\n\n"
        "## Local URLs\n\n"
        "| Surface | URL |\n"
        "| --- | --- |\n"
        "| API (compose host) | `http://localhost:8010` |\n"
        "| Swagger UI | `/docs` |\n"
        "| ReDoc | `/redoc` |\n"
        "| OpenAPI JSON | `/openapi.json` |\n\n"
        "See also `docs/API_REFERENCE.md` in the repository."
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=_OPENAPI_TAGS,
    contact={
        "name": f"{PRODUCT_SHORT} Nexus",
        "url": "https://docs.mosip.io",
    },
    license_info={
        "name": "See repository LICENSE",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ProductModeMiddleware)

register_exception_handlers(app)

# Expose /metrics for Prometheus scraping (Rancher monitoring stack).
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


def custom_openapi():
    """Attach richer OpenAPI metadata once (cached on the app)."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=_OPENAPI_TAGS,
        contact=app.contact,
        license_info=app.license_info,
    )
    schema["info"]["x-logo"] = {"altText": PRODUCT_NAME}
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@contextmanager
def _chat_slot() -> Iterator[None]:
    """Acquire a non-blocking chat concurrency slot or raise CapacityError."""
    acquired = _chat_semaphore.acquire(blocking=False)
    if not acquired:
        logger.warning(
            "Chat capacity exceeded (MAX_CONCURRENT_CHATS=%s)",
            MAX_CONCURRENT_CHATS,
        )
        raise CapacityError()
    try:
        yield
    finally:
        _chat_semaphore.release()


def _token_usage(raw: Any) -> TokenUsage:
    """Coerce ask()/controller token_usage dict into TokenUsage."""
    if not isinstance(raw, dict):
        return TokenUsage()
    return TokenUsage(
        prompt_tokens=int(raw.get("prompt_tokens") or 0),
        completion_tokens=int(raw.get("completion_tokens") or 0),
        total_tokens=int(raw.get("total_tokens") or 0),
    )


def _source_items(sources: list) -> list[SourceItem]:
    items: list[SourceItem] = []
    for s in sources or []:
        items.append(SourceItem(
            source=s.get("source", "") or "",
            title=s.get("title", "") or "",
            source_type=s.get("source_type", "") or "",
            tags=s.get("tags", "") or "",
            accepted=bool(s.get("accepted", False)),
        ))
    return items


# ── /config ────────────────────────────────────────────────────────────────────
@app.get(
    "/config",
    response_model=ConfigResponse,
    tags=["System"],
    summary="Public product config for UI",
    description=(
        "Returns product name, docs/community URLs, and GitHub org for the React UI "
        "and other clients. **Safe for browsers** — no secrets, DSNs, or API keys. "
        "Values come from `PRODUCT_*` / crawl URL environment variables."
    ),
    responses={
        200: {
            "description": "Public branding payload.",
            "content": {
                "application/json": {
                    "example": {
                        "product_name": "MOSIP Nexus",
                        "product_short": "MOSIP",
                        "product_slug": "mosip",
                        "docs_base_url": "https://docs.mosip.io/1.2.0",
                        "community_base_url": "https://community.mosip.io",
                        "community_new_topic_url": "https://community.mosip.io/new-topic",
                        "github_org": "mosip",
                    }
                }
            },
        }
    },
)
def get_config(
    product: str | None = Query(
        None,
        description="Optional product slug (`mosip` | `inji`). Defaults to `X-Nexus-Product` / server default.",
    ),
) -> ConfigResponse:
    """Return public branding and knowledge-base URLs (plus full product catalog)."""
    if product:
        set_current_product(product)
    return ConfigResponse(**public_config(product))


# ── /chat ──────────────────────────────────────────────────────────────────────
@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary=f"Ask a {PRODUCT_SHORT} question",
    description=(
        "Main RAG endpoint:\n\n"
        "1. Optionally condense follow-ups using session history\n"
        "2. Embed once and search pgvector collections in parallel\n"
        "3. Generate a grounded answer with the caller's LLM key (BYOK)\n\n"
        "Pass `session_id` from a prior response to keep context. "
        "Optionally queues an SMTP alert when confidence is low and "
        "`notify_on_low_confidence` is true.\n\n"
        "**Errors:** `400` missing/invalid key or session id · "
        "`503` when `MAX_CONCURRENT_CHATS` is saturated (`Retry-After: 2`)."
    ),
    responses={
        400: {
            "description": "Missing `llm_api_key`, invalid key, or bad `session_id`.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "LLM_KEY_REQUIRED",
                            "message": (
                                "llm_api_key is required. Provide your own Groq, Anthropic, "
                                "or OpenAI API key. No server-side LLM key is available."
                            ),
                            "details": None,
                            "request_id": "00000000-0000-0000-0000-000000000001",
                        }
                    }
                }
            },
        },
        502: {
            "description": "LLM / upstream provider failure.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "UPSTREAM_ERROR",
                            "message": "The language model failed to generate an answer. Please try again.",
                            "details": None,
                            "request_id": "00000000-0000-0000-0000-000000000001",
                        }
                    }
                }
            },
        },
        503: {
            "description": "Too many parallel chats (`CAPACITY_EXCEEDED`).",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "CAPACITY_EXCEEDED",
                            "message": (
                                "Server is at capacity (too many parallel chats). "
                                "Retry shortly, or raise MAX_CONCURRENT_CHATS."
                            ),
                            "details": {"retry_after": 2},
                            "request_id": "00000000-0000-0000-0000-000000000001",
                        }
                    }
                }
            },
        },
    },
)
def chat(req: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
    """Run one RAG turn and persist the Q&A to the session."""
    if req.product:
        set_current_product(req.product)
    with _chat_slot():
        result, should_notify = chat_ctrl.run_chat_turn(
            question=req.question,
            session_id=req.session_id,
            language=req.language,
            llm_provider=req.llm_provider,
            llm_api_key=req.llm_api_key,
            llm_model=req.llm_model,
            notify_on_low_confidence=req.notify_on_low_confidence,
            answer_mode=req.answer_mode,
            system_prompt=req.system_prompt,
        )
        if should_notify:
            chat_ctrl.queue_low_confidence_notify(
                background_tasks.add_task,
                question=req.question,
                language=req.language,
                source_type=result.get("source_type", ""),
            )
        return ChatResponse(
            answer=result["answer"],
            sources=_source_items(result.get("sources", [])),
            source_type=result["source_type"],
            confidence=result["confidence"],
            similar_questions=result.get("similar_questions", []),
            session_id=result["session_id"],
            token_usage=_token_usage(result.get("token_usage")),
        )


# ── /notify ────────────────────────────────────────────────────────────────────
@app.post("/notify/expert", response_model=NotifyResponse, tags=["Notifications"],
          summary="Request an expert response",
          description=(
              "Queues an email to `NOTIFY_EMAIL` via SMTP. Set `unanswered=true` "
              "when the knowledge base returned no answer (`source_type=none`); "
              "otherwise sends an expert-escalation template. Always returns "
              "queued=ok immediately; SMTP errors are logged in the background."
          ))
def notify_expert(req: ExpertNotifyRequest, background_tasks: BackgroundTasks) -> NotifyResponse:
    """Queue unanswered or expert-request email notification."""
    def _send() -> None:
        try:
            if req.unanswered:
                send_unanswered_notification(
                    question=req.question,
                    language=req.language,
                    user_email=req.user_email,
                )
            else:
                send_expert_request_notification(
                    question=req.question,
                    language=req.language,
                    user_email=req.user_email,
                    context=req.context,
                )
        except Exception:
            logger.exception("Expert notification failed")

    background_tasks.add_task(_send)
    return NotifyResponse(ok=True, message="Notification queued.")


# ── /session (create) ─────────────────────────────────────────────────────────
@app.post("/session", response_model=CreateSessionResponse, tags=["Session"],
          summary="Create a new session",
          description=(
              "Creates a new empty Postgres-backed session and returns its UUID. "
              "Pass this `session_id` to `/chat` and `/batch` to maintain history."
          ))
def create_session() -> CreateSessionResponse:
    """Create and return a new chat session id."""
    session_id = sessions_ctrl.create_session()
    return CreateSessionResponse(session_id=session_id, status="created")


# ── /session/{id}/history ──────────────────────────────────────────────────────
@app.get("/session/{session_id}/history", response_model=SessionHistoryResponse, tags=["Session"],
         summary="Get conversation history",
         description=(
             "Returns the full Q&A history for an active session as alternating "
             "`user` / `assistant` messages. **404** if missing or cleared."
         ))
def session_history(session_id: str) -> SessionHistoryResponse:
    """Load persisted turns for a session."""
    data = sessions_ctrl.get_history(session_id)
    return SessionHistoryResponse(
        session_id=data["session_id"],
        language=data["language"],
        turns=data["turns"],
        messages=[HistoryMessage(**m) for m in data["messages"]],
    )


# ── /sessions ──────────────────────────────────────────────────────────────────
@app.get("/sessions", response_model=SessionsResponse, tags=["Session"],
         summary="List all active sessions",
         description=(
             "Returns currently active (non-cleared) sessions with turn count and "
             "language after idle purge. Useful for ops/debug, not for end users."
         ))
def list_sessions() -> SessionsResponse:
    """List active sessions after idle purge."""
    data = sessions_ctrl.list_sessions()
    return SessionsResponse(
        active_sessions=data["active_sessions"],
        sessions=[SessionSummary(**s) for s in data["sessions"]],
    )


# ── /session/{id} DELETE ───────────────────────────────────────────────────────
@app.delete("/session/{session_id}", response_model=SessionDeleteResponse, tags=["Session"],
            summary="Clear a session",
            description=(
                "Soft-clears chat history for the session (sets `cleared_at`, "
                "deletes turns). Equivalent to clicking 'New Chat' in the UI."
            ))
def delete_session(session_id: str) -> SessionDeleteResponse:
    """Soft-clear a session's conversation history."""
    sessions_ctrl.delete_session(session_id)
    return SessionDeleteResponse(session_id=session_id, status="cleared")


# ── /search ────────────────────────────────────────────────────────────────────
@app.post("/search", response_model=SearchResponse, tags=["Search"],
          summary="Raw vector search",
          description=(
              "Retrieves matching chunks from pgvector without calling the LLM. "
              "Uses the same hybrid retriever as `/chat`. Content snippets are "
              "truncated to 500 characters. Subject to the chat concurrency slot."
          ))
def search(req: SearchRequest) -> SearchResponse:
    """Vector search across all indexed collections (no LLM)."""
    with _chat_slot():
        try:
            docs, _ = retrieve(req.query, k=req.k)
        except Exception as e:
            logger.exception("Error in /search for query: %s", req.query)
            raise UpstreamError(
                "Search failed. The knowledge index may be unavailable. Please try again.",
                details={"error": str(e)[:300]},
            ) from e

        results = [
            SearchResult(
                content=d.page_content[:500],
                source=d.metadata.get("source", ""),
                title=d.metadata.get("title", ""),
                source_type=d.metadata.get("source_type", ""),
            )
            for d in docs
        ]
        return SearchResponse(query=req.query, total=len(results), results=results)


# ── /similar ───────────────────────────────────────────────────────────────────
@app.post("/similar", response_model=SimilarResponse, tags=["Search"],
          summary="Find similar community threads",
          description=(
              "Checks the community forum index for an existing question-type "
              "thread whose similarity exceeds `DEDUP_THRESHOLD`. No LLM is "
              "called — use before posting a new community topic."
          ))
def similar(req: SimilarRequest) -> SimilarResponse:
    """Near-duplicate check against community question chunks."""
    try:
        result = find_similar_question(req.question)
    except Exception as e:
        logger.exception("Error in /similar")
        raise UpstreamError(
            "Similar-thread lookup failed. Please try again.",
            details={"error": str(e)[:300]},
        ) from e

    if result:
        return SimilarResponse(
            found=True,
            title=result.get("title", ""),
            source=result.get("source", ""),
            similarity_score=round(result.get("similarity_score", 0.0), 4),
            message="A similar community thread was found.",
        )
    return SimilarResponse(found=False, message="No similar community thread found.")


# ── /feedback ──────────────────────────────────────────────────────────────────
@app.post("/feedback", response_model=FeedbackResponse, tags=["Feedback"],
          summary="Submit answer feedback",
          description=(
              "Rate a specific turn (`turn` is 1-based) as positive or negative. "
              "Optional free-text `comment`. **404** if session or turn missing."
          ))
def feedback(req: FeedbackRequest) -> FeedbackResponse:
    """Record thumbs-up/down feedback for a session turn."""
    feedback_id = feedback_ctrl.record_feedback(
        session_id=req.session_id,
        turn=req.turn,
        rating=req.rating.value,
        comment=req.comment,
    )
    return FeedbackResponse(status="recorded", feedback_id=feedback_id)


# ── /stats ─────────────────────────────────────────────────────────────────────
@app.get("/stats", response_model=StatsResponse, tags=["Analytics"],
         summary="Usage statistics",
         description=(
             "Aggregated usage from `query_events` plus live session and feedback "
             "counts — confidence, source-type, and language distributions for "
             "stakeholder reporting."
         ))
def stats() -> StatsResponse:
    """Return aggregated usage metrics."""
    return StatsResponse(**stats_ctrl.get_dashboard_stats())


# ── /export/{session_id} ───────────────────────────────────────────────────────
@app.post(
    "/export/{session_id}",
    tags=["Session"],
    summary="Export a session",
    description=(
        "Export the full conversation as **JSON** (structured turns + sources) or "
        "**HTML** (styled downloadable report, same idea as Export Chat in the UI).\n\n"
        "Query parameter `format`: `json` (default) or `html`."
    ),
    responses={
        200: {
            "description": "JSON object or HTML attachment.",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "a3f1c8e2-4b5d-4e9a-9c1f-2d7e8a6b0c11",
                        "language": "English",
                        "total_turns": 1,
                        "turns": [
                            {
                                "turn": 1,
                                "question": "What does IDA-MLC-009 mean?",
                                "answer": "**IDA-MLC-009** indicates…",
                                "sources": [],
                                "source_type": "docs",
                                "confidence": "high",
                                "similar_questions": [],
                                "language": "English",
                            }
                        ],
                    }
                }
            },
        },
        404: {
            "description": "Session not found or cleared.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "SESSION_NOT_FOUND",
                            "message": "Session '…' not found.",
                            "details": None,
                            "request_id": "00000000-0000-0000-0000-000000000001",
                        }
                    }
                }
            },
        },
    },
)
def export_session(
    session_id: str,
    format: ExportFormat = Query(
        ExportFormat.json,
        description="Export format: `json` for structured data, `html` for a downloadable report.",
    ),
):
    """Export a session as JSON object or downloadable HTML."""
    if format == ExportFormat.json:
        return sessions_ctrl.export_session(session_id)

    html, filename = sessions_ctrl.export_session_html(session_id)
    return HTMLResponse(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── /batch ─────────────────────────────────────────────────────────────────────
@app.post("/batch", response_model=BatchResponse, tags=["Chat"],
          summary="Ask multiple questions at once",
          description=(
              "Process up to 10 questions sequentially in one request. Each "
              "question sees prior answers in the shared session (computed first, "
              "then committed). Requires BYOK `llm_api_key`. Subject to the chat "
              "concurrency slot."
          ))
def batch(req: BatchRequest) -> BatchResponse:
    """Answer multiple questions in one shared session."""
    if req.product:
        set_current_product(req.product)
    with _chat_slot():
        session_id, payloads = chat_ctrl.run_batch(
            questions=req.questions,
            session_id=req.session_id,
            language=req.language,
            llm_provider=req.llm_provider,
            llm_api_key=req.llm_api_key,
            llm_model=req.llm_model,
            answer_mode=req.answer_mode,
            system_prompt=req.system_prompt,
        )
        responses = [
            ChatResponse(
                answer=r["answer"],
                sources=_source_items(r.get("sources", [])),
                source_type=r["source_type"],
                confidence=r["confidence"],
                similar_questions=r.get("similar_questions", []),
                session_id=session_id,
                token_usage=_token_usage(r.get("token_usage")),
            )
            for r in payloads
        ]
        return BatchResponse(session_id=session_id, total=len(responses), results=responses)


# ── /health ────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"],
         summary="System health check",
         description=(
             "Returns pgvector collection chunk counts (non-empty only) and "
             "active session count. Responds with **503** and `status=degraded` "
             "if the database or embedder cannot be reached."
         ))
def health(response: Response) -> HealthResponse:
    """Liveness/readiness-style check for collections and sessions."""
    try:
        ensure_ready()
        collections: dict[str, Any] = get_collection_counts()
        active = sessions_ctrl.count_active()
    except Exception:
        logger.exception("Error reading pgvector collection counts in /health")
        response.status_code = 503
        return HealthResponse(
            status="degraded",
            collections={"error": "Unable to read collection stats."},
            active_sessions=0,
        )
    return HealthResponse(
        status="ok",
        collections=collections,
        active_sessions=active,
    )

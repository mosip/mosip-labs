"""
MOSIP Nexus REST API

Exposes the full RAG pipeline as HTTP endpoints with Swagger UI.

Run:
    uv run uvicorn MosipNexus.api.main:app --host 0.0.0.0 --port 8000 --reload

Swagger UI → http://localhost:8000/docs
"""

from __future__ import annotations

import html as _html
import logging
import sys
import uuid
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from langchain_core.messages import AIMessage, HumanMessage

from chain.query_engine import ask
from memory.session import SessionMemory
from retrieval.dedup import find_similar_question
from retrieval.retriever import retrieve
import retrieval.retriever as _retriever

logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MOSIP Nexus API",
    description=(
        "AI-powered MOSIP Knowledge Assistant — search official docs, community forum, "
        "GitHub issues, Confluence, and source code via REST.\n\n"
        "**Base URL:** `http://localhost:8000`\n\n"
        "**Swagger UI:** `/docs` &nbsp;|&nbsp; **ReDoc:** `/redoc`"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory stores ───────────────────────────────────────────────────────────
_sessions: dict[str, SessionMemory] = {}
_session_turns: dict[str, list[dict]] = {}   # session_id → list of full turn dicts
_feedback: list[dict] = []
_stats: dict[str, Any] = {
    "total_queries": 0,
    "confidence": defaultdict(int),
    "source_type": defaultdict(int),
    "language": defaultdict(int),
    "total_sources": 0,
}


def _get_session(session_id: str) -> SessionMemory:
    if session_id not in _sessions:
        _sessions[session_id] = SessionMemory()
        _session_turns[session_id] = []
    return _sessions[session_id]


def _record_stats(result: dict, language: str) -> None:
    _stats["total_queries"] += 1
    _stats["confidence"][result.get("confidence", "unknown")] += 1
    _stats["source_type"][result.get("source_type", "unknown")] += 1
    _stats["language"][language] += 1
    _stats["total_sources"] += len(result.get("sources", []))


# ── Shared models ──────────────────────────────────────────────────────────────
class SourceItem(BaseModel):
    source: str = ""
    title: str = ""
    source_type: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    source_type: str
    confidence: str
    similar_questions: list[str]
    session_id: str


# ── /chat ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to ask about MOSIP.")
    session_id: str | None = Field(None, description="Pass previous session_id to continue conversation.")
    language: str = Field("English", description="Response language e.g. English, Tamil, Hindi.")


@app.post("/chat", response_model=ChatResponse, tags=["Chat"],
          summary="Ask a MOSIP question",
          description="Main RAG endpoint. Returns answer + sources + confidence. Pass `session_id` from the response back to maintain conversation context.")
def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    memory = _get_session(session_id)

    try:
        result = ask(req.question, memory.messages, req.language)
    except Exception as e:
        logger.exception("Error in /chat for session %s", session_id)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

    memory.add_turn(req.question, result["answer"])
    _record_stats(result, req.language)

    turn = {
        "turn": len(_session_turns[session_id]) + 1,
        "question": req.question,
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "source_type": result["source_type"],
        "confidence": result["confidence"],
        "similar_questions": result.get("similar_questions", []),
        "language": req.language,
    }
    _session_turns[session_id].append(turn)

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceItem(**{k: s.get(k, "") for k in ("source", "title", "source_type")}) for s in result.get("sources", [])],
        source_type=result["source_type"],
        confidence=result["confidence"],
        similar_questions=result.get("similar_questions", []),
        session_id=session_id,
    )


# ── /session (create) ─────────────────────────────────────────────────────────
class CreateSessionResponse(BaseModel):
    session_id: str
    status: str


@app.post("/session", response_model=CreateSessionResponse, tags=["Session"],
          summary="Create a new session",
          description="Creates a new empty session and returns its ID. Use this session_id in subsequent `/chat` calls to maintain conversation context.")
def create_session() -> CreateSessionResponse:
    session_id = str(uuid.uuid4())
    _get_session(session_id)
    return CreateSessionResponse(session_id=session_id, status="created")


# ── /session/{id}/history ──────────────────────────────────────────────────────
class HistoryMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    language: str
    turns: int
    messages: list[HistoryMessage]


@app.get("/session/{session_id}/history", response_model=SessionHistoryResponse, tags=["Session"],
         summary="Get conversation history",
         description="Returns the full Q&A history for a session.")
def session_history(session_id: str) -> SessionHistoryResponse:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    memory = _sessions[session_id]
    messages = [
        HistoryMessage(role="user" if m.type == "human" else "assistant", content=m.content if isinstance(m.content, str) else str(m.content))
        for m in memory.messages
    ]
    return SessionHistoryResponse(
        session_id=session_id,
        language=memory.language,
        turns=len(memory.messages) // 2,
        messages=messages,
    )


# ── /sessions ──────────────────────────────────────────────────────────────────
class SessionSummary(BaseModel):
    session_id: str
    turns: int
    language: str


class SessionsResponse(BaseModel):
    active_sessions: int
    sessions: list[SessionSummary]


@app.get("/sessions", response_model=SessionsResponse, tags=["Session"],
         summary="List all active sessions",
         description="Returns all currently active sessions with their turn count and detected language.")
def list_sessions() -> SessionsResponse:
    return SessionsResponse(
        active_sessions=len(_sessions),
        sessions=[
            SessionSummary(
                session_id=sid,
                turns=len(mem.messages) // 2,
                language=mem.language,
            )
            for sid, mem in _sessions.items()
        ],
    )


# ── /session/{id} DELETE ───────────────────────────────────────────────────────
class SessionDeleteResponse(BaseModel):
    session_id: str
    status: str


@app.delete("/session/{session_id}", response_model=SessionDeleteResponse, tags=["Session"],
            summary="Clear a session",
            description="Deletes chat history for the session. Equivalent to clicking 'New Chat' in the UI.")
def delete_session(session_id: str) -> SessionDeleteResponse:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    _sessions.pop(session_id)
    _session_turns.pop(session_id, None)
    return SessionDeleteResponse(session_id=session_id, status="cleared")


# ── /search ────────────────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query.")
    k: int = Field(5, ge=1, le=20, description="Number of results to return (1–20).")


class SearchResult(BaseModel):
    content: str
    source: str
    title: str
    source_type: str


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]


@app.post("/search", response_model=SearchResponse, tags=["Search"],
          summary="Raw vector search",
          description="Retrieves matching chunks from pgvector without calling the LLM. Useful for exploring the knowledge base or building custom integrations.")
def search(req: SearchRequest) -> SearchResponse:
    try:
        docs, _ = retrieve(req.query, k=req.k)
    except Exception as e:
        logger.exception("Error in /search for query: %s", req.query)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

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
class SimilarRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to find similar threads for.")


class SimilarResponse(BaseModel):
    found: bool
    title: str = ""
    source: str = ""
    similarity_score: float = 0.0
    message: str = ""


@app.post("/similar", response_model=SimilarResponse, tags=["Search"],
          summary="Find similar community threads",
          description="Checks the community forum index for an existing thread that matches the question. No LLM is called.")
def similar(req: SimilarRequest) -> SimilarResponse:
    try:
        result = find_similar_question(req.question)
    except Exception as e:
        logger.exception("Error in /similar")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

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
class FeedbackRating(str, Enum):
    positive = "positive"
    negative = "negative"


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., description="Session ID the feedback belongs to.")
    turn: int = Field(..., ge=1, description="Turn number (1 = first Q&A, 2 = second, ...).")
    rating: FeedbackRating = Field(..., description="'positive' or 'negative'.")
    comment: str = Field("", description="Optional free-text comment.")


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: str


@app.post("/feedback", response_model=FeedbackResponse, tags=["Feedback"],
          summary="Submit answer feedback",
          description="Rate an answer as positive or negative. Link to a specific turn in a session.")
def feedback(req: FeedbackRequest) -> FeedbackResponse:
    if req.session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session '{req.session_id}' not found.")
    turns = _session_turns.get(req.session_id, [])
    if req.turn > len(turns):
        raise HTTPException(status_code=404, detail=f"Turn {req.turn} not found in session.")

    feedback_id = str(uuid.uuid4())
    turn_data = turns[req.turn - 1]
    _feedback.append({
        "feedback_id": feedback_id,
        "session_id": req.session_id,
        "turn": req.turn,
        "question": turn_data.get("question", ""),
        "rating": req.rating,
        "comment": req.comment,
    })
    return FeedbackResponse(status="recorded", feedback_id=feedback_id)


# ── /stats ─────────────────────────────────────────────────────────────────────
class StatsResponse(BaseModel):
    total_queries: int
    active_sessions: int
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    avg_sources_per_query: float
    confidence_distribution: dict[str, int]
    source_type_distribution: dict[str, int]
    language_distribution: dict[str, int]


@app.get("/stats", response_model=StatsResponse, tags=["Analytics"],
         summary="Usage statistics",
         description="Returns aggregated usage metrics — total queries, confidence levels, source types, and languages used. Useful for stakeholder reporting.")
def stats() -> StatsResponse:
    total = _stats["total_queries"]
    avg_sources = round(_stats["total_sources"] / total, 2) if total else 0.0
    pos = sum(1 for f in _feedback if f["rating"] == "positive")
    neg = sum(1 for f in _feedback if f["rating"] == "negative")
    return StatsResponse(
        total_queries=total,
        active_sessions=len(_sessions),
        total_feedback=len(_feedback),
        positive_feedback=pos,
        negative_feedback=neg,
        avg_sources_per_query=avg_sources,
        confidence_distribution=dict(_stats["confidence"]),
        source_type_distribution=dict(_stats["source_type"]),
        language_distribution=dict(_stats["language"]),
    )


# ── /export/{session_id} ───────────────────────────────────────────────────────
class ExportFormat(str, Enum):
    json = "json"
    html = "html"


@app.post("/export/{session_id}", tags=["Session"],
          summary="Export a session",
          description="Export the full conversation as JSON (structured data) or HTML (styled report, same as Export Chat in the UI).")
def export_session(session_id: str, format: ExportFormat = ExportFormat.json):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    turns = _session_turns.get(session_id, [])
    memory = _sessions[session_id]

    if format == ExportFormat.json:
        return {
            "session_id": session_id,
            "language": memory.language,
            "total_turns": len(turns),
            "turns": turns,
        }

    # HTML export
    rows = ""
    for t in turns:
        badge = {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}.get(t.get("confidence", ""), "")
        src_html = ""
        if t.get("sources"):
            links = "".join(
                f'<li><a href="{_html.escape(s.get("source",""))}" target="_blank">{_html.escape(s.get("title","") or s.get("source",""))}</a></li>'
                for s in t["sources"] if s.get("source")
            )
            if links:
                src_html = f'<div class="sources"><strong>Sources:</strong><ul>{links}</ul></div>'

        rows += f"""
        <div class="turn">
          <div class="question"><span class="label">Q{t["turn"]}</span><p>{_html.escape(t["question"])}</p></div>
          <div class="answer">
            <span class="label">Answer</span>
            {"<span class='badge'>" + badge + "</span>" if badge else ""}
            <p>{_html.escape(t["answer"])}</p>{src_html}
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>MOSIP Nexus — Session Export</title>
<style>
  body{{font-family:Arial,sans-serif;max-width:900px;margin:40px auto;color:#222}}
  h1{{color:#1a56db}}.meta{{color:#666;font-size:.9em;margin-bottom:30px}}
  .turn{{border:1px solid #e2e8f0;border-radius:8px;margin-bottom:20px;overflow:hidden}}
  .question{{background:#f0f4ff;padding:16px}}.answer{{background:#fff;padding:16px}}
  .label{{font-size:.75em;font-weight:700;text-transform:uppercase;color:#666;display:block;margin-bottom:6px}}
  .badge{{font-size:.8em;background:#f0fdf4;padding:2px 8px;border-radius:12px;margin-bottom:8px;display:inline-block}}
  .sources{{margin-top:12px;font-size:.85em;background:#f8fafc;padding:10px;border-radius:6px}}
  .sources ul{{margin:6px 0 0 0;padding-left:18px}}.sources li{{margin-bottom:4px}}
  a{{color:#1a56db}}
</style></head>
<body>
  <h1>🔷 MOSIP Nexus — Session Export</h1>
  <div class="meta">Session: {_html.escape(session_id)} &nbsp;|&nbsp; Language: {_html.escape(memory.language)} &nbsp;|&nbsp; Turns: {len(turns)}</div>
  {rows}
</body></html>"""

    return HTMLResponse(content=html, media_type="text/html",
                        headers={"Content-Disposition": f'attachment; filename="mosip_session_{session_id[:8]}.html"'})


# ── /batch ─────────────────────────────────────────────────────────────────────
class BatchRequest(BaseModel):
    questions: list[str] = Field(..., min_length=1, max_length=10, description="List of questions (max 10).")
    session_id: str | None = Field(None, description="Shared session — questions are answered sequentially, each aware of previous.")
    language: str = Field("English", description="Response language for all questions.")


class BatchResponse(BaseModel):
    session_id: str
    total: int
    results: list[ChatResponse]


@app.post("/batch", response_model=BatchResponse, tags=["Chat"],
          summary="Ask multiple questions at once",
          description="Process up to 10 questions sequentially in a single request. Each question is aware of the previous answers (shared session context).")
def batch(req: BatchRequest) -> BatchResponse:
    session_id = req.session_id or str(uuid.uuid4())
    memory = _get_session(session_id)

    # Phase 1 — compute all results without touching session state.
    # A growing temp list gives each question context from the previous ones.
    temp_messages = list(memory.messages)
    raw_results: list[tuple[str, dict]] = []

    for i, question in enumerate(req.questions):
        try:
            result = ask(question, temp_messages, req.language)
        except Exception as e:
            logger.exception("Error in /batch on question index %d", i)
            raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
        raw_results.append((question, result))
        temp_messages = [*temp_messages, HumanMessage(content=question), AIMessage(content=result["answer"])]

    # Phase 2 — all questions succeeded; commit turns and stats atomically.
    responses: list[ChatResponse] = []
    for question, result in raw_results:
        memory.add_turn(question, result["answer"])
        _record_stats(result, req.language)
        turn = {
            "turn": len(_session_turns[session_id]) + 1,
            "question": question,
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "source_type": result["source_type"],
            "confidence": result["confidence"],
            "similar_questions": result.get("similar_questions", []),
            "language": req.language,
        }
        _session_turns[session_id].append(turn)
        responses.append(ChatResponse(
            answer=result["answer"],
            sources=[SourceItem(**{k: s.get(k, "") for k in ("source", "title", "source_type")}) for s in result.get("sources", [])],
            source_type=result["source_type"],
            confidence=result["confidence"],
            similar_questions=result.get("similar_questions", []),
            session_id=session_id,
        ))

    return BatchResponse(session_id=session_id, total=len(responses), results=responses)


# ── /health ────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    collections: dict[str, Any]
    active_sessions: int


@app.get("/health", response_model=HealthResponse, tags=["System"],
         summary="System health check",
         description="Returns pgvector collection chunk counts and active session count.")
def health(response: Response) -> HealthResponse:
    try:
        _retriever._get_stores()  # ensure embedding model + stores are initialised
        collections: dict[str, Any] = _retriever.get_collection_counts()
    except Exception:
        logger.exception("Error reading pgvector collection counts in /health")
        response.status_code = 503
        return HealthResponse(
            status="degraded",
            collections={"error": "Unable to read collection stats."},
            active_sessions=len(_sessions),
        )
    return HealthResponse(
        status="ok",
        collections=collections,
        active_sessions=len(_sessions),
    )

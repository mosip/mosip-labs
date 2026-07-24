"""Session controller — API-facing operations over ``db.crud.sessions``.

Maps HTTP session endpoints to Postgres persistence and hydrates
``memory.session.SessionMemory`` for the RAG condenser. Raises
``BadRequestError`` for invalid UUIDs and ``NotFoundError`` when a session
is missing.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from errors import BadRequestError, NotFoundError
from config.settings import SESSION_MAX_COUNT, SESSION_TTL_SECONDS
from db.crud import sessions as session_crud
from db.crud import unit_of_work
from memory.session import SessionMemory

import logging

logger = logging.getLogger("nexus.sessions")


def _parse_id(session_id: str) -> uuid.UUID:
    """Parse a session id string into a UUID.

    Raises:
        BadRequestError: If ``session_id`` is not a valid UUID.
    """
    try:
        return uuid.UUID(session_id)
    except ValueError as e:
        raise BadRequestError(
            f"Invalid session id: {session_id}",
            code="INVALID_SESSION_ID",
        ) from e


def create_session() -> str:
    """Create an empty chat session and return its UUID string."""
    row = session_crud.create()
    logger.info("Created session %s", row.id)
    return str(row.id)


def get_memory(session_id: str) -> SessionMemory:
    """Load session as SessionMemory for the RAG condenser.

    Purges idle sessions first, then rebuilds Human/AI message pairs from
    persisted turns. Creates the session if it does not exist yet.

    Args:
        session_id: Session UUID string.

    Returns:
        Hydrated ``SessionMemory`` (may be empty for a new session).

    Raises:
        BadRequestError: Invalid UUID.
    """
    sid = _parse_id(session_id)
    with unit_of_work() as uow:
        session_crud.purge_idle(
            ttl_seconds=SESSION_TTL_SECONDS,
            max_count=SESSION_MAX_COUNT,
            uow=uow,
        )
        row = session_crud.load_with_turns(sid, uow=uow)
        if row is None:
            row = session_crud.get_or_create(sid, uow=uow)
            uow.db.refresh(row)
            turns = []
        else:
            turns = list(row.turns)
        mem = SessionMemory(language=row.language, lang_code=row.lang_code)
        for t in turns:
            mem.messages.append(HumanMessage(content=t.question))
            mem.messages.append(AIMessage(content=t.answer))
        mem.touch()
        return mem


def ensure_session(session_id: str | None) -> str:
    """Return an existing session id or create a new one.

    Args:
        session_id: Optional client-supplied UUID; ``None`` creates a new session.

    Returns:
        Canonical session UUID string.

    Raises:
        BadRequestError: Invalid UUID when ``session_id`` is provided.
    """
    if session_id:
        sid = _parse_id(session_id)
        session_crud.get_or_create(sid)
        return str(sid)
    return create_session()


def set_language(session_id: str, lang_code: str, language: str) -> None:
    """Persist the session's response language.

    Raises:
        BadRequestError: Invalid UUID.
    """
    sid = _parse_id(session_id)
    session_crud.set_language(sid, lang_code, language)


def add_turn(
    session_id: str,
    *,
    question: str,
    answer: str,
    sources: list,
    source_type: str,
    confidence: str,
    similar_questions: list,
    language: str,
    token_usage: dict | None = None,
    chunk_ids: list | None = None,
) -> dict[str, Any]:
    """Persist one Q&A turn and return a serialisable turn dict.

    Raises:
        BadRequestError: Invalid UUID.
    """
    sid = _parse_id(session_id)
    turn = session_crud.add_turn(
        sid,
        question=question,
        answer=answer,
        sources=sources,
        source_type=source_type,
        confidence=confidence,
        similar_questions=similar_questions,
        language=language,
        token_usage=token_usage,
        chunk_ids=chunk_ids,
    )
    return session_crud.turn_to_dict(turn)


def get_last_turn_chunk_ids(session_id: str) -> list[str]:
    """Chunk ids used to answer the most recent turn (for the follow-up signal)."""
    sid = _parse_id(session_id)
    turn = session_crud.get_last_turn(sid)
    return list(turn.chunk_ids or []) if turn else []


def get_history(session_id: str) -> dict[str, Any]:
    """Return conversation history as alternating user/assistant messages.

    Raises:
        NotFoundError: Session not found or cleared.
        BadRequestError: Invalid UUID.
    """
    sid = _parse_id(session_id)
    with unit_of_work() as uow:
        row = session_crud.load_with_turns(sid, uow=uow)
        if row is None:
            raise NotFoundError(f"Session '{session_id}' not found.", code="SESSION_NOT_FOUND")
        session_crud.touch(sid, uow=uow)
        return {
            "session_id": str(row.id),
            "language": row.language,
            "turns": len(row.turns),
            "messages": [
                item
                for t in row.turns
                for item in (
                    {"role": "user", "content": t.question},
                    {"role": "assistant", "content": t.answer},
                )
            ],
        }


def list_sessions() -> dict[str, Any]:
    """List active sessions after purging idle ones (for ``GET /sessions``)."""
    with unit_of_work() as uow:
        session_crud.purge_idle(
            ttl_seconds=SESSION_TTL_SECONDS,
            max_count=SESSION_MAX_COUNT,
            uow=uow,
        )
        rows = session_crud.list_active(uow=uow)
        return {
            "active_sessions": len(rows),
            "sessions": [
                {
                    "session_id": str(r.id),
                    "turns": len(r.turns),
                    "language": r.language,
                }
                for r in rows
            ],
        }


def delete_session(session_id: str) -> None:
    """Soft-clear a session (equivalent to UI "New Chat").

    Idempotent: no-op if the session is already missing or cleared.

    Raises:
        BadRequestError: Invalid UUID.
    """
    sid = _parse_id(session_id)
    cleared = session_crud.soft_delete(sid)
    if cleared:
        logger.info("Soft-cleared session %s", sid)
    else:
        logger.debug("Soft-clear no-op for session %s (missing or already cleared)", sid)


def export_session(session_id: str) -> dict[str, Any]:
    """Export full turn payload for JSON/HTML download.

    Raises:
        NotFoundError: Session not found or cleared.
        BadRequestError: Invalid UUID.
    """
    sid = _parse_id(session_id)
    row = session_crud.load_with_turns(sid)
    if row is None:
        raise NotFoundError(f"Session '{session_id}' not found.", code="SESSION_NOT_FOUND")
    turns = [session_crud.turn_to_dict(t) for t in row.turns]
    return {
        "session_id": str(row.id),
        "language": row.language,
        "total_turns": len(turns),
        "turns": turns,
    }


def export_session_html(session_id: str) -> tuple[str, str]:
    """Build a downloadable HTML report for a session.

    Returns:
        ``(html_body, filename)``.

    Raises:
        NotFoundError / BadRequestError: Same as ``export_session``.
    """
    import html as html_lib

    from config.settings import PRODUCT_NAME, PRODUCT_SLUG

    data = export_session(session_id)
    turns = data["turns"]
    language = data["language"]
    sid = data["session_id"]

    rows = ""
    for t in turns:
        badge = {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}.get(
            t.get("confidence", ""), ""
        )
        usage = t.get("token_usage") or {}
        tokens_html = ""
        if usage.get("total_tokens"):
            tokens_html = (
                f'<div class="tokens">Tokens: {int(usage.get("total_tokens", 0)):,}'
                f' (in {int(usage.get("prompt_tokens", 0)):,}'
                f' · out {int(usage.get("completion_tokens", 0)):,})</div>'
            )
        src_html = ""
        if t.get("sources"):
            links = "".join(
                f'<li><a href="{html_lib.escape(s.get("source", ""))}" target="_blank">'
                f'{html_lib.escape(s.get("title", "") or s.get("source", ""))}</a></li>'
                for s in t["sources"]
                if s.get("source")
            )
            if links:
                src_html = (
                    f'<div class="sources"><strong>Sources:</strong><ul>{links}</ul></div>'
                )

        rows += f"""
        <div class="turn">
          <div class="question"><span class="label">Q{t["turn"]}</span>
            <p>{html_lib.escape(t["question"])}</p></div>
          <div class="answer">
            <span class="label">Answer</span>
            {"<span class='badge'>" + badge + "</span>" if badge else ""}
            <p>{html_lib.escape(t["answer"])}</p>{src_html}{tokens_html}
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{html_lib.escape(PRODUCT_NAME)} — Session Export</title>
<style>
  body{{font-family:Arial,sans-serif;max-width:900px;margin:40px auto;color:#222}}
  h1{{color:#1a56db}}.meta{{color:#666;font-size:.9em;margin-bottom:30px}}
  .turn{{border:1px solid #e2e8f0;border-radius:8px;margin-bottom:20px;overflow:hidden}}
  .question{{background:#f0f4ff;padding:16px}}.answer{{background:#fff;padding:16px}}
  .label{{font-size:.75em;font-weight:700;text-transform:uppercase;color:#666;display:block;margin-bottom:6px}}
  .badge{{font-size:.8em;background:#f0fdf4;padding:2px 8px;border-radius:12px;margin-bottom:8px;display:inline-block}}
  .tokens{{margin-top:10px;font-size:.8em;color:#64748b}}
  .sources{{margin-top:12px;font-size:.85em;background:#f8fafc;padding:10px;border-radius:6px}}
  .sources ul{{margin:6px 0 0 0;padding-left:18px}}.sources li{{margin-bottom:4px}}
  a{{color:#1a56db}}
</style></head>
<body>
  <h1>{html_lib.escape(PRODUCT_NAME)} — Session Export</h1>
  <div class="meta">Session: {html_lib.escape(sid)} &nbsp;|&nbsp; Language: {html_lib.escape(language)} &nbsp;|&nbsp; Turns: {len(turns)}</div>
  {rows}
</body></html>"""

    filename = f"{PRODUCT_SLUG}_session_{sid[:8]}.html"
    return html, filename


def get_turn_question(session_id: str, turn_number: int) -> str | None:
    """Return the question text for a turn, or ``None`` if missing."""
    sid = _parse_id(session_id)
    turn = session_crud.get_turn(sid, turn_number)
    return turn.question if turn else None


def session_exists(session_id: str) -> bool:
    """Return True if ``session_id`` is a valid UUID of an active session."""
    try:
        sid = _parse_id(session_id)
    except BadRequestError:
        return False
    return session_crud.get_active(sid) is not None


def count_active() -> int:
    """Return the number of non-cleared sessions."""
    return session_crud.count_active()

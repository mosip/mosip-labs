"""Chat session / turn CRUD wrappers.

Each function opens its own transaction via ``unit_of_work()`` unless a
``UnitOfWork`` is passed for multi-step composition.

Example::

    from db.crud import sessions

    row = sessions.create()
    sessions.add_turn(row.id, question="...", answer="...", ...)
"""

from __future__ import annotations

import uuid
from typing import Any

from db.crud.uow import UnitOfWork, unit_of_work
from db.models import ChatSession, ChatTurn


def create(session_id: uuid.UUID | None = None, *, uow: UnitOfWork | None = None) -> ChatSession:
    """Create a new empty chat session."""

    def _run(w: UnitOfWork) -> ChatSession:
        return w.sessions.create(session_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def get(session_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> ChatSession | None:
    """Load a session by id (including soft-cleared)."""

    def _run(w: UnitOfWork) -> ChatSession | None:
        return w.sessions.get(session_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def get_active(session_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> ChatSession | None:
    """Load a session only if it exists and is not soft-cleared."""

    def _run(w: UnitOfWork) -> ChatSession | None:
        return w.sessions.get_active(session_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def get_or_create(session_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> ChatSession:
    """Return active session, reactivate cleared, or create."""

    def _run(w: UnitOfWork) -> ChatSession:
        return w.sessions.get_or_create(session_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def load_with_turns(
    session_id: uuid.UUID,
    *,
    uow: UnitOfWork | None = None,
) -> ChatSession | None:
    """Load an active session with turns eagerly loaded."""

    def _run(w: UnitOfWork) -> ChatSession | None:
        return w.sessions.load_with_turns(session_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def set_language(
    session_id: uuid.UUID,
    lang_code: str,
    language: str,
    *,
    uow: UnitOfWork | None = None,
) -> ChatSession:
    """Update language fields on a session (creates if missing)."""

    def _run(w: UnitOfWork) -> ChatSession:
        row = w.sessions.get_or_create(session_id)
        w.sessions.set_language(row, lang_code, language)
        return row

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def soft_delete(session_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> bool:
    """Soft-clear a session. Returns False if already missing/cleared."""

    def _run(w: UnitOfWork) -> bool:
        row = w.sessions.get_active(session_id)
        if row is None:
            return False
        w.sessions.clear(row)
        return True

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def hard_delete(session_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> bool:
    """Permanently delete a session and cascaded rows."""

    def _run(w: UnitOfWork) -> bool:
        return w.sessions.hard_delete(session_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def list_active(*, limit: int = 500, uow: UnitOfWork | None = None) -> list[ChatSession]:
    """List non-cleared sessions newest-first."""

    def _run(w: UnitOfWork) -> list[ChatSession]:
        return w.sessions.list_active(limit=limit)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def count_active(*, uow: UnitOfWork | None = None) -> int:
    """Count non-cleared sessions."""

    def _run(w: UnitOfWork) -> int:
        return w.sessions.count_active()

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def purge_idle(
    *,
    ttl_seconds: int,
    max_count: int,
    uow: UnitOfWork | None = None,
) -> int:
    """Soft-clear idle / overflow sessions. Returns how many were cleared."""

    def _run(w: UnitOfWork) -> int:
        return w.sessions.purge_idle(ttl_seconds=ttl_seconds, max_count=max_count)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def add_turn(
    session_id: uuid.UUID,
    *,
    question: str,
    answer: str,
    sources: list,
    source_type: str,
    confidence: str,
    similar_questions: list,
    language: str,
    token_usage: dict | None = None,
    uow: UnitOfWork | None = None,
) -> ChatTurn:
    """Append a Q&A turn to a session (creates session if needed)."""

    def _run(w: UnitOfWork) -> ChatTurn:
        row = w.sessions.get_or_create(session_id)
        return w.sessions.add_turn(
            row,
            question=question,
            answer=answer,
            sources=sources,
            source_type=source_type,
            confidence=confidence,
            similar_questions=similar_questions,
            language=language,
            token_usage=token_usage,
        )

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def get_turn(
    session_id: uuid.UUID,
    turn_number: int,
    *,
    uow: UnitOfWork | None = None,
) -> ChatTurn | None:
    """Load one turn by session id and 1-based turn number."""

    def _run(w: UnitOfWork) -> ChatTurn | None:
        return w.sessions.get_turn(session_id, turn_number)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def list_turns(session_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> list[ChatTurn]:
    """Return all turns for a session ordered by turn number."""

    def _run(w: UnitOfWork) -> list[ChatTurn]:
        return w.sessions.list_turns(session_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def update_turn(
    session_id: uuid.UUID,
    turn_number: int,
    *,
    answer: str | None = None,
    sources: list | None = None,
    source_type: str | None = None,
    confidence: str | None = None,
    similar_questions: list | None = None,
    uow: UnitOfWork | None = None,
) -> ChatTurn | None:
    """Patch fields on an existing turn."""

    def _run(w: UnitOfWork) -> ChatTurn | None:
        return w.sessions.update_turn(
            session_id,
            turn_number,
            answer=answer,
            sources=sources,
            source_type=source_type,
            confidence=confidence,
            similar_questions=similar_questions,
        )

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def delete_turn(
    session_id: uuid.UUID,
    turn_number: int,
    *,
    uow: UnitOfWork | None = None,
) -> bool:
    """Hard-delete one turn."""

    def _run(w: UnitOfWork) -> bool:
        return w.sessions.delete_turn(session_id, turn_number)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def touch(session_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> None:
    """Bump ``last_access`` on an active session if it exists."""

    def _run(w: UnitOfWork) -> None:
        row = w.sessions.get_active(session_id)
        if row is not None:
            w.sessions.touch(row)

    if uow is not None:
        _run(uow)
        return
    with unit_of_work() as w:
        _run(w)


def turn_to_dict(turn: ChatTurn) -> dict[str, Any]:
    """Serialise a turn for API / export payloads."""
    return {
        "turn": turn.turn_number,
        "question": turn.question,
        "answer": turn.answer,
        "sources": turn.sources,
        "source_type": turn.source_type,
        "confidence": turn.confidence,
        "similar_questions": turn.similar_questions,
        "token_usage": turn.token_usage or {},
        "language": turn.language,
    }

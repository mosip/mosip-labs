"""Session/chunk feedback CRUD wrappers."""

from __future__ import annotations

import uuid

from db.crud.uow import UnitOfWork, unit_of_work
from db.models import SessionChunkFeedback


def upsert(
    session_id: uuid.UUID,
    chunk_id: uuid.UUID,
    rating: str,
    *,
    uow: UnitOfWork | None = None,
) -> tuple[SessionChunkFeedback, str | None, float]:
    """Record this session's rating for a chunk. See ``SessionChunkFeedbackRepository.upsert``."""

    def _run(w: UnitOfWork) -> tuple[SessionChunkFeedback, str | None, float]:
        return w.session_chunk_feedback.upsert(session_id, chunk_id, rating)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def set_contribution(
    session_id: uuid.UUID,
    chunk_id: uuid.UUID,
    contribution: float,
    *,
    uow: UnitOfWork | None = None,
) -> None:
    """Persist the contribution actually applied for a (session, chunk) vote."""

    def _run(w: UnitOfWork) -> None:
        w.session_chunk_feedback.set_contribution(session_id, chunk_id, contribution)

    if uow is not None:
        _run(uow)
        return
    with unit_of_work() as w:
        _run(w)

"""Feedback CRUD wrappers."""

from __future__ import annotations

import uuid

from db.crud.uow import UnitOfWork, unit_of_work
from db.models import Feedback


def create(
    *,
    session_id: uuid.UUID,
    turn_number: int,
    question: str,
    rating: str,
    comment: str = "",
    uow: UnitOfWork | None = None,
) -> Feedback:
    """Insert a feedback row."""

    def _run(w: UnitOfWork) -> Feedback:
        return w.feedback.create(
            session_id=session_id,
            turn_number=turn_number,
            question=question,
            rating=rating,
            comment=comment,
        )

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def get(feedback_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> Feedback | None:
    """Load feedback by id."""

    def _run(w: UnitOfWork) -> Feedback | None:
        return w.feedback.get(feedback_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def list_for_session(
    session_id: uuid.UUID,
    *,
    limit: int = 100,
    uow: UnitOfWork | None = None,
) -> list[Feedback]:
    """List feedback for a session, newest first."""

    def _run(w: UnitOfWork) -> list[Feedback]:
        return w.feedback.list_for_session(session_id, limit=limit)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def delete(feedback_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> bool:
    """Hard-delete feedback. Returns True if a row was removed."""

    def _run(w: UnitOfWork) -> bool:
        return w.feedback.delete(feedback_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def counts(*, uow: UnitOfWork | None = None) -> tuple[int, int, int]:
    """Return ``(total, positive, negative)``."""

    def _run(w: UnitOfWork) -> tuple[int, int, int]:
        return w.feedback.counts()

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)

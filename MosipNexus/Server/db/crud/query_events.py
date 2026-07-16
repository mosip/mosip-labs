"""Query-event (stats) CRUD wrappers."""

from __future__ import annotations

import uuid
from typing import Any

from db.crud.uow import UnitOfWork, unit_of_work
from db.models import QueryEvent


def create(
    *,
    session_id: uuid.UUID | None,
    confidence: str,
    source_type: str,
    language: str,
    source_count: int,
    token_usage: dict | None = None,
    uow: UnitOfWork | None = None,
) -> QueryEvent:
    """Insert one analytics row for an answered query."""

    def _run(w: UnitOfWork) -> QueryEvent:
        return w.stats.record(
            session_id=session_id,
            confidence=confidence,
            source_type=source_type,
            language=language,
            source_count=source_count,
            token_usage=token_usage,
        )

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def get(event_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> QueryEvent | None:
    """Load a query event by id."""

    def _run(w: UnitOfWork) -> QueryEvent | None:
        return w.stats.get(event_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def list_recent(*, limit: int = 100, uow: UnitOfWork | None = None) -> list[QueryEvent]:
    """Return newest query events first."""

    def _run(w: UnitOfWork) -> list[QueryEvent]:
        return w.stats.list_recent(limit=limit)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def delete(event_id: uuid.UUID, *, uow: UnitOfWork | None = None) -> bool:
    """Hard-delete a query event."""

    def _run(w: UnitOfWork) -> bool:
        return w.stats.delete(event_id)

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)


def aggregate(*, uow: UnitOfWork | None = None) -> dict[str, Any]:
    """Compute totals and distribution maps for ``/stats``."""

    def _run(w: UnitOfWork) -> dict[str, Any]:
        return w.stats.aggregate()

    if uow is not None:
        return _run(uow)
    with unit_of_work() as w:
        return _run(w)

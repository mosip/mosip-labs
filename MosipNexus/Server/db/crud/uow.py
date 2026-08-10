"""Unit of work — one SQLAlchemy session + all repositories.

Use for multi-table CRUD in a single transaction::

    from db.crud import unit_of_work

    with unit_of_work() as uow:
        session = uow.sessions.create()
        uow.feedback.create(session_id=session.id, ...)
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from db.engine import session_scope
from db.repositories.feedback import FeedbackRepository
from db.repositories.session_chunk_feedback import SessionChunkFeedbackRepository
from db.repositories.sessions import SessionRepository
from db.repositories.stats import StatsRepository


class UnitOfWork:
    """Bound repositories sharing one transactional SQLAlchemy session."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.feedback = FeedbackRepository(db)
        self.session_chunk_feedback = SessionChunkFeedbackRepository(db)
        self.stats = StatsRepository(db)


@contextmanager
def unit_of_work() -> Generator[UnitOfWork, None, None]:
    """Open a transactional scope with session / feedback / stats repos.

    Yields:
        ``UnitOfWork`` — commit on success, rollback on error.
    """
    with session_scope() as db:
        yield UnitOfWork(db)

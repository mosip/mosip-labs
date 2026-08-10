"""Session/chunk feedback persistence — content-level idempotency.

Tracks the most recent rating a session has given to each individual chunk,
so re-asking the same (or a cache-served) question and voting again doesn't
re-apply a full nudge — only a genuine change of rating does.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import SessionChunkFeedback


class SessionChunkFeedbackRepository:
    """Get/upsert one (session_id, chunk_id) rating row."""

    def __init__(self, db: Session):
        """Bind to an open SQLAlchemy session (caller owns the transaction)."""
        self.db = db

    def get(self, session_id: uuid.UUID, chunk_id: uuid.UUID) -> SessionChunkFeedback | None:
        """Load the rating this session previously gave this chunk, if any."""
        return self.db.scalar(
            select(SessionChunkFeedback).where(
                SessionChunkFeedback.session_id == session_id,
                SessionChunkFeedback.chunk_id == chunk_id,
            )
        )

    def upsert(
        self,
        session_id: uuid.UUID,
        chunk_id: uuid.UUID,
        rating: str,
    ) -> tuple[SessionChunkFeedback, str | None]:
        """Record this session's rating for a chunk.

        Returns:
            ``(row, previous_rating)`` — ``previous_rating`` is ``None`` if
            this session has never rated this chunk before.
        """
        existing = self.get(session_id, chunk_id)
        if existing is not None:
            previous_rating = existing.rating
            existing.rating = rating
            self.db.flush()
            return existing, previous_rating
        row = SessionChunkFeedback(session_id=session_id, chunk_id=chunk_id, rating=rating)
        self.db.add(row)
        self.db.flush()
        return row, None

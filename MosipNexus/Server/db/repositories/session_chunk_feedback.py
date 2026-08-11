"""Session/chunk feedback persistence — content-level idempotency.

Tracks the most recent rating a session has given to each individual chunk,
so re-asking the same (or a cache-served) question and voting again doesn't
re-apply a full nudge — only a genuine change of rating does.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
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
    ) -> tuple[SessionChunkFeedback, str | None, float]:
        """Record this session's rating for a chunk.

        Atomic ``INSERT ... ON CONFLICT DO UPDATE`` (not get-then-insert/update)
        for the same reason as ``FeedbackRepository.upsert_for_turn`` — avoids
        a race window where two concurrent votes on the same (session, chunk)
        could both see "no existing row" and either crash on the unique
        constraint or double-apply a chunk-score correction.

        Returns:
            ``(row, previous_rating, previous_contribution)`` — ``previous_rating``
            is ``None`` if this session has never rated this chunk before;
            ``previous_contribution`` is the exact signed delta this session's
            prior vote (if any) applied to ``chunk_scores.explicit_score`` —
            needed to undo it precisely on a changed vote.
        """
        new_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        result = self.db.execute(
            text(
                """
                WITH previous AS (
                    SELECT rating, contribution FROM session_chunk_feedback
                    WHERE session_id = :session_id AND chunk_id = :chunk_id
                ),
                upserted AS (
                    INSERT INTO session_chunk_feedback (id, session_id, chunk_id, rating, contribution, updated_at)
                    VALUES (:id, :session_id, :chunk_id, :rating, 0.0, :updated_at)
                    ON CONFLICT (session_id, chunk_id) DO UPDATE
                    SET rating = EXCLUDED.rating, updated_at = EXCLUDED.updated_at
                    RETURNING id
                )
                SELECT u.id, p.rating AS previous_rating, p.contribution AS previous_contribution
                FROM upserted u LEFT JOIN previous p ON true
                """
            ),
            {
                "id": new_id,
                "session_id": session_id,
                "chunk_id": chunk_id,
                "rating": rating,
                "updated_at": now,
            },
        ).one()
        self.db.flush()
        self.db.expire_all()  # the raw INSERT bypassed the ORM identity map
        row = self.db.get(SessionChunkFeedback, result.id)
        assert row is not None
        return row, result.previous_rating, result.previous_contribution or 0.0

    def set_contribution(self, session_id: uuid.UUID, chunk_id: uuid.UUID, contribution: float) -> None:
        """Persist the contribution actually applied for a (session, chunk) vote."""
        row = self.get(session_id, chunk_id)
        if row is not None:
            row.contribution = contribution
            self.db.flush()

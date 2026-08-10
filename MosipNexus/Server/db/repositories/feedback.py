"""Feedback persistence.

Stores thumbs-up / thumbs-down ratings linked to a session turn. Counts feed
the ``/stats`` endpoint via ``FeedbackRepository.counts``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import Feedback


class FeedbackRepository:
    """Insert and aggregate user feedback rows."""

    def __init__(self, db: Session):
        """Bind to an open SQLAlchemy session (caller owns the transaction)."""
        self.db = db

    def create(
        self,
        *,
        session_id: uuid.UUID,
        turn_number: int,
        question: str,
        rating: str,
        comment: str = "",
    ) -> Feedback:
        """Insert a feedback row.

        Args:
            session_id: Parent chat session UUID.
            turn_number: 1-based turn index within the session.
            question: Snapshot of the question text at rating time.
            rating: ``positive`` or ``negative``.
            comment: Optional free-text comment.

        Returns:
            The flushed ``Feedback`` row.
        """
        row = Feedback(
            session_id=session_id,
            turn_number=turn_number,
            question=question,
            rating=rating,
            comment=comment or "",
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, feedback_id: uuid.UUID) -> Feedback | None:
        """Load feedback by primary key."""
        return self.db.get(Feedback, feedback_id)

    def get_for_turn(self, session_id: uuid.UUID, turn_number: int) -> Feedback | None:
        """Load the (at most one) feedback row for a session turn."""
        return self.db.scalar(
            select(Feedback).where(
                Feedback.session_id == session_id,
                Feedback.turn_number == turn_number,
            )
        )

    def upsert_for_turn(
        self,
        *,
        session_id: uuid.UUID,
        turn_number: int,
        question: str,
        rating: str,
        comment: str = "",
    ) -> tuple[Feedback, str | None]:
        """Insert feedback for a turn, or update it if already rated.

        Returns:
            ``(row, previous_rating)`` — ``previous_rating`` is ``None`` for a
            fresh vote, the prior rating string if this is a changed vote, or
            equal to ``rating`` if this is a duplicate resubmit (e.g. page
            refresh + re-click) of the same vote.
        """
        existing = self.get_for_turn(session_id, turn_number)
        if existing is not None:
            previous_rating = existing.rating
            existing.rating = rating
            if comment:
                existing.comment = comment
            self.db.flush()
            return existing, previous_rating
        row = self.create(
            session_id=session_id,
            turn_number=turn_number,
            question=question,
            rating=rating,
            comment=comment,
        )
        return row, None

    def list_for_session(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> list[Feedback]:
        """List feedback rows for a session, newest first."""
        return list(
            self.db.scalars(
                select(Feedback)
                .where(Feedback.session_id == session_id)
                .order_by(Feedback.created_at.desc())
                .limit(limit)
            )
        )

    def delete(self, feedback_id: uuid.UUID) -> bool:
        """Hard-delete a feedback row. Returns True if a row was removed."""
        row = self.get(feedback_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.flush()
        return True

    def counts(self) -> tuple[int, int, int]:
        """Return ``(total, positive, negative)`` feedback counts."""
        total = int(self.db.scalar(select(func.count()).select_from(Feedback)) or 0)
        pos = int(
            self.db.scalar(
                select(func.count()).select_from(Feedback).where(Feedback.rating == "positive")
            )
            or 0
        )
        neg = int(
            self.db.scalar(
                select(func.count()).select_from(Feedback).where(Feedback.rating == "negative")
            )
            or 0
        )
        return total, pos, neg

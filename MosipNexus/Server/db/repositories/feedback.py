"""Feedback persistence.

Stores thumbs-up / thumbs-down ratings linked to a session turn. Counts feed
the ``/stats`` endpoint via ``FeedbackRepository.counts``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text
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

        A single atomic ``INSERT ... ON CONFLICT DO UPDATE`` — not a plain
        get-then-insert/update — so two concurrent requests for the same
        (session_id, turn_number) can't both see "no existing row", both
        attempt an insert, and have the second one crash on the unique
        constraint (or, worse, both read the same stale previous_rating and
        double-apply a chunk-score correction). The ``previous`` CTE reads
        the pre-upsert row within the same statement, so there's no window
        between reading and writing for another transaction to land in.

        Returns:
            ``(row, previous_rating)`` — ``previous_rating`` is ``None`` for a
            fresh vote, the prior rating string if this is a changed vote, or
            equal to ``rating`` if this is a duplicate resubmit (e.g. page
            refresh + re-click) of the same vote.
        """
        new_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        result = self.db.execute(
            text(
                """
                WITH previous AS (
                    SELECT rating FROM feedback
                    WHERE session_id = :session_id AND turn_number = :turn_number
                ),
                upserted AS (
                    INSERT INTO feedback (id, session_id, turn_number, question, rating, comment, created_at)
                    VALUES (:id, :session_id, :turn_number, :question, :rating, :comment, :created_at)
                    ON CONFLICT (session_id, turn_number) DO UPDATE
                    SET rating = EXCLUDED.rating,
                        comment = CASE WHEN EXCLUDED.comment = '' THEN feedback.comment ELSE EXCLUDED.comment END
                    RETURNING id
                )
                SELECT u.id, p.rating AS previous_rating
                FROM upserted u LEFT JOIN previous p ON true
                """
            ),
            {
                "id": new_id,
                "session_id": session_id,
                "turn_number": turn_number,
                "question": question,
                "rating": rating,
                "comment": comment or "",
                "created_at": now,
            },
        ).one()
        self.db.flush()
        self.db.expire_all()  # the raw INSERT bypassed the ORM identity map
        row = self.db.get(Feedback, result.id)
        assert row is not None
        return row, result.previous_rating

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

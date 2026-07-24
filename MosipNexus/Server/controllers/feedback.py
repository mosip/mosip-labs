"""Feedback controller — API-facing ratings over ``db.crud``.

Validates that the session and turn exist before inserting feedback.
"""

from __future__ import annotations

import uuid

from errors import BadRequestError, NotFoundError
from chain.confidence.scorer import apply_explicit_feedback
from db.crud import feedback as feedback_crud
from db.crud import sessions as session_crud
from db.crud import unit_of_work

import logging

logger = logging.getLogger("nexus.feedback")


def record_feedback(
    *,
    session_id: str,
    turn: int,
    rating: str,
    comment: str = "",
) -> str:
    """Record positive/negative feedback for a session turn.

    Args:
        session_id: Chat session UUID string.
        turn: 1-based turn number.
        rating: ``positive`` or ``negative``.
        comment: Optional free-text comment.

    Returns:
        New feedback row UUID as a string.

    Raises:
        NotFoundError: Session or turn not found.
        BadRequestError: Invalid session UUID.
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError as e:
        raise BadRequestError(
            f"Invalid session id: {session_id}",
            code="INVALID_SESSION_ID",
        ) from e

    with unit_of_work() as uow:
        if session_crud.get_active(sid, uow=uow) is None:
            raise NotFoundError(
                f"Session '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
            )
        turn_row = session_crud.get_turn(sid, turn, uow=uow)
        if turn_row is None:
            raise NotFoundError(
                f"Turn {turn} not found in session.",
                code="TURN_NOT_FOUND",
            )
        row = feedback_crud.create(
            session_id=sid,
            turn_number=turn,
            question=turn_row.question,
            rating=rating,
            comment=comment,
            uow=uow,
        )
        chunk_ids = list(turn_row.chunk_ids or [])
        logger.info(
            "Recorded feedback id=%s session=%s turn=%s rating=%s",
            row.id,
            sid,
            turn,
            rating,
        )

    # Best-effort: propagate to chunk_scores after the feedback row commits.
    # Separate transaction (different table, no need to be atomic with it) —
    # never let a scoring failure turn a successful feedback submission into an error.
    try:
        apply_explicit_feedback(chunk_ids, rating)
    except Exception:
        logger.exception("Failed to apply explicit feedback to chunk_scores session=%s turn=%s", sid, turn)

    return str(row.id)


def feedback_counts() -> tuple[int, int, int]:
    """Return ``(total, positive, negative)`` feedback counts for ``/stats``."""
    return feedback_crud.counts()

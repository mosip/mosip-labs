"""Feedback controller — API-facing ratings over ``db.crud``.

Validates that the session and turn exist before inserting feedback.
"""

from __future__ import annotations

import uuid

from errors import BadRequestError, NotFoundError
from chain.confidence.scorer import apply_explicit_feedback, change_explicit_feedback
from db.crud import feedback as feedback_crud
from db.crud import session_chunk_feedback as chunk_feedback_crud
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

    Idempotent per (session_id, chunk) — not just per (session_id, turn).
    Re-asking the same question creates a *new* turn but usually retrieves
    (or cache-serves) the *same* chunks, so idempotency is tracked per chunk:
    a duplicate submission of the same rating for a chunk this session has
    already rated (via any turn) is a no-op; a changed rating for that chunk
    corrects the prior nudge instead of stacking a second one on top. A
    turn's chunks that this session hasn't rated before still get a full,
    fresh nudge, even if other chunks in the same turn are already-rated
    repeats.

    Returns:
        Feedback row UUID as a string (existing row's id if re-rating this turn).

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
        row, previous_turn_rating = feedback_crud.upsert_for_turn(
            session_id=sid,
            turn_number=turn,
            question=turn_row.question,
            rating=rating,
            comment=comment,
            uow=uow,
        )

        # Per-chunk session history — decides, chunk by chunk, whether this vote
        # is fresh, a duplicate (already rated this way in this session, maybe
        # via a different turn that hit the same chunks), or a genuine change.
        chunk_decisions: list[tuple[str, str | None]] = []
        for chunk_id_str in turn_row.chunk_ids or []:
            try:
                chunk_uuid = uuid.UUID(chunk_id_str)
            except (ValueError, TypeError):
                continue
            _, prev_chunk_rating = chunk_feedback_crud.upsert(sid, chunk_uuid, rating, uow=uow)
            chunk_decisions.append((chunk_id_str, prev_chunk_rating))

        logger.info(
            "Recorded feedback id=%s session=%s turn=%s rating=%s previous_turn_rating=%s chunks=%d",
            row.id,
            sid,
            turn,
            rating,
            previous_turn_rating,
            len(chunk_decisions),
        )

    # Best-effort: propagate to chunk_scores after the transaction commits.
    # Separate transaction (different table, no need to be atomic with it) —
    # never let a scoring failure turn a successful feedback submission into an error.
    try:
        new_chunks = [cid for cid, prev in chunk_decisions if prev is None]
        changed_by_old_rating: dict[str, list[str]] = {}
        for cid, prev in chunk_decisions:
            if prev is not None and prev != rating:
                changed_by_old_rating.setdefault(prev, []).append(cid)
            # prev == rating: this session already voted this way on this
            # chunk (this turn or another) — no-op, no double-counting.

        if new_chunks:
            apply_explicit_feedback(new_chunks, rating)
        for old_rating, cids in changed_by_old_rating.items():
            change_explicit_feedback(cids, old_rating=old_rating, new_rating=rating)
    except Exception:
        logger.exception("Failed to apply explicit feedback to chunk_scores session=%s turn=%s", sid, turn)

    return str(row.id)


def feedback_counts() -> tuple[int, int, int]:
    """Return ``(total, positive, negative)`` feedback counts for ``/stats``."""
    return feedback_crud.counts()

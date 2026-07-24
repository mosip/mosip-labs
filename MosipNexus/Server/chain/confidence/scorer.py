"""Autonomous multi-signal confidence scorer.

Evolves the existing single-signal confidence (best MMR relevance score,
``retrieval.retriever.retrieve``) into a blend of that per-query relevance
score and each chunk's historical reliability, without requiring any
explicit user feedback to start improving (see source_weights.py for the
signal formula and which signals are reserved for the not-yet-built
environment-diagnostic system).

No nightly recompute job: ``final_score`` is derived live from stored raw
accumulators (retrieval_count, agreement_score, follow_up_score,
explicit_score, resolution_score) plus a recency decay computed from
``first_seen_at`` — cheaper than a background batch job and always current.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from langchain_core.documents import Document

from config.settings import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM
from db.engine import session_scope
from db.models import ChunkScore

from chain.confidence.source_weights import (
    AGREEMENT_STEP,
    ANSWER_HISTORY_WEIGHT,
    ANSWER_RELEVANCE_WEIGHT,
    EXPLICIT_FEEDBACK_STEP,
    FOLLOWUP_NEGATIVE_STEP,
    RECENCY_DECAY_PER_WEEK,
    RECENCY_EXEMPT_SOURCE_TYPES,
    RETRIEVAL_SATURATION_COUNT,
    W_AGREEMENT,
    W_BASE,
    W_EXPLICIT,
    W_FOLLOWUP,
    W_RECENCY,
    W_RESOLUTION,
    W_RETRIEVAL,
    base_weight,
)

logger = logging.getLogger("nexus.confidence")


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _recency_score(source_type: str, first_seen_at: datetime) -> float:
    if source_type in RECENCY_EXEMPT_SOURCE_TYPES:
        return 1.0
    now = datetime.now(timezone.utc)
    weeks = max(0.0, (now - first_seen_at).total_seconds() / (7 * 86400))
    return RECENCY_DECAY_PER_WEEK**weeks


def _final_score(row: ChunkScore) -> float:
    retrieval_score = min(row.retrieval_count / max(1, RETRIEVAL_SATURATION_COUNT), 1.0)
    recency_score = _recency_score(row.source_type, row.first_seen_at)
    score = (
        base_weight(row.source_type) * W_BASE
        + retrieval_score * W_RETRIEVAL
        + row.agreement_score * W_AGREEMENT
        + recency_score * W_RECENCY
        + row.follow_up_score * W_FOLLOWUP
        + row.explicit_score * W_EXPLICIT
        + row.resolution_score * W_RESOLUTION
    )
    return _clamp(score)


def _chunk_uuid(doc: Document) -> uuid.UUID | None:
    """Parse a Document's pgvector row id, or None if missing/unparseable."""
    raw = getattr(doc, "id", None)
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def record_retrieval(docs: list[Document], *, product_slug: str) -> list[str]:
    """Upsert chunk_scores rows for one retrieval batch; return chunk id strings.

    Bumps ``retrieval_count`` for every retrieved chunk, and nudges
    ``agreement_score`` up for all chunks when the batch spans more than one
    source type (independent collections corroborating the same query).

    Args:
        docs: Retrieved/deduped Document list for one query (post-annotation —
            each must carry a valid ``doc.id`` to be scored).
        product_slug: Active product slug (``mosip`` / ``inji`` / ...).

    Returns:
        Chunk id strings aligned to ``docs`` (empty string where ``doc.id``
        is missing/unparseable, so callers can still zip against ``docs``).
    """
    distinct_source_types = {d.metadata.get("source_type", "") for d in docs if d.metadata.get("source_type")}
    multi_source = len(distinct_source_types) > 1

    chunk_id_strs: list[str] = []
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        for doc in docs:
            chunk_id = _chunk_uuid(doc)
            if chunk_id is None:
                chunk_id_strs.append("")
                continue
            chunk_id_strs.append(str(chunk_id))
            source_type = doc.metadata.get("source_type", "") or ""
            row = db.get(ChunkScore, chunk_id)
            if row is None:
                row = ChunkScore(
                    chunk_id=chunk_id,
                    product_slug=product_slug,
                    collection_name=doc.metadata.get("collection", "") or source_type,
                    source_type=source_type,
                    retrieval_count=0,
                    first_seen_at=now,
                )
                db.add(row)
            row.retrieval_count += 1
            row.last_retrieved_at = now
            if multi_source:
                row.agreement_score = _clamp(row.agreement_score + AGREEMENT_STEP)
    return chunk_id_strs


def score_answer(docs: list[Document], *, mmr_relevance: float) -> str:
    """Blend this-query relevance with each chunk's historical reliability.

    Call after ``record_retrieval`` so the rows read here already reflect
    this query's retrieval bump. Falls back to relevance-only scoring for
    chunks with no scorable id (keeps working before/independent of the
    chunk-id plumbing being complete everywhere).

    Args:
        docs: The same Document list passed to ``record_retrieval``.
        mmr_relevance: Best MMR relevance score across searched collections
            (0..1, from ``retrieval.retriever``) — preserves today's
            relevance-driven behaviour as the dominant signal.

    Returns:
        ``"high"`` / ``"medium"`` / ``"low"``.
    """
    chunk_ids = [cid for doc in docs if (cid := _chunk_uuid(doc)) is not None]
    history_component = mmr_relevance
    if chunk_ids:
        with session_scope() as db:
            rows = [db.get(ChunkScore, cid) for cid in chunk_ids]
            scores = [_final_score(r) for r in rows if r is not None]
        if scores:
            history_component = sum(scores) / len(scores)

    blended = _clamp(
        ANSWER_RELEVANCE_WEIGHT * mmr_relevance + ANSWER_HISTORY_WEIGHT * history_component
    )
    if blended >= CONFIDENCE_HIGH:
        return "high"
    if blended >= CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


def apply_explicit_feedback(chunk_ids: list[str], rating: str) -> None:
    """Nudge ``explicit_score`` for every chunk used in a rated turn.

    Args:
        chunk_ids: Chunk id strings persisted on the turn (``ChatTurn.chunk_ids``).
        rating: ``"positive"`` or ``"negative"``.
    """
    if not chunk_ids:
        return
    step = EXPLICIT_FEEDBACK_STEP if rating == "positive" else -EXPLICIT_FEEDBACK_STEP
    with session_scope() as db:
        for cid_str in chunk_ids:
            try:
                cid = uuid.UUID(cid_str)
            except (ValueError, TypeError):
                continue
            row = db.get(ChunkScore, cid)
            if row is not None:
                row.explicit_score = _clamp(row.explicit_score + step)
    logger.info("Applied explicit feedback rating=%s chunks=%d", rating, len(chunk_ids))


def apply_follow_up_penalty(chunk_ids: list[str]) -> None:
    """Downgrade ``follow_up_score`` — a quick follow-up suggests the prior
    turn's answer was incomplete or missed the point.

    Only the negative half of Signal 1 is implemented: detecting "no
    follow-up happened" as an implicit positive would need a time-based
    background sweep, which isn't built yet (disclosed simplification).
    """
    if not chunk_ids:
        return
    with session_scope() as db:
        for cid_str in chunk_ids:
            try:
                cid = uuid.UUID(cid_str)
            except (ValueError, TypeError):
                continue
            row = db.get(ChunkScore, cid)
            if row is not None:
                row.follow_up_score = _clamp(row.follow_up_score - FOLLOWUP_NEGATIVE_STEP)

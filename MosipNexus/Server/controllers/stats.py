"""Stats controller — record query events and dashboard aggregates for ``/stats``."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from controllers import feedback as feedback_ctrl
from controllers import sessions as sessions_ctrl
from db.crud import query_events

logger = logging.getLogger("nexus.stats")


def record_query(result: dict, language: str, session_id: str | None = None) -> None:
    """Persist one analytics event from a RAG ``ask()`` result dict.

    Args:
        result: Dict with ``confidence``, ``source_type``, and optional ``sources``.
        language: Response language name.
        session_id: Optional session UUID string (ignored if not a valid UUID).
    """
    sid = None
    if session_id:
        try:
            sid = uuid.UUID(session_id)
        except ValueError:
            sid = None
    query_events.create(
        session_id=sid,
        confidence=str(result.get("confidence", "unknown")),
        source_type=str(result.get("source_type", "unknown")),
        language=language,
        source_count=len(result.get("sources") or []),
        token_usage=result.get("token_usage") or {},
    )
    logger.debug(
        "Recorded query_event session=%s confidence=%s source_type=%s tokens=%s",
        sid,
        result.get("confidence"),
        result.get("source_type"),
        (result.get("token_usage") or {}).get("total_tokens"),
    )


def get_stats() -> dict:
    """Return aggregate maps used by ``GET /stats``."""
    return query_events.aggregate()


def get_dashboard_stats() -> dict[str, Any]:
    """Full payload for ``GET /stats`` (query + session + feedback counts)."""
    agg = get_stats()
    total = agg["total_queries"]
    avg_sources = round(agg["total_sources"] / total, 2) if total else 0.0
    total_fb, pos, neg = feedback_ctrl.feedback_counts()
    return {
        "total_queries": total,
        "active_sessions": sessions_ctrl.count_active(),
        "total_feedback": total_fb,
        "positive_feedback": pos,
        "negative_feedback": neg,
        "avg_sources_per_query": avg_sources,
        "confidence_distribution": agg["confidence"],
        "source_type_distribution": agg["source_type"],
        "language_distribution": agg["language"],
    }

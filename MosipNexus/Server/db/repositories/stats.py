"""Query event / stats persistence.

Each answered ``/chat`` (or batch item) records a ``QueryEvent`` so ``/stats``
can aggregate confidence, source type, and language distributions without
scanning chat turns.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import QueryEvent


class StatsRepository:
    """Record and aggregate per-query analytics events."""

    def __init__(self, db: Session):
        """Bind to an open SQLAlchemy session (caller owns the transaction)."""
        self.db = db

    def record(
        self,
        *,
        session_id: uuid.UUID | None,
        confidence: str,
        source_type: str,
        language: str,
        source_count: int,
        token_usage: dict | None = None,
    ) -> QueryEvent:
        """Insert one analytics row for an answered query.

        Args:
            session_id: Optional link to ``chat_sessions`` (SET NULL on delete).
            confidence: Confidence label from the RAG pipeline.
            source_type: Aggregated source classification.
            language: Response language name.
            source_count: Number of sources attached to the answer.
            token_usage: Optional LLM token counters for this query.

        Returns:
            The flushed ``QueryEvent`` row.
        """
        row = QueryEvent(
            session_id=session_id,
            confidence=confidence or "unknown",
            source_type=source_type or "unknown",
            language=language or "English",
            source_count=max(0, source_count),
            token_usage=token_usage or {},
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, event_id: uuid.UUID) -> QueryEvent | None:
        """Load a query event by primary key."""
        return self.db.get(QueryEvent, event_id)

    def list_recent(self, *, limit: int = 100) -> list[QueryEvent]:
        """Return newest query events first."""
        return list(
            self.db.scalars(
                select(QueryEvent).order_by(QueryEvent.created_at.desc()).limit(limit)
            )
        )

    def delete(self, event_id: uuid.UUID) -> bool:
        """Hard-delete a query event. Returns True if a row was removed."""
        row = self.get(event_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.flush()
        return True

    def aggregate(self) -> dict:
        """Compute totals and distribution maps for ``/stats``.

        Returns:
            Dict with ``total_queries``, ``total_sources``, and maps
            ``confidence``, ``source_type``, ``language`` → counts.
        """
        total = int(self.db.scalar(select(func.count()).select_from(QueryEvent)) or 0)
        total_sources = int(
            self.db.scalar(select(func.coalesce(func.sum(QueryEvent.source_count), 0))) or 0
        )

        def _dist(column) -> dict[str, int]:
            rows = self.db.execute(
                select(column, func.count()).group_by(column)
            ).all()
            return {str(k): int(v) for k, v in rows}

        return {
            "total_queries": total,
            "total_sources": total_sources,
            "confidence": _dist(QueryEvent.confidence),
            "source_type": _dist(QueryEvent.source_type),
            "language": _dist(QueryEvent.language),
        }

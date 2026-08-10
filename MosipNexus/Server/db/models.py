"""App-owned ORM models. LangChain vector tables are NOT declared here.

Tables:

* ``chat_sessions`` / ``chat_turns`` — conversational history for RAG
* ``feedback`` — thumbs up/down on a specific turn
* ``query_events`` — one row per answered query for ``/stats``
* ``chunk_scores`` — per-chunk confidence signal accumulators (see ``chain.confidence``)

Migrated exclusively via Alembic (see ``docs/DATABASE_LAYER.md``).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(Base):
    """One user conversation thread (may be soft-cleared via ``cleared_at``)."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    language: Mapped[str] = mapped_column(String(64), nullable=False, default="English")
    lang_code: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_access: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    turns: Mapped[list[ChatTurn]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatTurn.turn_number",
    )


class ChatTurn(Base):
    """A single Q&A pair within a session, including sources and confidence."""

    __tablename__ = "chat_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "turn_number", name="uq_chat_turns_session_turn"),
        Index("ix_chat_turns_session_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list | dict] = mapped_column(JSONB, nullable=False, default=list)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    # pgvector row UUIDs (as strings) for the chunks used to answer this turn — links
    # this turn to chunk_scores rows for explicit feedback / follow-up signal propagation.
    chunk_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    similar_questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    language: Mapped[str] = mapped_column(String(64), nullable=False, default="English")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    session: Mapped[ChatSession] = relationship(back_populates="turns")


class Feedback(Base):
    """User rating (positive/negative) for a specific session turn.

    One row per (session_id, turn_number) — re-rating updates the existing row
    (see ``controllers.feedback``) instead of inserting a duplicate, so a page
    refresh + re-click can't silently re-apply the same chunk_scores nudge.
    """

    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_session_id", "session_id"),
        UniqueConstraint("session_id", "turn_number", name="uq_feedback_session_turn"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rating: Mapped[str] = mapped_column(String(16), nullable=False)  # positive | negative
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class QueryEvent(Base):
    """One row per answered query — used for ``/stats`` aggregates."""

    __tablename__ = "query_events"
    __table_args__ = (
        Index("ix_query_events_confidence", "confidence"),
        Index("ix_query_events_source_type", "source_type"),
        Index("ix_query_events_language", "language"),
        Index("ix_query_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    language: Mapped[str] = mapped_column(String(64), nullable=False, default="English")
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ChunkScore(Base):
    """Autonomous confidence-signal accumulators for one retrieved chunk.

    ``chunk_id`` references a ``langchain_pg_embedding.id`` row (a LangChain-managed
    table, not declared here — no hard FK across schemas). Signal accumulators are
    raw running values; the weighted ``final_score`` is computed on read by
    ``chain.confidence.scorer`` (recency decay applied live from ``first_seen_at``),
    not recomputed by a background job. ``resolution_score`` stays neutral (0.5)
    until the environment-log diagnostic system (log resolution watcher) exists.
    """

    __tablename__ = "chunk_scores"
    __table_args__ = (
        Index("ix_chunk_scores_source_type", "source_type"),
        Index("ix_chunk_scores_product_slug", "product_slug"),
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    product_slug: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    collection_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    retrieval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Accumulators, each clamped to [0, 1] with 0.5 as the neutral starting point.
    agreement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    follow_up_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    explicit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    resolution_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    # Number of explicit-feedback nudges applied — sizes a diminishing-returns step so
    # a handful of bad-faith/repeat votes can't dominate a chunk that's earned many
    # good votes (see chain.confidence.scorer.apply_explicit_feedback).
    feedback_vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class SessionChunkFeedback(Base):
    """What THIS session most recently told us about ONE chunk.

    Generalises turn-level feedback idempotency (``feedback`` table's unique
    session+turn constraint) to content-level idempotency: re-asking the same
    question in a new turn re-uses the same chunks, so a repeat vote on the
    exact same rating is a no-op here too — only a *changed* rating (a genuine
    opinion change) triggers a chunk_scores correction. See
    ``controllers.feedback.record_feedback``.
    """

    __tablename__ = "session_chunk_feedback"
    __table_args__ = (
        UniqueConstraint("session_id", "chunk_id", name="uq_session_chunk_feedback"),
        Index("ix_session_chunk_feedback_session_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rating: Mapped[str] = mapped_column(String(16), nullable=False)  # positive | negative
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

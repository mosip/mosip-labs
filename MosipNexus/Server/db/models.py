"""App-owned ORM models. LangChain vector tables are NOT declared here.

Tables:

* ``chat_sessions`` / ``chat_turns`` — conversational history for RAG
* ``feedback`` — thumbs up/down on a specific turn
* ``query_events`` — one row per answered query for ``/stats``

Migrated exclusively via Alembic (see ``docs/DATABASE_LAYER.md``).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
    similar_questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    language: Mapped[str] = mapped_column(String(64), nullable=False, default="English")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    session: Mapped[ChatSession] = relationship(back_populates="turns")


class Feedback(Base):
    """User rating (positive/negative) for a specific session turn."""

    __tablename__ = "feedback"
    __table_args__ = (Index("ix_feedback_session_id", "session_id"),)

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

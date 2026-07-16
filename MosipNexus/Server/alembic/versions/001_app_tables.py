"""Create app chat / feedback / query_events tables.

Revision ID: 001_app_tables
Revises:
Create Date: 2026-07-14

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_app_tables"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False, server_default="English"),
        sa.Column("lang_code", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_access", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "chat_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("similar_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False, server_default="English"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "turn_number", name="uq_chat_turns_session_turn"),
    )
    op.create_index("ix_chat_turns_session_id", "chat_turns", ["session_id"])

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("rating", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_feedback_session_id", "feedback", ["session_id"])

    op.create_table(
        "query_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_query_events_confidence", "query_events", ["confidence"])
    op.create_index("ix_query_events_source_type", "query_events", ["source_type"])
    op.create_index("ix_query_events_language", "query_events", ["language"])
    op.create_index("ix_query_events_created_at", "query_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("query_events")
    op.drop_table("feedback")
    op.drop_table("chat_turns")
    op.drop_table("chat_sessions")

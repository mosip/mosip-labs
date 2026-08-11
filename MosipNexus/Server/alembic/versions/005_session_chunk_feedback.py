"""Add session_chunk_feedback table for content-level (not just turn-level) idempotency.

Revision ID: 005_session_chunk_feedback
Revises: 004_feedback_idempotency
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_session_chunk_feedback"
down_revision: Union[str, Sequence[str], None] = "004_feedback_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_chunk_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_session_chunk_feedback_session_id", "session_chunk_feedback", ["session_id"]
    )
    op.create_unique_constraint(
        "uq_session_chunk_feedback", "session_chunk_feedback", ["session_id", "chunk_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_session_chunk_feedback", "session_chunk_feedback", type_="unique")
    op.drop_index("ix_session_chunk_feedback_session_id", table_name="session_chunk_feedback")
    op.drop_table("session_chunk_feedback")

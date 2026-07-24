"""Add chunk_scores table and chat_turns.chunk_ids for autonomous confidence scoring.

Revision ID: 003_chunk_scores
Revises: 002_token_usage
Create Date: 2026-07-23

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_chunk_scores"
down_revision: Union[str, Sequence[str], None] = "002_token_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_turns",
        sa.Column(
            "chunk_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_table(
        "chunk_scores",
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("product_slug", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("collection_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("retrieval_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agreement_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("follow_up_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("explicit_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("resolution_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chunk_scores_source_type", "chunk_scores", ["source_type"])
    op.create_index("ix_chunk_scores_product_slug", "chunk_scores", ["product_slug"])


def downgrade() -> None:
    op.drop_index("ix_chunk_scores_product_slug", table_name="chunk_scores")
    op.drop_index("ix_chunk_scores_source_type", table_name="chunk_scores")
    op.drop_table("chunk_scores")
    op.drop_column("chat_turns", "chunk_ids")

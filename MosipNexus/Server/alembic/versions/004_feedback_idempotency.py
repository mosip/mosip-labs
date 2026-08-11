"""Feedback idempotency (unique session+turn) and chunk_scores vote counter.

Revision ID: 004_feedback_idempotency
Revises: 003_chunk_scores
Create Date: 2026-07-24

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_feedback_idempotency"
down_revision: Union[str, Sequence[str], None] = "003_chunk_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chunk_scores",
        sa.Column("feedback_vote_count", sa.Integer(), nullable=False, server_default="0"),
    )
    # Collapse any pre-existing duplicate (session_id, turn_number) feedback rows to the
    # most recent one before adding the unique constraint — safe on a fresh 003 install
    # (no feedback rows yet), but guards against re-running this against seeded data.
    # ROW_NUMBER (not created_at < created_at) so rows sharing an identical timestamp
    # still collapse to exactly one survivor instead of both surviving and breaking
    # the unique constraint below.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY session_id, turn_number
                    ORDER BY created_at DESC, id DESC
                ) AS row_number
            FROM feedback
        )
        DELETE FROM feedback AS f
        USING ranked AS r
        WHERE f.id = r.id
          AND r.row_number > 1
        """
    )
    op.create_unique_constraint(
        "uq_feedback_session_turn", "feedback", ["session_id", "turn_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_feedback_session_turn", "feedback", type_="unique")
    op.drop_column("chunk_scores", "feedback_vote_count")

"""Add session_chunk_feedback.contribution for exact vote-change reversal.

Revision ID: 006_session_chunk_contribution
Revises: 005_session_chunk_feedback
Create Date: 2026-08-11

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_session_chunk_contribution"
down_revision: Union[str, Sequence[str], None] = "005_session_chunk_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_chunk_feedback",
        sa.Column("contribution", sa.Float(), nullable=False, server_default="0.0"),
    )


def downgrade() -> None:
    op.drop_column("session_chunk_feedback", "contribution")

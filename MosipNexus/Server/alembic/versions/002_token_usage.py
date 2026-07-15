"""Add token_usage JSONB to chat_turns and query_events.

Revision ID: 002_token_usage
Revises: 001_app_tables
Create Date: 2026-07-15

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_token_usage"
down_revision: Union[str, Sequence[str], None] = "001_app_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_turns",
        sa.Column(
            "token_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "query_events",
        sa.Column(
            "token_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("query_events", "token_usage")
    op.drop_column("chat_turns", "token_usage")

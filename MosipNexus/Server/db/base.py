"""SQLAlchemy declarative base for Nexus app tables (not LangChain).

``Base.metadata`` is what Alembic migrates. LangChain's ``langchain_pg_*``
tables are excluded in ``alembic/env.py`` and must never appear here.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all app-owned ORM models."""

    pass

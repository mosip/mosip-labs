"""Database package — app tables via Alembic; vector store stays LangChain-owned.

This package owns SQLAlchemy models, repositories, and CRUD wrappers for chat
sessions, turns, feedback, and query analytics. pgvector collections
(`langchain_pg_*`) are written by ``ingestion.store`` / ``langchain_postgres``
and must not be declared in ``db.models`` or dropped by Alembic autogenerate.

Typical usage from controllers::

    from db.crud import sessions, unit_of_work

    with unit_of_work() as uow:
        sessions.create(uow=uow)
"""

from db.base import Base
from db.engine import get_engine, session_scope
from db.models import ChatSession, ChatTurn, Feedback, QueryEvent

__all__ = [
    "Base",
    "ChatSession",
    "ChatTurn",
    "Feedback",
    "QueryEvent",
    "get_engine",
    "session_scope",
]

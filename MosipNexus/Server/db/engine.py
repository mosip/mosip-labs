"""Shared SQLAlchemy engine + session factory.

One process-wide pooled engine backs both:

* App repositories (sessions, feedback, stats)
* LangChain ``PGVector`` stores (via ``get_engine()`` in the retriever)

Pool knobs come from ``config.settings`` (``PG_POOL_*``). Use
``session_scope()`` in controllers so commits/rollbacks stay consistent.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import (
    PG_CONNECTION,
    PG_MAX_OVERFLOW,
    PG_POOL_RECYCLE,
    PG_POOL_SIZE,
    PG_POOL_TIMEOUT,
)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide pooled engine (lazy-created once).

    Returns:
        SQLAlchemy ``Engine`` bound to ``PG_CONNECTION`` with pre-ping enabled.
    """
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(
            PG_CONNECTION,
            pool_size=PG_POOL_SIZE,
            max_overflow=PG_MAX_OVERFLOW,
            pool_timeout=PG_POOL_TIMEOUT,
            pool_recycle=PG_POOL_RECYCLE,
            pool_pre_ping=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the bound ``sessionmaker``, creating the engine if needed.

    Returns:
        A ``sessionmaker`` that produces ``Session`` instances.
    """
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope: commit on success, rollback on error.

    Yields:
        An open SQLAlchemy ``Session``.

    Raises:
        Exception: Re-raises after rollback if the block fails.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

"""Thin controllers over ``db.crud`` (API uses these, not raw SQL).

Public modules:

* ``controllers.chat`` — RAG orchestration for ``/chat`` and ``/batch``
* ``controllers.sessions`` — create/load/clear/export chat sessions
* ``controllers.feedback`` — record ratings
* ``controllers.stats`` — record query events and dashboard aggregates

Controllers validate HTTP inputs and shape DTOs. Persistence goes through
``db.crud`` (transactional wrappers) → ``db.repositories`` (SQLAlchemy).
Domain errors live in ``errors`` (not ``api.errors``).
"""

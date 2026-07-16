"""App-table CRUD wrappers used by Server controllers and jobs.

Layers:

* ``db.repositories.*`` — SQLAlchemy operations bound to an open ``Session``
* ``db.crud.*`` — transactional wrappers (+ optional ``UnitOfWork`` composition)
* ``controllers.*`` — HTTP/API-facing validation and DTO shaping

Typical single-op usage::

    from db.crud import sessions, feedback, query_events

    sessions.create()
    feedback.counts()

Multi-table transaction::

    from db.crud import unit_of_work

    with unit_of_work() as uow:
        s = uow.sessions.create()
        uow.feedback.create(session_id=s.id, ...)
"""

from db.crud import feedback, query_events, sessions
from db.crud.uow import UnitOfWork, unit_of_work

__all__ = [
    "UnitOfWork",
    "feedback",
    "query_events",
    "sessions",
    "unit_of_work",
]

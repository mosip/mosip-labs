"""SQLAlchemy repositories — Session-bound CRUD primitives.

Prefer ``db.crud`` from controllers and jobs. Use repositories directly only
when you already hold an open ``Session`` (or via ``UnitOfWork``).
"""

from db.repositories.feedback import FeedbackRepository
from db.repositories.sessions import SessionRepository
from db.repositories.stats import StatsRepository

__all__ = ["FeedbackRepository", "SessionRepository", "StatsRepository"]

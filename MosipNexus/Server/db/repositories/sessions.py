"""Session / turn persistence.

``SessionRepository`` is the only place that mutates ``chat_sessions`` /
``chat_turns``. Soft-delete uses ``cleared_at`` so UUIDs can be reactivated.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from db.models import ChatSession, ChatTurn


class SessionRepository:
    """CRUD helpers for chat sessions and ordered turns."""

    def __init__(self, db: Session):
        """Bind to an open SQLAlchemy session (caller owns the transaction)."""
        self.db = db

    def get(self, session_id: uuid.UUID) -> ChatSession | None:
        """Load a session by id, including cleared ones."""
        return self.db.get(ChatSession, session_id)

    def get_active(self, session_id: uuid.UUID) -> ChatSession | None:
        """Return the session only if it exists and is not soft-cleared."""
        row = self.get(session_id)
        if row is None or row.cleared_at is not None:
            return None
        return row

    def create(self, session_id: uuid.UUID | None = None) -> ChatSession:
        """Insert a new empty session.

        Args:
            session_id: Optional fixed UUID; otherwise a random UUID is assigned.

        Returns:
            The flushed ``ChatSession`` row.
        """
        row = ChatSession(id=session_id or uuid.uuid4())
        self.db.add(row)
        self.db.flush()
        return row

    def get_or_create(self, session_id: uuid.UUID) -> ChatSession:
        """Return an active session, reactivating a cleared one or creating new.

        Reactivation clears old turns and resets language to English.
        """
        row = self.get_active(session_id)
        if row is not None:
            row.last_access = datetime.now(timezone.utc)
            return row
        # Recreate if previously cleared
        existing = self.get(session_id)
        if existing is not None:
            existing.cleared_at = None
            existing.language = "English"
            existing.lang_code = "en"
            existing.last_access = datetime.now(timezone.utc)
            # Remove old turns
            for turn in list(existing.turns):
                self.db.delete(turn)
            self.db.flush()
            return existing
        return self.create(session_id)

    def touch(self, session: ChatSession) -> None:
        """Bump ``last_access`` to now (UTC)."""
        session.last_access = datetime.now(timezone.utc)

    def set_language(self, session: ChatSession, lang_code: str, language: str) -> None:
        """Update session language fields and touch ``last_access``."""
        session.lang_code = lang_code
        session.language = language
        self.touch(session)

    def add_turn(
        self,
        session: ChatSession,
        *,
        question: str,
        answer: str,
        sources: list,
        source_type: str,
        confidence: str,
        similar_questions: list,
        language: str,
        token_usage: dict | None = None,
    ) -> ChatTurn:
        """Append the next numbered turn and touch the parent session.

        Args:
            session: Parent session row (must already be persisted).
            question: User question text.
            answer: Model answer text.
            sources: List of source metadata dicts (stored as JSONB).
            source_type: Aggregated source label (e.g. ``mosip_docs``, ``mixed``).
            confidence: ``high`` / ``medium`` / ``low`` / ``n/a``.
            similar_questions: Related community titles.
            language: Response language for this turn.
            token_usage: Optional ``{prompt_tokens, completion_tokens, total_tokens}``.

        Returns:
            The flushed ``ChatTurn`` with assigned ``turn_number``.
        """
        next_n = (
            self.db.scalar(
                select(func.coalesce(func.max(ChatTurn.turn_number), 0)).where(
                    ChatTurn.session_id == session.id
                )
            )
            or 0
        ) + 1
        turn = ChatTurn(
            session_id=session.id,
            turn_number=next_n,
            question=question,
            answer=answer,
            sources=sources or [],
            source_type=source_type or "",
            confidence=confidence or "",
            similar_questions=similar_questions or [],
            token_usage=token_usage or {},
            language=language,
        )
        self.db.add(turn)
        self.touch(session)
        self.db.flush()
        return turn

    def list_turns(self, session_id: uuid.UUID) -> list[ChatTurn]:
        """Return all turns for a session ordered by ``turn_number``."""
        return list(
            self.db.scalars(
                select(ChatTurn)
                .where(ChatTurn.session_id == session_id)
                .order_by(ChatTurn.turn_number)
            )
        )

    def get_turn(self, session_id: uuid.UUID, turn_number: int) -> ChatTurn | None:
        """Load one turn by session id and 1-based turn number."""
        return self.db.scalar(
            select(ChatTurn).where(
                ChatTurn.session_id == session_id,
                ChatTurn.turn_number == turn_number,
            )
        )

    def clear(self, session: ChatSession) -> None:
        """Soft-clear: delete turns, set ``cleared_at``, reset language."""
        for turn in list(session.turns):
            self.db.delete(turn)
        session.cleared_at = datetime.now(timezone.utc)
        session.language = "English"
        session.lang_code = "en"
        self.touch(session)

    def hard_delete(self, session_id: uuid.UUID) -> bool:
        """Permanently delete a session (cascades turns/feedback). Returns True if removed."""
        row = self.get(session_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.flush()
        return True

    def update_turn(
        self,
        session_id: uuid.UUID,
        turn_number: int,
        *,
        answer: str | None = None,
        sources: list | None = None,
        source_type: str | None = None,
        confidence: str | None = None,
        similar_questions: list | None = None,
    ) -> ChatTurn | None:
        """Patch fields on an existing turn. Returns the turn or ``None`` if missing."""
        turn = self.get_turn(session_id, turn_number)
        if turn is None:
            return None
        if answer is not None:
            turn.answer = answer
        if sources is not None:
            turn.sources = sources
        if source_type is not None:
            turn.source_type = source_type
        if confidence is not None:
            turn.confidence = confidence
        if similar_questions is not None:
            turn.similar_questions = similar_questions
        self.db.flush()
        return turn

    def delete_turn(self, session_id: uuid.UUID, turn_number: int) -> bool:
        """Hard-delete one turn. Returns True if a row was removed."""
        turn = self.get_turn(session_id, turn_number)
        if turn is None:
            return False
        self.db.delete(turn)
        self.db.flush()
        return True

    def list_active(self, *, limit: int = 500) -> list[ChatSession]:
        """List non-cleared sessions newest-first, with turns eagerly loaded."""
        return list(
            self.db.scalars(
                select(ChatSession)
                .options(selectinload(ChatSession.turns))
                .where(ChatSession.cleared_at.is_(None))
                .order_by(ChatSession.last_access.desc())
                .limit(limit)
            )
        )

    def count_active(self) -> int:
        """Count sessions where ``cleared_at`` is null."""
        return int(
            self.db.scalar(
                select(func.count()).select_from(ChatSession).where(ChatSession.cleared_at.is_(None))
            )
            or 0
        )

    def purge_idle(self, *, ttl_seconds: int, max_count: int) -> int:
        """Soft-clear idle sessions; then soft-clear oldest beyond ``max_count``.

        Args:
            ttl_seconds: Idle threshold (minimum 60s applied internally).
            max_count: Soft cap on active sessions (minimum 100 applied).

        Returns:
            Number of sessions soft-cleared in this call.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=max(60, ttl_seconds))
        idle = list(
            self.db.scalars(
                select(ChatSession).where(
                    ChatSession.cleared_at.is_(None),
                    ChatSession.last_access < cutoff,
                )
            )
        )
        for row in idle:
            self.clear(row)

        active = self.list_active(limit=max_count + 500)
        overflow = len(active) - max(100, max_count)
        if overflow > 0:
            for row in active[-overflow:]:
                self.clear(row)
        return len(idle) + max(0, overflow)

    def load_with_turns(self, session_id: uuid.UUID) -> ChatSession | None:
        """Load an active session with turns eagerly loaded, or ``None``."""
        return self.db.scalar(
            select(ChatSession)
            .options(selectinload(ChatSession.turns))
            .where(ChatSession.id == session_id, ChatSession.cleared_at.is_(None))
        )

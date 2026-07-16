"""
Session Memory.

Thin wrapper around LangChain HumanMessage / AIMessage objects for the RAG
condenser. Persisted turns live in Postgres (``chat_turns``); controllers
hydrate this object per request. It is **not** the source of truth across
workers — always reload via ``controllers.sessions.get_memory``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


@dataclass
class SessionMemory:
    """In-request conversation view (not the source of truth).

    Attributes:
        messages: Alternating Human/AI messages for the condenser.
        language: Human-readable language name (e.g. ``English``).
        lang_code: Short language code (e.g. ``en``).
        last_access: Unix timestamp of last touch (in-process only).
    """

    messages: list[BaseMessage] = field(default_factory=list)
    language: str = "English"
    lang_code: str = "en"
    last_access: float = field(default_factory=time.time)

    def touch(self) -> None:
        """Update ``last_access`` to the current time."""
        self.last_access = time.time()

    def add_turn(self, question: str, answer: str) -> None:
        """Append a Human + AI message pair to the in-memory history."""
        self.messages.append(HumanMessage(content=question))
        self.messages.append(AIMessage(content=answer))
        self.touch()

    def clear(self) -> None:
        """Drop messages and reset language fields (in-memory only)."""
        self.messages.clear()
        self.language = "English"
        self.lang_code = "en"
        self.touch()

    def set_language(self, lang_code: str, lang_name: str) -> None:
        """Set language code/name on this in-memory view."""
        self.lang_code = lang_code
        self.language = lang_name
        self.touch()

    @property
    def is_empty(self) -> bool:
        """True when no messages have been added yet."""
        return len(self.messages) == 0

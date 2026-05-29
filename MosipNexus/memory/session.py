"""
Session Memory.

Thin wrapper around a list of LangChain HumanMessage / AIMessage objects.
Each Streamlit session holds one SessionMemory instance in st.session_state.
The full history is passed to the condenser and QA chains on every turn.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


@dataclass
class SessionMemory:
    """Stores the conversation history for one user session."""

    messages: list[BaseMessage] = field(default_factory=list)
    language: str = "English"
    lang_code: str = "en"

    def add_turn(self, question: str, answer: str) -> None:
        """Append a completed Q/A turn to history."""
        self.messages.append(HumanMessage(content=question))
        self.messages.append(AIMessage(content=answer))

    def clear(self) -> None:
        """Reset history and language (called on New Chat)."""
        self.messages.clear()
        self.language = "English"
        self.lang_code = "en"

    def set_language(self, lang_code: str, lang_name: str) -> None:
        self.lang_code = lang_code
        self.language = lang_name

    @property
    def is_empty(self) -> bool:
        return len(self.messages) == 0

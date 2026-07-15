"""Token-budget helpers for BYOK chat — pack context and trim history.

Goal: keep prompt tokens predictable so callers are not billed for huge
retrieved dumps or long prior answers.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

_FOLLOW_UP_RE = re.compile(
    r"\b("
    r"it|this|that|those|these|they|them|the same|above|previous|earlier|"
    r"also|what about|how about|and then|continue|more details|"
    r"explain (?:that|this|it)|same (?:error|issue|problem)|as (?:above|before)"
    r")\b",
    re.IGNORECASE,
)


def pack_context(docs: list[Document], *, max_chars: int, max_docs: int) -> str:
    """Join retrieved chunks into a char-capped context string.

    Prefer earlier (higher-ranked) docs. Each chunk gets a short header so the
    model can cite without needing the full metadata dump.
    """
    if max_chars <= 0 or max_docs <= 0 or not docs:
        return ""

    parts: list[str] = []
    used = 0
    for doc in docs[:max_docs]:
        meta = doc.metadata or {}
        stype = (meta.get("source_type") or "").strip()
        title = (meta.get("title") or "").strip()
        header = f"[{stype}] {title}".strip() if (stype or title) else "[chunk]"
        body = (doc.page_content or "").strip()
        if not body:
            continue
        piece = f"{header}\n{body}"
        overhead = 2 if parts else 0  # "\n\n"
        if used + overhead + len(piece) <= max_chars:
            parts.append(piece)
            used += overhead + len(piece)
            continue
        remaining = max_chars - used - overhead
        if remaining < 180:
            break
        parts.append(piece[:remaining].rstrip() + "…")
        break

    return "\n\n".join(parts)


def trim_history(
    messages: list,
    *,
    max_messages: int,
    max_chars_per_message: int,
) -> list[BaseMessage]:
    """Keep only the last ``max_messages`` turns, truncating long assistant replies.

    Empty / non-positive limits return an empty list (no history in the prompt).
    """
    if max_messages <= 0 or not messages:
        return []

    recent = list(messages[-max_messages:])
    out: list[BaseMessage] = []
    for msg in recent:
        content = getattr(msg, "content", "") or ""
        if isinstance(content, list):
            # Rare multimodal content — flatten to text
            content = " ".join(
                str(part.get("text", part)) if isinstance(part, dict) else str(part)
                for part in content
            )
        text = str(content)
        if max_chars_per_message > 0 and len(text) > max_chars_per_message:
            text = text[: max_chars_per_message - 1].rstrip() + "…"

        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            out.append(HumanMessage(content=text))
        elif isinstance(msg, AIMessage) or getattr(msg, "type", "") == "ai":
            out.append(AIMessage(content=text))
        else:
            # Preserve unknown roles as human text to avoid dropping context
            out.append(HumanMessage(content=text))
    return out


def needs_condense(question: str, chat_history: list) -> bool:
    """True when a follow-up likely depends on prior turns (worth an LLM rewrite).

    Skipping condense saves a full LLM round-trip on standalone questions.
    """
    if not chat_history:
        return False
    q = (question or "").strip()
    if len(q) < 12:
        return True
    if _FOLLOW_UP_RE.search(q):
        return True
    # Very short questions with history are usually follow-ups
    return len(q) < 40


def usage_snapshot(token_usage: dict[str, Any] | None) -> str:
    """Short log-friendly summary."""
    if not token_usage:
        return "0"
    return str(token_usage.get("total_tokens") or 0)

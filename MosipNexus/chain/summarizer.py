"""
Thread Summarizer.

Condenses long community threads (multiple answers) into a structured summary
with key points and the final resolution.  Called when a thread has more than
a threshold number of answers to avoid overwhelming the LLM context window.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).parent.parent))
from chain.query_engine import build_llm

_llm: BaseChatModel | None = None

MIN_ANSWERS_TO_SUMMARIZE = 4   # threads with fewer answers are used as-is


def _get_llm() -> BaseChatModel:
    global _llm
    if _llm is None:
        _llm = build_llm()
    return _llm


def summarize_thread(title: str, answers: list[dict], language: str = "English") -> str:
    """Summarise a list of community answer dicts into a concise thread summary.

    Args:
        title:    Topic title (used for context).
        answers:  List of answer dicts with keys: text, accepted, vote_count.
        language: Language to respond in.

    Returns:
        A markdown-formatted summary string.
    """
    if len(answers) < MIN_ANSWERS_TO_SUMMARIZE:
        # Short thread: just return the best answer directly
        best = next((a for a in answers if a.get("accepted")), answers[0] if answers else None)
        return best["text"] if best else ""

    # Build a condensed representation of all answers
    answer_block = ""
    for i, ans in enumerate(answers, 1):
        tag = " [ACCEPTED]" if ans.get("accepted") else f" [{ans.get('vote_count', 0)} votes]"
        answer_block += f"\n--- Answer {i}{tag} ---\n{ans['text'][:600]}\n"

    llm = _get_llm()
    response = llm.invoke([
        SystemMessage(content=(
            f"You are a technical assistant. Summarise the following community thread answers "
            f"into: (1) 2-3 key points, (2) the final resolution or recommended approach. "
            f"Be concise and factual. Respond in {language}."
        )),
        HumanMessage(content=f"Thread: {title}\n\n{answer_block}"),
    ])
    return response.content

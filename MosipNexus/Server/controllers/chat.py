"""Chat controller — RAG orchestration for ``/chat`` and ``/batch``.

Keeps FastAPI routes thin: session hydrate → ``ask()`` → persist → stats →
optional low-confidence notify flag.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage

from chain.query_engine import ask
from controllers import sessions as sessions_ctrl
from controllers import stats as stats_ctrl
from errors import BadRequestError, map_llm_exception

logger = logging.getLogger("nexus.chat")


def _require_llm_key(llm_api_key: str | None) -> None:
    if not llm_api_key:
        raise BadRequestError(
            "llm_api_key is required. Provide your own Groq, Anthropic, OpenAI, or xAI Grok API key. "
            "No server-side LLM key is available.",
            code="LLM_KEY_REQUIRED",
        )


def run_chat_turn(
    *,
    question: str,
    session_id: str | None,
    language: str,
    llm_provider: str,
    llm_api_key: str,
    llm_model: str | None = None,
    notify_on_low_confidence: bool = True,
    answer_mode: str | None = None,
    system_prompt: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Run one chat turn and persist it.

    Returns:
        ``(result_dict, should_notify_low_confidence)`` where ``result_dict``
        includes ``session_id`` plus ask() fields.
    """
    _require_llm_key(llm_api_key)
    sid = sessions_ctrl.ensure_session(session_id)
    memory = sessions_ctrl.get_memory(sid)
    logger.info(
        "chat turn session=%s provider=%s lang=%s mode=%s q_len=%d history=%d",
        sid,
        llm_provider,
        language,
        answer_mode or "(product default)",
        len(question or ""),
        len(memory.messages),
    )

    try:
        result = ask(
            question,
            memory.messages,
            language,
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            answer_mode=answer_mode,
            system_prompt=system_prompt,
        )
    except Exception as e:
        logger.exception("RAG ask failed session=%s", sid)
        raise map_llm_exception(e) from e

    logger.info(
        "chat turn done session=%s confidence=%s source_type=%s sources=%d tokens=%s",
        sid,
        result.get("confidence"),
        result.get("source_type"),
        len(result.get("sources") or []),
        (result.get("token_usage") or {}).get("total_tokens"),
    )

    sessions_ctrl.add_turn(
        sid,
        question=question,
        answer=result["answer"],
        sources=result.get("sources", []),
        source_type=result["source_type"],
        confidence=result["confidence"],
        similar_questions=result.get("similar_questions", []),
        language=language,
        token_usage=result.get("token_usage") or {},
    )
    stats_ctrl.record_query(result, language, session_id=sid)

    confidence = result.get("confidence", "")
    source_type = result.get("source_type", "")
    should_notify = bool(
        notify_on_low_confidence
        and confidence == "low"
        and source_type not in ("none", "chat", "web", "n/a", "llm")
    )

    payload = {**result, "session_id": sid}
    return payload, should_notify


def run_batch(
    *,
    questions: list[str],
    session_id: str | None,
    language: str,
    llm_provider: str,
    llm_api_key: str,
    llm_model: str | None = None,
    answer_mode: str | None = None,
    system_prompt: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Answer multiple questions in one session.

    Returns:
        ``(session_id, list_of_result_dicts)`` each result includes ask() fields
        and ``session_id``.
    """
    _require_llm_key(llm_api_key)
    sid = sessions_ctrl.ensure_session(session_id)
    memory = sessions_ctrl.get_memory(sid)
    logger.info(
        "batch start session=%s questions=%d provider=%s mode=%s",
        sid,
        len(questions),
        llm_provider,
        answer_mode or "(product default)",
    )

    temp_messages = list(memory.messages)
    raw_results: list[tuple[str, dict]] = []

    for i, question in enumerate(questions):
        try:
            result = ask(
                question,
                temp_messages,
                language,
                llm_provider=llm_provider,
                llm_api_key=llm_api_key,
                llm_model=llm_model,
                answer_mode=answer_mode,
                system_prompt=system_prompt,
            )
        except Exception as e:
            logger.exception("RAG ask failed in batch index=%d session=%s", i, sid)
            raise map_llm_exception(e) from e
        raw_results.append((question, result))
        temp_messages = [
            *temp_messages,
            HumanMessage(content=question),
            AIMessage(content=result["answer"]),
        ]

    payloads: list[dict[str, Any]] = []
    for question, result in raw_results:
        sessions_ctrl.add_turn(
            sid,
            question=question,
            answer=result["answer"],
            sources=result.get("sources", []),
            source_type=result["source_type"],
            confidence=result["confidence"],
            similar_questions=result.get("similar_questions", []),
            language=language,
            token_usage=result.get("token_usage") or {},
        )
        stats_ctrl.record_query(result, language, session_id=sid)
        payloads.append({**result, "session_id": sid})

    logger.info("batch done session=%s total=%d", sid, len(payloads))
    return sid, payloads


def queue_low_confidence_notify(
    add_task: Callable[..., None],
    *,
    question: str,
    language: str,
    source_type: str,
) -> None:
    """Schedule low-confidence SMTP notify via FastAPI BackgroundTasks.add_task."""
    from notifications.email_notifier import send_low_confidence_notification

    add_task(
        send_low_confidence_notification,
        question=question,
        language=language,
        source_type=source_type,
    )

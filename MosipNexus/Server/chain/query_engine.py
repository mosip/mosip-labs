"""
Query Engine — the core RAG chain.

Pipeline for each user question:
  1. Pure greeting / meta → template reply (no LLM — BYOK-friendly).
  2. Optionally condense follow-ups (skipped when the question looks standalone).
  3. Retrieve top-K chunks from pgvector collections via MMR.
  4. Pack context under MAX_CONTEXT_CHARS / MAX_CONTEXT_DOCS.
  5. Generate answer with a lean system prompt + trimmed history.
  6. [NO_DOC_SOURCE] / empty retrieval → capped DuckDuckGo web fallback.

Token usage is tracked via LangChain usage callbacks and returned to the UI.
"""

from __future__ import annotations

import re
import sys
import logging
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.products import current_product, normalize_answer_mode
from config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_MAX_HISTORY_CHARS,
    LLM_MAX_HISTORY_MESSAGES,
    LLM_MAX_OUTPUT_TOKENS,
    MAX_CONTEXT_CHARS,
    MAX_CONTEXT_DOCS,
    MAX_WEB_CONTEXT_CHARS,
    WEB_SEARCH_MAX_RESULTS,
)
from chain.context_budget import needs_condense, pack_context, trim_history
from retrieval.retriever import (
    is_code_query as query_looks_like_code,
    is_error_code_query as query_has_error_code,
    retrieve,
)


logger = logging.getLogger("nexus.rag")

# Detects "works locally but fails in hosted/staging/synergy/production" debugging questions.
# These require a fundamentally different answer shape: focus on environmental differences,
# not generic troubleshooting steps.
_ENV_DEBUG_RE = re.compile(
    r"work(?:s|ed|ing)?\s+(?:fine\s+)?(?:locally|local|on\s+local)|"
    r"local(?:ly)?\s+(?:it\s+)?work(?:s|ed)|"
    r"(?:synergy|hosted|production|staging|remote)\s+(?:env(?:ironment)?|setup)",
    re.IGNORECASE,
)

_llm: ChatGroq | None = None
_condenser = None


def build_llm(
    provider: str = "groq",
    api_key: str | None = None,
    model: str | None = None,
) -> BaseChatModel:
    """Factory — returns a chat model for the given provider and key.

    ``api_key`` is required for all providers on user-facing paths. For internal
    backend use (ingestion, summarizer) the server's ``GROQ_API_KEY`` is used as
    fallback; user-facing ``ask()`` enforces BYOK before reaching here.

    Args:
        provider: ``groq`` | ``anthropic`` | ``openai`` | ``xai`` | ``grok``.
        api_key: Provider API key (BYOK for chat).
        model: Optional model id override.

    Returns:
        A LangChain ``BaseChatModel`` instance with ``LLM_MAX_OUTPUT_TOKENS`` capped.
    """
    max_out = max(256, LLM_MAX_OUTPUT_TOKENS)
    key = (provider or "groq").strip().lower()
    if key == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or "claude-haiku-4-5-20251001",
            api_key=api_key,  # type: ignore[arg-type]
            max_tokens=max_out,
        )
    if key == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key,  # type: ignore[arg-type]
            max_tokens=max_out,
        )
    if key in ("xai", "grok"):
        # xAI Grok — OpenAI-compatible API
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "grok-3-mini",
            api_key=api_key,  # type: ignore[arg-type]
            base_url="https://api.x.ai/v1",
            max_tokens=max_out,
        )
    # groq — api_key required for user queries; backend falls back to server key
    return ChatGroq(
        model=model or GROQ_MODEL,
        api_key=api_key or GROQ_API_KEY,
        max_tokens=max_out,
    )


_NO_LLM_RESPONSE: dict = {
    "answer": (
        "⚙️ **No LLM configured.**\n\n"
        "To use the web interface, go to **⚙️ Settings** (sidebar) and enter your own "
        "API key for Claude (Anthropic), OpenAI, Groq, or xAI Grok.\n\n"
        "Alternatively, use **Claude Desktop** with the MCP integration — "
        "no API key needed, queries run on your own Claude subscription."
    ),
    "sources": [],
    "source_type": "none",
    "confidence": "n/a",
    "similar_questions": [],
}

_GREETINGS = {
    "hi", "hello", "hey", "hola", "bonjour", "namaste", "vanakkam",
    "ciao", "hallo", "salut", "ola", "howdy", "sup", "yo",
    "good morning", "good afternoon", "good evening", "good night",
    "thanks", "thank you", "bye", "goodbye", "ok", "okay", "great",
}

_META_QUESTION_PHRASES = [
    "knowledge source", "knowledge base", "what sources", "what data",
    "what do you know", "what can you help", "what can you do",
    "who are you", "what are you", "tell me about yourself",
    "how do you work", "how does this work", "what information do you have",
    "what topics", "what are your capabilities", "what can i ask",
]

_META_ANSWER_TMPL = """\
I am **{name}** — an AI assistant with deep knowledge of the {short} \
ecosystem. My knowledge comes from documentation, community forum threads, \
GitHub issues, Confluence (when indexed), and source code for {short}.

You can ask about architecture, configuration, deployment, error codes, \
APIs, and integration. I support questions in any language.\
"""

_NO_SOURCE_MARKER = "[NO_DOC_SOURCE]"


_CONDENSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Given the conversation history and the latest question, rewrite the question "
     "as a standalone search query that captures all necessary context. "
     "Return ONLY the rewritten question, nothing else."),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])


def _build() -> None:
    global _llm, _condenser
    _llm = build_llm()
    _condenser = _CONDENSE_PROMPT | _llm | StrOutputParser()


def _get_llm() -> BaseChatModel:
    if _llm is None:
        _build()
    assert _llm is not None
    return _llm


def _web_search(query: str, max_results: int | None = None) -> list[dict]:
    """Search DuckDuckGo and return result dicts with href, title, body."""
    n = WEB_SEARCH_MAX_RESULTS if max_results is None else max_results
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max(1, n)))
    except Exception:
        return []


def _rate_limit_response() -> dict:
    return {
        "answer": (
            "⚠️ **Groq API rate limit reached.** The free tier allows 100,000 tokens per day. "
            "Please wait a few minutes and try again, or check your usage at "
            "[console.groq.com](https://console.groq.com)."
        ),
        "sources": [],
        "source_type": "none",
        "confidence": "n/a",
        "similar_questions": [],
    }


def _web_fallback_or_none(
    question: str,
    language: str,
    fallback_answer: str | None = None,
    llm: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Try DuckDuckGo when the knowledge base has no usable context.

    Args:
        question: Original user question (used as the web search query).
        language: Response language for the web-synthesis prompt.
        fallback_answer: Optional text to return if web search also fails.
        llm: Required when web hits exist (synthesises the answer).

    Returns:
        Same shape as ``ask()`` with ``source_type`` of ``web`` or ``none``.
    """
    web_hits = _web_search(question)
    if web_hits:
        parts: list[str] = []
        used = 0
        for h in web_hits:
            block = f"[{h.get('title', '')}]({h['href']})\n{(h.get('body') or '')[:500]}"
            if used + len(block) > MAX_WEB_CONTEXT_CHARS:
                break
            parts.append(block)
            used += len(block) + 2
        web_context = "\n\n".join(parts)
        assert llm is not None, "llm must be provided to _web_fallback_or_none"
        web_response = llm.invoke([
            SystemMessage(content=(
                f"Answer using only the web snippets below. Note that this is external "
                f"web content, not official {current_product().short} docs. Cite URLs inline. "
                f"Be concise. Respond in {language}."
            )),
            HumanMessage(content=f"Web results:\n{web_context}\n\nQuestion: {question}"),
        ])
        return {
            "answer":           web_response.content,
            "sources":          [{"source": h["href"], "title": h.get("title", "")} for h in web_hits],
            "source_type":      "web",
            "confidence":       "medium",
            "similar_questions": [],
        }

    return {
        "answer": fallback_answer or (
            "No relevant results were found on the web for your query."
        ),
        "sources":          [],
        "source_type":      "none",
        "confidence":       "low",
        "similar_questions": [],
    }


def _is_greeting(text: str) -> bool:
    return text.strip().lower().rstrip("!.,?") in _GREETINGS


def _is_meta_question(text: str) -> bool:
    lowered = text.strip().lower()
    return any(phrase in lowered for phrase in _META_QUESTION_PHRASES)


def _starts_with_greeting(text: str) -> bool:
    first = text.strip().lower().split()[0].rstrip("!.,?") if text.strip() else ""
    return first in _GREETINGS


def _greeting_reply(question: str, language: str) -> str:
    """Template greeting — zero LLM tokens (BYOK-friendly)."""
    q = question.strip().lower().rstrip("!.,?")
    if q in ("thanks", "thank you"):
        return "You're welcome! Ask anytime if you have more questions."
    if q in ("bye", "goodbye"):
        return "Goodbye! Come back anytime with more questions."
    if q in ("ok", "okay", "great"):
        return f"Sounds good — what would you like to know about {current_product().short}?"
    lang_note = (
        f" I'll answer in **{language}**."
        if language and language.lower() not in ("english", "en")
        else ""
    )
    return (
        f"Hello! I'm **{current_product().name}** — ask me anything about "
        f"{current_product().short} docs, community, GitHub issues, or source code.{lang_note}"
    )


def _build_system_prompt(
    language: str,
    has_greeting: bool,
    is_error_query: bool = False,
    is_code_query: bool = False,
    is_env_debug: bool = False,
) -> str:
    """Build a lean system prompt for one RAG turn (token-conscious for BYOK)."""
    greeting_rule = (
        "Open with one short greeting sentence, then answer.\n"
        if has_greeting else ""
    )
    if is_env_debug:
        answer_format = (
            "Env-debug: local works, hosted fails. Focus on env differences "
            "(versions, credentials, network, config). Treat 401/500 as HTTP status, "
            "not MOSIP error codes. Cite community threads if present; say if unresolved.\n"
        )
        if is_error_query:
            answer_format += (
                "Also quote the exact MOSIP error constant; flag %s/%d as runtime placeholders.\n"
            )
    elif is_error_query:
        answer_format = (
            "Error-code answer — you MUST synthesise ALL source types present in context "
            "(source code + docs + community + GitHub issues). Structure your answer:\n"
            "1. **What it is** — exact constant name and raw message template; "
            "quote %s/%d as-is, never substitute invented values.\n"
            "2. **Where it occurs** — which API endpoint or service raises this "
            "(e.g. /idauthentication/v1/auth/, Registration Client, Resident Services). "
            "If context does not name the endpoint, reason from the module prefix: "
            "IDA-* → IDA authentication endpoints, REG-* → Registration Client, "
            "RES-* → Resident Services, PMS-* → Partner Management.\n"
            "3. **What the placeholder resolves to** — IMPORTANT: first read the constant "
            "NAME itself to identify what %s represents (e.g. '%s Auth Type is Locked' → "
            "%s is an auth type such as Fingerprint/Iris/Face/OTP/Demo). Only fall back to "
            "'depends on the caller' if the constant name gives no clue and context is silent.\n"
            "4. **Why it happens** — root causes from docs/community in context "
            "(e.g. too many failed attempts triggering a lock policy, admin action, "
            "ID not registered, deactivated, wrong env, DB unavailable, missing mapping).\n"
            "5. **How to fix it** — give the OPERATIONAL fix, not a restatement of the "
            "problem. State WHO must act (admin, partner, caller) and HOW "
            "(e.g. unlock via Partner Management portal / admin API, correct the request "
            "field, check DB state, update config). If context lacks specifics, "
            "say what to investigate, not just 'ensure X is not Y'.\n"
            "6. **Related codes** — if context contains sibling error codes for the same "
            "module, contrast them briefly.\n"
            "Skip any section that has no supporting context — do not invent. "
            "Cite [ACCEPTED ANSWER] threads and exact file/class names when present.\n"
        )
    elif is_code_query:
        answer_format = (
            "Code answer: name exact class/file from context; note package; key methods; "
            "flag demo/test/sample packages explicitly vs production.\n"
        )
    else:
        answer_format = (
            "Match format to the question (definition / steps / comparison). Be direct.\n"
        )
    product = current_product()
    return (
        f"You are a senior {product.short} engineer. Answer from the retrieved context only.\n"
        f"{answer_format}"
        f"RULES:\n"
        f"{greeting_rule}"
        f"- Do NOT invent class names, commands, repos, config keys, or paths — "
        f"only use strings that appear in the context. If missing, say so briefly.\n"
        f"- No hedging ('refer to the docs', 'may vary', 'I would need more info'). "
        f"Give one concrete answer; cite [ACCEPTED ANSWER] / GitHub / file names when present.\n"
        f"- Output {_NO_SOURCE_MARKER} only if the question is unrelated to {product.short}.\n"
        f"- Respond in {language}. Keep the answer concise but complete.\n\n"
        f"Context:\n{{context}}"
    )


def _direct_system_prompt(
    language: str,
    *,
    custom_system_prompt: str | None = None,
) -> str:
    """System prompt for BYOK direct (non-RAG) answers."""
    product = current_product()
    if custom_system_prompt and custom_system_prompt.strip():
        base = custom_system_prompt.strip()
        return f"{base}\n\nRespond in {language}."
    return (
        f"You are {product.name}, a helpful AI assistant ({product.short}). "
        f"Answer the user's question clearly and accurately using your knowledge. "
        f"If you are unsure, say so. Respond in {language}."
    )


def _ask_direct(
    question: str,
    history_for_llm: list,
    language: str,
    llm: BaseChatModel,
    *,
    system_prompt: str | None = None,
    started: float,
) -> dict[str, Any]:
    """BYOK LLM-only path — no vector retrieval, no docs URLs required."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _direct_system_prompt(language, custom_system_prompt=system_prompt)),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    chain = prompt | llm | StrOutputParser()
    try:
        answer = chain.invoke({"input": question, "chat_history": history_for_llm})
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            return _rate_limit_response()
        raise
    logger.info(
        "ask done kind=direct source_type=llm confidence=n/a elapsed_ms=%.0f",
        (time.perf_counter() - started) * 1000,
    )
    return {
        "answer": answer,
        "sources": [],
        "source_type": "llm",
        "confidence": "n/a",
        "similar_questions": [],
    }


def ask(
    question: str,
    chat_history: list,
    language: str = "English",
    llm_provider: str = "groq",
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    answer_mode: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Run one chat turn — RAG knowledge base or direct BYOK LLM.

    Args:
        question: Raw user message.
        chat_history: LangChain HumanMessage / AIMessage objects from prior turns.
        language: Human-readable language name for the LLM response language.
        llm_provider: ``groq`` | ``anthropic`` | ``openai`` | ``xai`` | ``grok``.
        llm_api_key: User-supplied API key (BYOK). Required.
        llm_model: Optional model override.
        answer_mode: ``rag`` (retrieve + grounded answer) or ``direct`` (LLM only).
            When omitted, uses the active product's ``default_answer_mode``.
        system_prompt: Optional override for ``direct`` mode (white-label apps).

    Returns:
        Dict with answer, sources, source_type, confidence, similar_questions, token_usage.
    """
    from langchain_core.callbacks import get_usage_metadata_callback

    from chain.token_usage import summarize_usage_metadata

    with get_usage_metadata_callback() as cb:
        result = _ask_impl(
            question,
            chat_history,
            language=language,
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            answer_mode=answer_mode,
            system_prompt=system_prompt,
        )
        usage = summarize_usage_metadata(cb.usage_metadata)
        result["token_usage"] = usage
        logger.info(
            "ask tokens prompt=%s completion=%s total=%s",
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return result


def _ask_impl(
    question: str,
    chat_history: list,
    language: str = "English",
    llm_provider: str = "groq",
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    answer_mode: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Inner chat pipeline (token usage attached by ``ask``)."""
    started = time.perf_counter()
    mode = normalize_answer_mode(answer_mode)
    logger.info(
        "ask start provider=%s model=%s lang=%s mode=%s product=%s q_len=%d history=%d",
        llm_provider,
        llm_model or "(default)",
        language,
        mode,
        current_product().slug,
        len(question or ""),
        len(chat_history or []),
    )

    # Require the user to supply their own API key — no server fallback.
    if not llm_api_key:
        logger.warning("ask rejected — missing llm_api_key")
        return _NO_LLM_RESPONSE

    llm = build_llm(llm_provider, llm_api_key, llm_model)
    history_for_llm = trim_history(
        chat_history,
        max_messages=LLM_MAX_HISTORY_MESSAGES,
        max_chars_per_message=LLM_MAX_HISTORY_CHARS,
    )

    # ── Pure greeting (no LLM — saves BYOK tokens) ─────────────────────────────
    if _is_greeting(question):
        result = {
            "answer": _greeting_reply(question, language),
            "sources": [],
            "source_type": "chat",
            "confidence": "n/a",
            "similar_questions": [],
        }
        logger.info(
            "ask done kind=greeting tokens=0 elapsed_ms=%.0f",
            (time.perf_counter() - started) * 1000,
        )
        return result

    # ── Meta-question (about the system itself) — RAG products only ────────────
    if mode == "rag" and _is_meta_question(question):
        logger.info(
            "ask done kind=meta tokens=0 elapsed_ms=%.0f",
            (time.perf_counter() - started) * 1000,
        )
        return {
            "answer": _META_ANSWER_TMPL.format(
                name=current_product().name,
                short=current_product().short,
            ),
            "sources": [],
            "source_type": "chat",
            "confidence": "n/a",
            "similar_questions": [],
        }

    # ── Web search (DuckDuckGo → LLM synthesis) ────────────────────────────────
    if mode == "web":
        result = _web_fallback_or_none(question, language, llm=llm)
        logger.info(
            "ask done kind=web source_type=%s elapsed_ms=%.0f",
            result.get("source_type"),
            (time.perf_counter() - started) * 1000,
        )
        return result

    # ── Direct BYOK (no retrieval) ─────────────────────────────────────────────
    if mode == "direct":
        return _ask_direct(
            question,
            history_for_llm,
            language,
            llm,
            system_prompt=system_prompt,
            started=started,
        )

    # ── Condense follow-up questions (skip when question looks standalone) ─────
    try:
        if needs_condense(question, history_for_llm):
            condenser = _CONDENSE_PROMPT | llm | StrOutputParser()
            standalone = condenser.invoke(
                {"input": question, "chat_history": history_for_llm}
            )
            logger.debug("ask condensed q_len=%d → %d", len(question), len(standalone or ""))
        else:
            standalone = question
            if chat_history:
                logger.debug("ask skip condense (standalone follow-up heuristic)")
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            return _rate_limit_response()
        raise

    # ── Retrieve from product collections ──────────────────────────────────────
    docs, confidence = retrieve(standalone)
    context = pack_context(
        docs,
        max_chars=MAX_CONTEXT_CHARS,
        max_docs=MAX_CONTEXT_DOCS,
    )
    logger.debug(
        "ask retrieve docs=%d packed_chars=%d confidence=%s elapsed_ms=%.0f",
        len(docs),
        len(context),
        confidence,
        (time.perf_counter() - started) * 1000,
    )

    # No chunks retrieved — return "not available" (no web fallback for RAG products).
    if not docs or not context.strip():
        product = current_product()
        return {
            "answer": f"This information is not available in the {product.short} knowledge sources.",
            "sources": [],
            "source_type": "none",
            "confidence": "low",
            "similar_questions": [],
        }

    # ── Build QA chain ─────────────────────────────────────────────────────────
    has_greeting = _starts_with_greeting(question)
    # Check both original question and condensed form — condensation can strip env signals
    # (e.g. "Synergy environment", "works locally") from a long community-post paste
    is_env_debug   = bool(_ENV_DEBUG_RE.search(question)) or bool(_ENV_DEBUG_RE.search(standalone))
    is_error_query = query_has_error_code(standalone)
    # env_debug + error_query can both be true (e.g. "IDA-MLC-009 in Synergy, works locally")
    # env_debug takes format priority but error_query rules still apply inside that format.
    # code_query is mutually exclusive with both since code analysis ≠ debugging/error context.
    is_code_query  = not is_error_query and not is_env_debug and query_looks_like_code(standalone)
    sys_prompt = _build_system_prompt(
        language, has_greeting,
        is_error_query=is_error_query,
        is_code_query=is_code_query,
        is_env_debug=is_env_debug,
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", sys_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    qa_chain = qa_prompt | llm | StrOutputParser()

    try:
        answer = qa_chain.invoke({
            "input":        question,
            "chat_history": history_for_llm,
            "context":      context,
        })
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            return _rate_limit_response()
        raise

    # ── Confidence override — downgrade when LLM admits info wasn't found ────────
    _NOT_FOUND_PHRASES = (
        "not in the available documentation",
        "not available in the",
        "not in the context",
        "is not available in",
        "cannot find",
        "not found in",
        "no information available",
        "not provided in",
        "not mentioned in",
    )
    if any(p in answer.lower() for p in _NOT_FOUND_PHRASES):
        confidence = "low"

    # ── [NO_DOC_SOURCE] → not available in this product's knowledge base ────────
    if _NO_SOURCE_MARKER in answer:
        clean = answer.replace(_NO_SOURCE_MARKER, "").strip()
        product = current_product()
        logger.info("ask done kind=no_source elapsed_ms=%.0f", (time.perf_counter() - started) * 1000)
        return {
            "answer": clean or f"This information is not available in the {product.short} knowledge sources.",
            "sources": [],
            "source_type": "none",
            "confidence": "low",
            "similar_questions": [],
        }

    # ── Classify sources ───────────────────────────────────────────────────────
    source_types = {d.metadata.get("source_type", "") for d in docs}
    if source_types == {"docs"}:
        source_type = "mosip_docs"
    elif source_types == {"community"}:
        source_type = "community"
    elif source_types == {"github"}:
        source_type = "github"
    elif source_types == {"code"}:
        source_type = "code"
    elif source_types == {"confluence"}:
        source_type = "confluence"
    elif source_types == {"jira"}:
        source_type = "jira"
    else:
        source_type = "mixed"

    # Show top 2 per collection — enough for attribution without overwhelming the user
    _by_type: dict[str, list] = {}
    for d in docs:
        t = d.metadata.get("source_type", "other")
        _by_type.setdefault(t, []).append(d.metadata)

    # Remove doc URLs that are ancestors of a more specific URL already in the list
    # e.g. drop /identity-verification when /identity-verification/id-authentication is present
    _doc_candidates = _by_type.get("docs", [])[:2]
    _doc_urls = [m.get("source", "") for m in _doc_candidates]
    _doc_filtered = [
        m for m in _doc_candidates
        if not any(
            other != m.get("source", "") and other.startswith(m.get("source", "") + "/")
            for other in _doc_urls
        )
    ]

    sources = (
        _doc_filtered +
        _by_type.get("community", [])[:2] +
        _by_type.get("github", [])[:1] +
        _by_type.get("code", [])[:1] +
        _by_type.get("confluence", [])[:1]
    )

    # ── Similar questions (community titles in the results) ────────────────────
    similar_questions = list({
        d.metadata.get("title", "")
        for d in docs
        if d.metadata.get("source_type") == "community" and d.metadata.get("title")
    })[:3]

    result = {
        "answer": answer,
        "sources": sources,
        "source_type": source_type,
        "confidence": confidence,
        "similar_questions": similar_questions,
    }
    logger.info(
        "ask done kind=rag source_type=%s confidence=%s sources=%d elapsed_ms=%.0f",
        source_type,
        confidence,
        len(sources),
        (time.perf_counter() - started) * 1000,
    )
    return result

"""
Query Engine — the core RAG chain.

Pipeline for each user question:
  1. Pure greeting → direct friendly reply (no RAG).
  2. Message starting with greeting → RAG answer prefixed with a brief greeting.
  3. Condense follow-up questions using chat history (LCEL condenser chain).
  4. Retrieve top-K chunks from all pgvector collections via MMR.
  5. Score confidence from the best chunk's cosine distance.
  6. Generate answer grounded strictly in context (Groq Llama 3.3).
  7. If retrieved context is irrelevant → emit [NO_DOC_SOURCE] marker.
  8. [NO_DOC_SOURCE] path → DuckDuckGo web search fallback.
  9. If web search also fails → source_type="none" (UI shows escalation options).

LangSmith tracing is activated automatically when LANGCHAIN_TRACING_V2=true
and LANGCHAIN_API_KEY are set in the environment — no code changes needed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import GROQ_API_KEY, GROQ_MODEL
from retrieval.retriever import retrieve, _ERROR_CODE_RE, _CODE_QUERY_RE

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

    api_key is required for all providers. For internal backend use (ingestion,
    summarizer) the server's GROQ_API_KEY is used as fallback; user-facing
    ask() enforces BYOK before reaching here.
    """
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or "claude-haiku-4-5-20251001",
            api_key=api_key,  # type: ignore[arg-type]
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key,  # type: ignore[arg-type]
        )
    # groq — api_key required for user queries; backend falls back to server key
    return ChatGroq(
        model=model or GROQ_MODEL,
        api_key=api_key or GROQ_API_KEY,
    )


_NO_LLM_RESPONSE: dict = {
    "answer": (
        "⚙️ **No LLM configured.**\n\n"
        "To use the web interface, go to **⚙️ Settings** (sidebar) and enter your own "
        "API key for Claude (Anthropic), OpenAI, or Groq.\n\n"
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

_META_ANSWER = """\
I am **MOSIP Nexus** — an AI assistant with deep knowledge of the MOSIP \
(Modular Open Source Identity Platform) ecosystem. My knowledge comes from \
five sources:

1. **MOSIP Documentation** — all 449 pages from docs.mosip.io/1.2.0 \
(architecture, modules, deployment guides, APIs)
2. **Community Forum** — Q&A threads from community.mosip.io, prioritising \
accepted answers and highly-voted replies
3. **GitHub Issues** — issues and discussions from 25 active MOSIP \
repositories
4. **Confluence** — internal Confluence spaces covering engineering, QA, \
and product management
5. **MOSIP Source Code** — Java, YAML, SQL, XML, and properties files \
from 71 MOSIP repositories (error constants, service implementations, \
controllers, schemas)

You can ask me anything about MOSIP modules (IDA, Registration, Resident \
Services, Partner Management, Key Manager, Admin UI), error codes, \
configuration, deployment, or integration. I support questions in any \
language.\
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


def _web_search(query: str, max_results: int = 4) -> list[dict]:
    """Search DuckDuckGo and return result dicts with href, title, body."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
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
    """Try a web search when the knowledge base has no usable context; otherwise
    return a plain "not available" response instead of letting the LLM guess."""
    web_hits = _web_search(question)
    if web_hits:
        web_context = "\n\n".join(
            f"[{h.get('title', '')}]({h['href']})\n{h['body']}"
            for h in web_hits
        )
        assert llm is not None, "llm must be provided to _web_fallback_or_none"
        web_response = llm.invoke([
            SystemMessage(content=(
                f"You are a helpful assistant. The MOSIP knowledge base did not have "
                f"the answer. Use the web search results below to answer the question. "
                f"Cite source URLs inline. Begin by noting this comes from external web "
                f"sources, not MOSIP documentation. Respond in {language}."
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
            "This information is not available in the MOSIP knowledge sources."
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


def _build_system_prompt(
    language: str,
    has_greeting: bool,
    is_error_query: bool = False,
    is_code_query: bool = False,
    is_env_debug: bool = False,
) -> str:
    """Build the system prompt for one RAG turn.

    is_env_debug and is_error_query can both be true simultaneously
    (e.g. an error code that only appears in a hosted environment).
    In that case env_debug takes format priority and error rules are appended.
    """
    greeting_rule = (
        "Start with one warm sentence acknowledging the greeting, then answer directly.\n"
        if has_greeting else ""
    )
    if is_env_debug:
        answer_format = (
            "This is an environment-comparison debugging question — the user says the same thing "
            "works locally but fails in a hosted/remote environment (Synergy, production, staging, etc.). "
            "Structure your answer as:\n"
            "  1. Confirm the key insight: the biometric data / request payload itself is NOT the problem "
            "(it works locally). The failure is in the hosted environment's configuration or version.\n"
            "  2. IMPORTANT — do NOT treat HTTP status codes (401, 500, 403, etc.) as MOSIP error codes "
            "(like IDA-MLC-009 or KER-ATH-401). In this context, 401 means the hosted service returned "
            "HTTP 401 Unauthorized, and 500 means the hosted service threw an internal error. "
            "Treat them as HTTP-level responses from that specific service (BQAT, SBI, biosdk-service, etc.).\n"
            "  3. List what differs between local and hosted environments — focus on: "
            "version/image tag mismatch, credential or API key requirements in the hosted env, "
            "network policies or IP allowlists, config drift in values.yaml or application.properties.\n"
            "  4. Give specific next steps to narrow down which env difference is causing it. "
            "For 401 from a remote service: check whether the hosted service requires auth headers "
            "the local Docker image does not. "
            "For 500 from a remote service: check the hosted service pod logs for the actual stack trace.\n"
            "  5. If the retrieved context includes community threads about this exact issue, "
            "cite them by name. If those threads have no accepted answer, say so explicitly — "
            "do not invent a resolution that isn't in the context.\n\n"
        )
        if is_error_query:
            answer_format += (
                "Additionally, this query references a specific MOSIP error code — "
                "apply the error code rules: quote the exact constant, flag %s/%d as "
                "runtime placeholders, and compare sibling error codes if present.\n\n"
            )
    elif is_error_query:
        answer_format = (
            "For this error code question, structure your answer as:\n"
            "  1. Exact error definition — quote the constant from source code if available. "
            "CRITICAL: if the message contains %s, %d, or any Java format specifier, state "
            "explicitly that this is a runtime placeholder substituted with the actual offending "
            "value in the API response. NEVER replace %s with a specific example value and present "
            "it as the definition. Tell the user to read their actual error response to see what "
            "field name was substituted.\n"
            "  2. How this differs from sibling error codes in the same file — e.g. 'missing' vs "
            "'present but invalid' — if sibling constants appear in the retrieved context.\n"
            "  3. Most likely root causes specific to this error, ranked by likelihood. "
            "Do NOT list generic causes that apply to any error — only causes grounded in the "
            "retrieved context or in how this specific constant is used in the codebase.\n"
            "  4. Step-by-step resolution — first step MUST be: check your actual error response "
            "for the substituted field name (%s value), since that tells you exactly which "
            "parameter is failing.\n"
            "  5. How to verify the fix worked.\n\n"
        )
    elif is_code_query:
        answer_format = (
            "For this code/class question:\n"
            "  - Name the exact class(es) or file(s) from the retrieved context directly and immediately.\n"
            "  - State what the class does and which package/module it belongs to.\n"
            "  - Mention key methods if they are in the context.\n"
            "  - If multiple classes share the responsibility, list them in order of importance.\n"
            "  - If the exact class is not in the context, name the closest class you CAN identify "
            "and clearly state what aspect of the question it covers.\n"
            "  - CRITICAL: if the only matching class in the retrieved context is from a demo, "
            "test, sample, mock, or simulator package (e.g. io.mosip.*.demo.*, SampleSDK, "
            "DemoService), you MUST state explicitly: 'This class is from the demo/test "
            "application, NOT the production implementation.' Then describe what the production "
            "class likely does based on the pattern, but make clear the exact production class "
            "name is not in the available context.\n\n"
        )
    else:
        answer_format = (
            "Match your answer format to the question type — definitions get clear explanations, "
            "how-to questions get numbered steps, comparisons get bullet lists. "
            "Don't force a fixed structure onto every answer.\n\n"
        )
    return (
        f"You are a senior MOSIP (Modular Open Source Identity Platform) engineer and "
        f"first-level support expert. You have deep hands-on knowledge of all MOSIP modules: "
        f"ID Authentication (IDA), Registration Client, Registration Processor, Resident Services, "
        f"Partner Management, Key Manager, Admin UI, and the full Kubernetes deployment stack.\n\n"
        f"Answer like a knowledgeable colleague responding in a Slack channel — direct, complete, "
        f"actionable. You ARE the expert. Never say 'consult the documentation', "
        f"'check the forums', or 'contact the MOSIP team'.\n\n"
        f"{answer_format}"
        f"RULE #1 — FABRICATION IS FORBIDDEN (read this before anything else):\n"
        f"Every class name, method name, CLI command, Helm chart name, repository name, "
        f"configuration key, file path, and API endpoint you write MUST appear word-for-word "
        f"in the retrieved context below. If it is not in the context, do NOT write it. "
        f"Do not guess. Do not complete a plausible-sounding name. Do not write 'HelmInstaller', "
        f"'installChart', 'mosip/mosip-id-auth', or any other specific name unless those exact "
        f"strings appear in the retrieved context. When the specific name is absent, say so — "
        f"e.g. 'the exact class/command is not in the available documentation' — then explain "
        f"the concept or point to the repository where the user can find it. "
        f"A vague but honest answer is far more valuable than a detailed but fabricated one. "
        f"Contributors who follow fabricated class names or commands lose hours of work.\n\n"
        f"STRICT RULES — violating these makes the answer useless:\n"
        f"{greeting_rule}"
        f"- NEVER end with or add a 'Note:' or 'Note that' sentence. NEVER use hedging phrases: "
        f"'it appears that', 'may be involved', 'it is possible that', "
        f"'I would need more information', 'cannot determine without more context', "
        f"'would need to review the codebase', 'more information is required', "
        f"'the exact answer depends on', 'these steps may vary', 'may vary depending on', "
        f"'may vary depending on the version', 'the actual requirements may vary', "
        f"'the specific configuration settings and classes may vary', "
        f"'depending on the specific implementation', 'depending on your setup', "
        f"'depending on the version of MOSIP', 'depending on the specific version', "
        f"'refer to the MOSIP documentation', 'refer to the documentation', "
        f"'it is recommended to refer', 'consult the documentation', 'check the documentation'. "
        f"State what you know directly. If something varies by version, name the version you are "
        f"describing and stop — do not add a trailing disclaimer.\n"
        f"- Give ONE concrete answer first. Then add caveats only if essential.\n"
        f"- If the retrieved context gives conflicting version numbers or specs, pick the most "
        f"specific/conservative value and state it clearly — do NOT list both and confuse the reader.\n"
        f"- Synthesize all retrieved context into a complete, useful answer.\n"
        f"- Do NOT start with 'According to the documentation' or similar phrases.\n"
        f"- If partial information is all you have, give that information clearly and tell the user "
        f"specifically what log entry, config key, or environment detail would confirm the rest — "
        f"never stop at 'I don't have enough information'.\n"
        f"- Prioritise content marked [ACCEPTED ANSWER] — these are verified solutions.\n"
        f"- GitHub Issues in the context show real error reports with real solutions — use them.\n"
        f"- When source code file names appear in context, cite them by name and explain their role.\n"
        f"- When community threads appear in the context about the same issue as the query, "
        f"ALWAYS cite them explicitly by their exact title from the context. "
        f"If the thread contains a resolution or ACCEPTED ANSWER, summarise it. "
        f"If the thread has no accepted answer, say so explicitly — "
        f"this signals an unresolved known issue the user should follow or escalate.\n"
        f"- ONLY output {_NO_SOURCE_MARKER} at the very start if the question is completely "
        f"unrelated to MOSIP (e.g. weather, sports, general coding unrelated to MOSIP). "
        f"For any MOSIP question — even with limited context — give your best answer.\n"
        f"- Always respond in {language}. This is mandatory.\n\n"
        f"Retrieved context (your primary source — use it fully):\n{{context}}"
    )


def ask(
    question: str,
    chat_history: list,
    language: str = "English",
    llm_provider: str = "groq",
    llm_api_key: str | None = None,
    llm_model: str | None = None,
) -> dict[str, Any]:
    """Run the full RAG pipeline for one user turn.

    Args:
        question:     Raw user message.
        chat_history: LangChain HumanMessage / AIMessage objects from prior turns.
        language:     Human-readable language name for the LLM response language.
        llm_provider: "groq" | "anthropic" | "openai" — defaults to server Groq key.
        llm_api_key:  User-supplied API key (BYOK); None uses server default.
        llm_model:    Optional model override (e.g. "claude-haiku-4-5-20251001").

    Returns:
        answer      (str):       generated response text.
        sources     (list[dict]): metadata of retrieved chunks; empty for chat/no-source.
        source_type (str):       "mosip_docs" | "community" | "mixed" | "chat" | "none".
        confidence  (str):       "high" | "medium" | "low" | "n/a".
        similar_questions (list[str]): titles of related community threads (may be empty).
    """
    # Require the user to supply their own API key — no server fallback.
    if not llm_api_key:
        return _NO_LLM_RESPONSE

    llm = build_llm(llm_provider, llm_api_key, llm_model)
    condenser = _CONDENSE_PROMPT | llm | StrOutputParser()

    # ── Pure greeting ──────────────────────────────────────────────────────────
    if _is_greeting(question):
        response = llm.invoke([
            SystemMessage(content=(
                f"You are a friendly MOSIP assistant. Respond naturally to the greeting "
                f"in {language} and invite the user to ask about MOSIP."
            )),
            HumanMessage(content=question),
        ])
        return {
            "answer": response.content,
            "sources": [],
            "source_type": "chat",
            "confidence": "n/a",
            "similar_questions": [],
        }

    # ── Meta-question (about the system itself) ────────────────────────────────
    if _is_meta_question(question):
        return {
            "answer": _META_ANSWER,
            "sources": [],
            "source_type": "chat",
            "confidence": "n/a",
            "similar_questions": [],
        }

    # ── Condense follow-up questions ───────────────────────────────────────────
    try:
        standalone = (
            condenser.invoke({"input": question, "chat_history": chat_history})
            if chat_history
            else question
        )
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            return _rate_limit_response()
        raise

    # ── Retrieve from both collections ─────────────────────────────────────────
    docs, confidence = retrieve(standalone)
    context = "\n\n".join(d.page_content for d in docs)

    # No chunks retrieved at all — don't let the LLM guess from pretrained
    # knowledge, go straight to the same web-fallback path as [NO_DOC_SOURCE].
    if not docs:
        return _web_fallback_or_none(question, language, llm=llm)

    # ── Build QA chain ─────────────────────────────────────────────────────────
    has_greeting = _starts_with_greeting(question)
    # Check both original question and condensed form — condensation can strip env signals
    # (e.g. "Synergy environment", "works locally") from a long community-post paste
    is_env_debug   = bool(_ENV_DEBUG_RE.search(question)) or bool(_ENV_DEBUG_RE.search(standalone))
    is_error_query = bool(_ERROR_CODE_RE.search(standalone))
    # env_debug + error_query can both be true (e.g. "IDA-MLC-009 in Synergy, works locally")
    # env_debug takes format priority but error_query rules still apply inside that format.
    # code_query is mutually exclusive with both since code analysis ≠ debugging/error context.
    is_code_query  = not is_error_query and not is_env_debug and bool(_CODE_QUERY_RE.search(standalone))
    system_prompt = _build_system_prompt(
        language, has_greeting,
        is_error_query=is_error_query,
        is_code_query=is_code_query,
        is_env_debug=is_env_debug,
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    qa_chain = qa_prompt | llm | StrOutputParser()

    try:
        answer = qa_chain.invoke({
            "input":        question,
            "chat_history": chat_history,
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

    # ── [NO_DOC_SOURCE] → try DuckDuckGo web search fallback ─────────────────
    if _NO_SOURCE_MARKER in answer:
        fallback_answer = answer.replace(_NO_SOURCE_MARKER, "").lstrip()
        return _web_fallback_or_none(question, language, fallback_answer, llm=llm)

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

    return {
        "answer": answer,
        "sources": sources,
        "source_type": source_type,
        "confidence": confidence,
        "similar_questions": similar_questions,
    }

"""System-level semantic answer cache — the actual token-saving layer.

Confidence scoring (``chain.confidence``) only changes how much an answer is
*trusted*; it never skipped a generation call. This module does: a
near-duplicate question gets served a previously-generated high-confidence
answer instead of a fresh LLM call. Scoped per product, shared across every
user/session (not per-user) — the first person to ask a question pays the
LLM cost, everyone after with a near-duplicate question gets it for free.

Trust is re-checked at serve time via ``chain.confidence.scorer.mean_final_score``
against the cached answer's own ``chunk_ids`` — so negative feedback recorded
by ANY later question naturally stops a stale/bad cached answer from being
served again, with no separate cache-invalidation step required.

PRIVACY: sharing across every user/session is exactly what makes this global,
cross-user store risky — there's no user/tenant scoping anywhere in this
codebase, so a question containing personal or deployment-specific detail
could be served back to an unrelated user later. See the
``ANSWER_CACHE_ENABLED`` comment in ``config/settings.py`` (defaults off) and
the ``was_condensed`` gating in ``chain/query_engine.py`` before changing
either — this file alone does not decide whether caching is safe to run.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from langchain_core.documents import Document
from langchain_postgres import PGVector

from config.settings import (
    ANSWER_CACHE_CANDIDATES,
    ANSWER_CACHE_MAX_AGE_DAYS,
    ANSWER_CACHE_MIN_TRUST,
    ANSWER_CACHE_SIMILARITY,
)
from db.engine import get_engine
from chain.confidence.scorer import mean_final_score, record_retrieval

logger = logging.getLogger("nexus.answer_cache")

_stores: dict[str, PGVector] = {}
_build_lock = threading.Lock()


def _collection_name(product_slug: str) -> str:
    return f"{product_slug}_answer_cache"


def _get_store(product_slug: str) -> PGVector:
    cached = _stores.get(product_slug)
    if cached is not None:
        return cached
    with _build_lock:
        cached = _stores.get(product_slug)
        if cached is not None:
            return cached
        from retrieval.retriever import get_embeddings

        store = PGVector(
            embeddings=get_embeddings(),
            connection=get_engine(),
            collection_name=_collection_name(product_slug),
        )
        _stores[product_slug] = store
        return store


def _delete_entry(product_slug: str, doc_id: str | None) -> None:
    """Best-effort removal of a confirmed-invalid cache row.

    Only called for entries we've positively identified as expired or fallen
    below the trust floor — not for "never scored yet", which isn't evidence
    of a bad entry. Keeps the collection from accumulating dead rows that
    would otherwise sit there indefinitely (no separate cleanup job exists).
    """
    if not doc_id:
        return
    try:
        _get_store(product_slug).delete(ids=[doc_id])
    except Exception:
        logger.exception("Failed to delete stale answer cache entry")


def _validate_candidate(doc: Document, similarity: float, product_slug: str) -> dict | None:
    """Check one candidate; return a serve-ready result, or None if it's not usable."""
    if similarity < ANSWER_CACHE_SIMILARITY:
        return None

    meta = doc.metadata or {}
    try:
        cached_at = datetime.fromisoformat(meta.get("cached_at", ""))
        age_days = (datetime.now(timezone.utc) - cached_at).total_seconds() / 86400
        if age_days > ANSWER_CACHE_MAX_AGE_DAYS:
            _delete_entry(product_slug, doc.id)
            return None
    except ValueError:
        return None

    chunk_ids = meta.get("chunk_ids") or []
    live_score = mean_final_score(chunk_ids)
    if live_score is not None and live_score < ANSWER_CACHE_MIN_TRUST:
        # Confirmed downvoted below the trust floor since caching — remove it,
        # don't just skip it, so it stops shadowing a valid lower-ranked candidate.
        _delete_entry(product_slug, doc.id)
        return None
    if live_score is None:
        # Not evidence the entry is bad — just not (yet) scored — don't delete,
        # but don't risk serving it either.
        return None

    # Skips retrieve(), so record the bookkeeping here to keep the underlying
    # chunks' retrieval/agreement signals fresh even on a cache-served turn.
    try:
        source_types = meta.get("chunk_source_types") or []
        stand_in_docs = [
            Document(id=cid, page_content="", metadata={"source_type": st})
            for cid, st in zip(chunk_ids, source_types, strict=False)
        ]
        if stand_in_docs:
            record_retrieval(stand_in_docs, product_slug=product_slug)
    except Exception:
        logger.exception("Failed to record cache-hit retrieval bookkeeping")

    logger.info("Answer cache hit product=%s similarity=%.3f", product_slug, similarity)
    return {
        "answer": meta.get("answer", ""),
        "sources": meta.get("sources") or [],
        "source_type": meta.get("source_type", ""),
        "confidence": "high",
        "similar_questions": meta.get("similar_questions") or [],
        "chunk_ids": chunk_ids,
        "cached": True,
    }


def lookup(query: str, *, product_slug: str) -> dict | None:
    """Return a cached answer dict for a near-duplicate question, or ``None``.

    Checks up to ``ANSWER_CACHE_CANDIDATES`` nearest entries, not just the
    single closest one — a stale/low-trust top match no longer hides a valid
    lower-ranked candidate; it gets deleted and the next one is tried.

    Args:
        query: Standalone (already condensed) question text.
        product_slug: Active product slug — cache is scoped per product.

    Returns:
        Same shape as ``chain.query_engine.ask()``'s RAG result dict (plus
        ``cached: True``), or ``None`` if no candidate is usable — callers
        fall through to the normal pipeline.
    """
    store = _get_store(product_slug)
    try:
        hits = store.similarity_search_with_relevance_scores(query, k=ANSWER_CACHE_CANDIDATES)
    except Exception:
        logger.exception("Answer cache lookup failed — falling back to live pipeline")
        return None

    for doc, similarity in hits:
        result = _validate_candidate(doc, similarity, product_slug)
        if result is not None:
            return result
    return None


def store(query: str, result: dict, *, product_slug: str) -> None:
    """Cache a high-confidence RAG answer for future near-duplicate questions.

    Only call this for answers that already scored ``confidence == "high"`` —
    callers (``chain.query_engine``) gate on that before invoking ``store``.

    Args:
        query: Standalone question text — embedded as the cache lookup key.
        result: The RAG result dict as returned by ``chain.query_engine.ask()``,
            including ``chunk_ids`` and ``chunk_source_types`` (parallel lists).
        product_slug: Active product slug.
    """
    doc = Document(
        page_content=query,
        metadata={
            "answer": result.get("answer", ""),
            "sources": result.get("sources") or [],
            "source_type": result.get("source_type", ""),
            "similar_questions": result.get("similar_questions") or [],
            "chunk_ids": result.get("chunk_ids") or [],
            "chunk_source_types": result.get("chunk_source_types") or [],
            "cached_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    try:
        _get_store(product_slug).add_documents([doc])
    except Exception:
        logger.exception("Failed to write answer cache entry — non-fatal")

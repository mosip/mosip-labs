"""
Duplicate Question Detection.

Before running the full RAG pipeline, check whether the user's query is
semantically similar to an existing community thread.  If similarity exceeds
DEDUP_THRESHOLD, return the existing thread metadata so the app can surface it
directly — avoiding redundant LLM calls and pointing users to existing answers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DEDUP_THRESHOLD
from retrieval.retriever import get_community_store


def find_similar_question(query: str) -> dict | None:
    """Search community collection for a question similar to the query.

    Filters to ``post_type=question`` chunks when the backend supports metadata
    filters; otherwise falls back to unfiltered similarity search.

    Args:
        query: User question to match against community threads.

    Returns:
        Metadata dict of the matching thread, or ``None`` if similarity is
        below ``DEDUP_THRESHOLD`` / no hits. Dict keys: ``title``, ``source``
        (URL), ``tags``, ``similarity_score``.

    Raises:
        Exception: Propagates non-filter-related store errors.
    """
    store = get_community_store()

    # Filter to question-type chunks only — we match the question, not answers.
    # Use relevance_scores (normalised to [0,1]) rather than raw distance so the
    # conversion is correct regardless of whether the collection uses L2 or cosine space.
    try:
        results = store.similarity_search_with_relevance_scores(
            query,
            k=1,
            filter={"post_type": "question"},
        )
    except Exception as e:
        # Some backends don't support filter on this method; fall back.
        if not any(kw in str(e).lower() for kw in ("filter", "where", "unsupported")):
            raise
        results = store.similarity_search_with_relevance_scores(query, k=1)

    if not results:
        return None

    doc, similarity = results[0]   # relevance_scores already in [0, 1]

    if similarity < DEDUP_THRESHOLD:
        return None

    return {
        "title":            doc.metadata.get("title", ""),
        "source":           doc.metadata.get("source", ""),
        "tags":             doc.metadata.get("tags", ""),
        "similarity_score": round(similarity, 3),
    }

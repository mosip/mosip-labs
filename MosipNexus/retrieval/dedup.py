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
from config.settings import CHROMA_DIR, COMMUNITY_COLLECTION, DEDUP_THRESHOLD


def find_similar_question(query: str) -> dict | None:
    """Search community collection for a question similar to the query.

    Returns metadata dict of the matching thread, or None if no close match.
    The dict includes: title, source (URL), tags, similarity_score.

    Uses similarity_search_with_score so we get the actual distance value
    to compare against DEDUP_THRESHOLD.
    """
    from langchain_chroma import Chroma
    from retrieval.retriever import get_embeddings

    embeddings = get_embeddings()
    store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name=COMMUNITY_COLLECTION,
    )

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
        # Some Chroma versions don't support filter on this method; fall back.
        # Re-raise anything that is not a filter-compatibility error.
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

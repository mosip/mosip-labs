"""
Retriever — loads both ChromaDB collections and exposes unified search.

Docs and community results are retrieved separately via MMR search,
then merged and returned with source metadata preserved.
Confidence is derived from the best chunk's cosine distance.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    CHROMA_DIR, CODE_COLLECTION, CODE_RETRIEVAL_K,
    COMMUNITY_COLLECTION, CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM, DOCS_COLLECTION, EMBED_MODEL,
    GITHUB_COLLECTION, GITHUB_RETRIEVAL_K,
    RETRIEVAL_FETCH_K, RETRIEVAL_K,
)

_ERROR_CODE_RE = re.compile(r'\b[A-Z]{2,}-[A-Z]{2,}-\d{3,}\b')
_CODE_QUERY_RE = re.compile(
    r"\b(class|method|interface|package|service|impl|handler|processor|"
    r"java|spring|bean|annotation|controller|repository|util|helper|"
    r"which file|what file|where is|which class|what class|handles|implements|"
    r"source code|codebase|code for|"
    r"configure|configuration|setup|install|deploy|deployment|"
    r"helm|values\.yaml|properties|yaml|yml|config)\b",
    re.IGNORECASE,
)

_embeddings: HuggingFaceEmbeddings | None = None
_docs_store: Chroma | None = None
_community_store: Chroma | None = None
_github_store: Chroma | None = None
_code_store: Chroma | None = None


def _try_load_optional_store(collection_name: str, embeddings: HuggingFaceEmbeddings) -> Chroma | None:
    """Load a ChromaDB collection only if it exists and has content."""
    try:
        store = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name=collection_name,
        )
        if store._collection.count() > 0:
            return store
    except Exception:
        pass
    return None


def _build() -> None:
    global _embeddings, _docs_store, _community_store, _github_store, _code_store
    _embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    _docs_store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=_embeddings,
        collection_name=DOCS_COLLECTION,
    )
    _community_store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=_embeddings,
        collection_name=COMMUNITY_COLLECTION,
    )
    _github_store = _try_load_optional_store(GITHUB_COLLECTION, _embeddings)
    _code_store   = _try_load_optional_store(CODE_COLLECTION, _embeddings)


def _get_stores() -> tuple[Chroma, Chroma]:
    if _docs_store is None:
        _build()
    assert _docs_store is not None and _community_store is not None
    return _docs_store, _community_store


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return the shared embedding model, initialising lazily."""
    if _embeddings is None:
        _build()
    assert _embeddings is not None
    return _embeddings


def retrieve(query: str, k: int = RETRIEVAL_K) -> tuple[list[Document], str]:
    """Search all available collections and return merged results with confidence label.

    Searches docs + community always; GitHub collection searched when available.

    Returns:
        docs:       combined list of retrieved Document objects
        confidence: "high" | "medium" | "low"
    """
    docs_store, community_store = _get_stores()

    docs_retriever = docs_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": RETRIEVAL_FETCH_K},
    )
    community_retriever = community_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": RETRIEVAL_FETCH_K},
    )

    doc_results       = docs_retriever.invoke(query)
    community_results = community_retriever.invoke(query)

    github_results: list[Document] = []
    if _github_store is not None:
        github_retriever = _github_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": GITHUB_RETRIEVAL_K, "fetch_k": RETRIEVAL_FETCH_K},
        )
        github_results = github_retriever.invoke(query)

    code_results: list[Document] = []
    if _code_store is not None:
        # 3× boost for error-code queries and explicit code/class questions
        _is_targeted_code = _ERROR_CODE_RE.search(query) or _CODE_QUERY_RE.search(query)
        code_k = CODE_RETRIEVAL_K * 3 if _is_targeted_code else CODE_RETRIEVAL_K
        code_retriever = _code_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": code_k, "fetch_k": RETRIEVAL_FETCH_K},
        )
        code_results = code_retriever.invoke(query)

    # Confidence from the best relevance score across all searched collections.
    # similarity_search_with_relevance_scores returns [0, 1] regardless of the
    # underlying distance metric (L2 or cosine), so thresholds are always valid.
    best_score = 0.0
    _score_stores = [
        (docs_store, 1.0),
        (community_store, 1.0),
    ]
    if _github_store is not None:
        _score_stores.append((_github_store, 1.0))
    if _code_store is not None:
        _score_stores.append((_code_store, 1.0))

    for store, _ in _score_stores:
        try:
            top = store.similarity_search_with_relevance_scores(query, k=1)
            if top:
                best_score = max(best_score, top[0][1])
        except Exception:
            pass

    if best_score >= CONFIDENCE_HIGH:
        confidence = "high"
    elif best_score >= CONFIDENCE_MEDIUM:
        confidence = "medium"
    else:
        confidence = "low"

    return doc_results + community_results + github_results + code_results, confidence

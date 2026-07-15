"""
Retriever — loads pgvector collections and exposes unified search.

Docs and community results are retrieved separately via MMR search,
then merged and returned with source metadata preserved.
Confidence is derived from the best chunk's cosine similarity score.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy import create_engine as _create_engine, text as _sql_text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    PG_CONNECTION, CODE_COLLECTION, CODE_RETRIEVAL_K,
    COMMUNITY_COLLECTION, CONFLUENCE_COLLECTION, CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM, DOCS_COLLECTION, EMBED_MODEL,
    GITHUB_COLLECTION, GITHUB_RETRIEVAL_K, JIRA_COLLECTION,
    MAX_CONTEXT_DOCS, RETRIEVAL_FETCH_K, RETRIEVAL_K,YOUTUBE_COLLECTION,
)

_ERROR_CODE_RE = re.compile(r'\b[A-Z]{2,}-[A-Z]{2,}-\d{3,}\b')
_FORMAT_SPECIFIER_RE = re.compile(r'%[sd]')
# Packages that are demo/test/sample apps — ranked lower than production code.
# A result from io.mosip.authentication.demo is NOT the production class.
_DEMO_PACKAGE_RE = re.compile(
    r'\b(?:\.demo\.|\.test\.|\.sample\.|\.mock\.|\.simulator\.|SampleSDK|DemoService)',
    re.IGNORECASE,
)
_SIBLING_FILE_RE = re.compile(r'error(?:code|codes|constants)?\.java$', re.IGNORECASE)
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
_docs_store: PGVector | None = None
_community_store: PGVector | None = None
_github_store: PGVector | None = None
_code_store: PGVector | None = None
_pg_engine = None
_youtube_store = None


def _get_pg_engine():
    global _pg_engine
    if _pg_engine is None:
        _pg_engine = _create_engine(PG_CONNECTION)
    return _pg_engine


def _try_load_optional_store(collection_name: str, embeddings: HuggingFaceEmbeddings) -> PGVector | None:
    """Load a pgvector collection only if it exists and has content."""
    try:
        with _get_pg_engine().connect() as conn:
            count = conn.execute(
                _sql_text(
                    "SELECT COUNT(*) FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :name"
                ),
                {"name": collection_name},
            ).scalar()
        if count and count > 0:
            return PGVector(
                embeddings=embeddings,
                connection=PG_CONNECTION,
                collection_name=collection_name,
            )
    except Exception:
        pass
    return None


def _build() -> None:
    global _embeddings, _docs_store, _community_store, _github_store, _code_store, _youtube_store
    _embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    _docs_store = PGVector(
        embeddings=_embeddings,
        connection=PG_CONNECTION,
        collection_name=DOCS_COLLECTION,
    )
    _community_store = PGVector(
        embeddings=_embeddings,
        connection=PG_CONNECTION,
        collection_name=COMMUNITY_COLLECTION,
    )
    _github_store = _try_load_optional_store(GITHUB_COLLECTION, _embeddings)
    _code_store   = _try_load_optional_store(CODE_COLLECTION, _embeddings)
    _youtube_store = _try_load_optional_store(
        YOUTUBE_COLLECTION,
        _embeddings,
    )


def get_collection_counts() -> dict[str, int]:
    """Return row counts for all ingested pgvector collections (non-zero only)."""
    _all = {
        DOCS_COLLECTION:      "docs",
        COMMUNITY_COLLECTION: "community",
        GITHUB_COLLECTION:    "github",
        CODE_COLLECTION:      "code",
        CONFLUENCE_COLLECTION:"confluence",
        JIRA_COLLECTION:      "jira",
        YOUTUBE_COLLECTION: "youtube",
    }
    counts: dict[str, int] = {}
    with _get_pg_engine().connect() as conn:
        for coll_name, label in _all.items():
            result = conn.execute(
                _sql_text(
                    "SELECT COUNT(*) FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :name"
                ),
                {"name": coll_name},
            ).scalar() or 0
            if result > 0:
                counts[label] = result
    return counts


def _exact_code_search(error_code: str, collection_name: str, limit: int = 5) -> list[Document]:
    """SQL ILIKE search for chunks that literally contain the error code string.

    Bypasses vector similarity so the defining constant is always surfaced even
    when its embedding drifts from the query phrasing.
    """
    try:
        with _get_pg_engine().connect() as conn:
            rows = conn.execute(
                _sql_text(
                    "SELECT e.document, e.cmetadata "
                    "FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :coll "
                    "AND e.document ILIKE :pattern "
                    "LIMIT :limit"
                ),
                {"coll": collection_name, "pattern": f"%{error_code}%", "limit": limit},
            ).fetchall()
        return [Document(page_content=row[0], metadata=row[1] or {}) for row in rows]
    except Exception:
        return []


def _sibling_chunks(title: str, collection_name: str, limit: int = 8) -> list[Document]:
    """Retrieve additional chunks from the same source file by title match.

    When we land on an error-constants file, pulling sibling chunks provides the
    surrounding constant definitions so the LLM can compare related error codes.
    """
    try:
        with _get_pg_engine().connect() as conn:
            rows = conn.execute(
                _sql_text(
                    "SELECT e.document, e.cmetadata "
                    "FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :coll "
                    "AND e.cmetadata->>'title' = :title "
                    "LIMIT :limit"
                ),
                {"coll": collection_name, "title": title, "limit": limit},
            ).fetchall()
        return [Document(page_content=row[0], metadata=row[1] or {}) for row in rows]
    except Exception:
        return []


def _split_production_vs_demo(docs: list[Document]) -> tuple[list[Document], list[Document]]:
    """Partition code chunks into production code vs. demo/test/sample code.

    Demo packages (*.demo.*, SampleSDK, etc.) rank lower than production code
    for production questions — prevents the LLM from citing a demo-app class
    as if it were the real IDA/kernel/regproc implementation.
    """
    production: list[Document] = []
    demo: list[Document] = []
    for doc in docs:
        if _DEMO_PACKAGE_RE.search(doc.page_content) or _DEMO_PACKAGE_RE.search(
            doc.metadata.get("source", "") + " " + doc.metadata.get("title", "")
        ):
            demo.append(doc)
        else:
            production.append(doc)
    return production, demo


def _annotate_format_specifiers(docs: list[Document]) -> list[Document]:
    """Inline-annotate code chunks that contain Java format specifiers (%s, %d).

    When an error-constant definition like `"Invalid Input parameter - %s"` appears
    in retrieved context, LLMs often substitute a specific example value seen elsewhere
    in training data (e.g. "id") instead of correctly identifying it as a placeholder.
    This annotation is placed right next to the format string so any LLM reads the
    warning in context without relying solely on system prompt instructions.
    """
    annotated: list[Document] = []
    for doc in docs:
        if (
            doc.metadata.get("source_type") == "code"
            and _FORMAT_SPECIFIER_RE.search(doc.page_content)
            and _ERROR_CODE_RE.search(doc.page_content)
        ):
            annotation = (
                "\n⚠️  NOTE FOR LLM: This chunk contains Java format specifiers (%s / %d). "
                "These are RUNTIME PLACEHOLDERS — the actual field name or value is substituted "
                "at runtime and appears in the real API error response. "
                "DO NOT replace %s with any specific value (such as 'id') in your answer. "
                "Tell the user to read their actual error response for the substituted value."
            )
            doc = Document(
                page_content=doc.page_content + annotation,
                metadata=doc.metadata,
            )
        annotated.append(doc)
    return annotated


def _get_stores() -> tuple[PGVector, PGVector]:
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

    doc_results = docs_retriever.invoke(query)[:4]
    community_results = community_retriever.invoke(query)[:2]

    github_results: list[Document] = []
    if _github_store is not None:
        github_retriever = _github_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": GITHUB_RETRIEVAL_K, "fetch_k": RETRIEVAL_FETCH_K},
        )
        github_results = github_retriever.invoke(query)[:1]
    youtube_results: list[Document] = []
    if _youtube_store is not None:
        youtube_retriever = _youtube_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": RETRIEVAL_FETCH_K},
        )
        youtube_results = youtube_retriever.invoke(query)[:3]
        

    code_results: list[Document] = []
    exact_results: list[Document] = []
    sibling_results: list[Document] = []
    if _code_store is not None:
        # 3× boost for error-code queries and explicit code/class questions
        _error_match = _ERROR_CODE_RE.search(query)
        _is_targeted_code = _error_match or _CODE_QUERY_RE.search(query)
        code_k = CODE_RETRIEVAL_K * 3 if _is_targeted_code else CODE_RETRIEVAL_K
        code_retriever = _code_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": code_k, "fetch_k": RETRIEVAL_FETCH_K},
        )
        code_results = code_retriever.invoke(query)[:2]

        if _error_match:
            error_code = _error_match.group()
            # Fix 3: SQL keyword search so the defining constant is always retrieved
            exact_results = _exact_code_search(error_code, CODE_COLLECTION)
            # Fix 4: pull sibling constants from every error-constants file we landed on.
            # Matches files like IdAuthenticationErrorConstants.java, AuthAdapterErrorCode.java,
            # KernelErrorCodes.java, PacketManagerErrorCodes.java, etc.
            seen_titles: set[str] = set()
            for doc in exact_results + code_results:
                title = doc.metadata.get("title", "")
                if title and _SIBLING_FILE_RE.search(title) and title not in seen_titles:
                    seen_titles.add(title)
                    sibling_results.extend(_sibling_chunks(title, CODE_COLLECTION))

    # Split code results: production code ranks above demo/test/sample code
    _prod_code, _demo_code = _split_production_vs_demo(exact_results + sibling_results + code_results)

    # Deduplicate by content while preserving priority order:
    # exact/sibling production code → doc/community/github → demo/test code (last resort)
    _seen: set[str] = set()
    _deduped: list[Document] = []
    for doc in (
    _prod_code
    + doc_results
    + community_results
    + github_results
    + youtube_results
    + _demo_code
    ):
        if doc.page_content not in _seen:
            _seen.add(doc.page_content)
            _deduped.append(doc)

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
    if _youtube_store is not None:
        _score_stores.append((_youtube_store, 1.0))    
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

    return _annotate_format_specifiers(_deduped[:MAX_CONTEXT_DOCS]), confidence

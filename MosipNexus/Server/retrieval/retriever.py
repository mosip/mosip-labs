"""
Retriever — loads pgvector collections and exposes unified search.

Optimised for parallel users:
  - One shared SQLAlchemy engine (pooled) for all stores
  - Query embedded once (with lock + LRU cache), then collections searched in parallel
  - Confidence taken from MMR score results (no second embedding pass)
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy import text as _sql_text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.products import ProductProfile, get_product, list_products
from config.settings import (
    CODE_RETRIEVAL_K,
    EMBED_CACHE_SIZE,
    EMBED_MODEL,
    GITHUB_RETRIEVAL_K,
    MAX_CONTEXT_DOCS,
    RETRIEVAL_FETCH_K,
    RETRIEVAL_K,
    RETRIEVAL_PARALLELISM,
)
from db.engine import get_engine
from chain.confidence import scorer as confidence_scorer


logger = logging.getLogger(__name__)

_ERROR_CODE_RE = re.compile(r'\b[A-Z]{2,}-[A-Z]{2,}-\d{3,}\b')
_FORMAT_SPECIFIER_RE = re.compile(r'%[sd]')
# Packages that are demo/test/sample apps — ranked lower than production code.
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


class _ProductStores:
    """PGVector handles for one product slug."""

    __slots__ = ("docs", "community", "github", "code", "esignet", "website", "profile")

    def __init__(
        self,
        profile: ProductProfile,
        docs: PGVector,
        community: PGVector,
        github: PGVector | None,
        code: PGVector | None,
        esignet: PGVector | None,
        website: PGVector | None,
    ):
        self.profile = profile
        self.docs = docs
        self.community = community
        self.github = github
        self.code = code
        self.esignet = esignet
        self.website = website


_embeddings: HuggingFaceEmbeddings | None = None
_stores_by_slug: dict[str, _ProductStores] = {}
_build_lock = threading.Lock()
_embed_lock = threading.Lock()
_embed_cache: OrderedDict[str, list[float]] = OrderedDict()
_embed_cache_lock = threading.Lock()
_search_pool: ThreadPoolExecutor | None = None


def _get_search_pool() -> ThreadPoolExecutor:
    global _search_pool
    if _search_pool is None:
        _search_pool = ThreadPoolExecutor(
            max_workers=max(1, RETRIEVAL_PARALLELISM),
            thread_name_prefix="nexus-retrieve",
        )
    return _search_pool


def _get_pg_engine():
    return get_engine()


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
                connection=_get_pg_engine(),
                collection_name=collection_name,
            )
    except Exception:
        logger.debug("Optional collection %s not loaded", collection_name, exc_info=True)
    return None


def _ensure_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        with _build_lock:
            if _embeddings is None:
                _embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return _embeddings


def _build_product_stores(profile: ProductProfile) -> _ProductStores:
    """Create / attach pgvector stores for one product (docs+community required)."""
    emb = _ensure_embeddings()
    engine = _get_pg_engine()
    docs = PGVector(
        embeddings=emb,
        connection=engine,
        collection_name=profile.docs_collection,
    )
    community = PGVector(
        embeddings=emb,
        connection=engine,
        collection_name=profile.community_collection,
    )
    github = _try_load_optional_store(profile.github_collection, emb)
    code = _try_load_optional_store(profile.code_collection, emb)
    esignet = (
        _try_load_optional_store(profile.esignet_collection, emb)
        if profile.esignet_collection
        else None
    )
    website = (
        _try_load_optional_store(profile.website_collection, emb)
        if profile.website_collection
        else None
    )
    return _ProductStores(profile, docs, community, github, code, esignet, website)


def _get_stores(product: str | None = None) -> _ProductStores:
    """Return cached stores for the active (or named) product."""
    profile = get_product(product)
    slug = profile.slug
    cached = _stores_by_slug.get(slug)
    if cached is not None:
        return cached
    with _build_lock:
        cached = _stores_by_slug.get(slug)
        if cached is not None:
            return cached
        stores = _build_product_stores(profile)
        _stores_by_slug[slug] = stores
        logger.info(
            "Loaded vector stores for product=%s docs=%s community=%s",
            slug,
            profile.docs_collection,
            profile.community_collection,
        )
        return stores


def warmup() -> None:
    """Load embedding model + stores for every product that uses retrieval."""
    _ensure_embeddings()
    for profile in list_products():
        if not profile.retrieval_enabled:
            logger.info("Skipping vector warmup for product=%s (retrieval disabled)", profile.slug)
            continue
        try:
            _get_stores(profile.slug)
        except Exception:
            logger.exception("Warmup failed for product=%s (will retry lazily)", profile.slug)
    logger.info("Retriever warmup complete (embed model + pgvector stores).")


def ensure_ready() -> None:
    """Public readiness probe — initialise embedder and active product stores."""
    _get_stores()
    get_embeddings()


def is_error_code_query(query: str) -> bool:
    """True when the query mentions a MOSIP-style error code (e.g. ``IDA-MLC-009``)."""
    return bool(_ERROR_CODE_RE.search(query or ""))


def is_code_query(query: str) -> bool:
    """True when the query looks like a source-code / class / method lookup."""
    return bool(_CODE_QUERY_RE.search(query or ""))


def get_collection_counts(product: str | None = None) -> dict[str, int]:
    """Return row counts for the active product's collections (non-zero only)."""
    profile = get_product(product)
    _all = {
        profile.docs_collection: "docs",
        profile.community_collection: "community",
        profile.github_collection: "github",
        profile.code_collection: "code",
        profile.confluence_collection: "confluence",
        profile.jira_collection: "jira",
    }
    if profile.esignet_collection:
        _all[profile.esignet_collection] = "esignet"
    if profile.website_collection:
        _all[profile.website_collection] = "website"
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
    """SQL ILIKE search for chunks that literally contain the error code string."""
    try:
        with _get_pg_engine().connect() as conn:
            rows = conn.execute(
                _sql_text(
                    "SELECT e.id, e.document, e.cmetadata "
                    "FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :coll "
                    "AND e.document ILIKE :pattern "
                    "LIMIT :limit"
                ),
                {"coll": collection_name, "pattern": f"%{error_code}%", "limit": limit},
            ).fetchall()
        return [Document(id=str(row[0]), page_content=row[1], metadata=row[2] or {}) for row in rows]
    except Exception:
        return []


def _sibling_chunks(title: str, collection_name: str, limit: int = 8) -> list[Document]:
    """Retrieve additional chunks from the same source file by title match."""
    try:
        with _get_pg_engine().connect() as conn:
            rows = conn.execute(
                _sql_text(
                    "SELECT e.id, e.document, e.cmetadata "
                    "FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :coll "
                    "AND e.cmetadata->>'title' = :title "
                    "LIMIT :limit"
                ),
                {"coll": collection_name, "title": title, "limit": limit},
            ).fetchall()
        return [Document(id=str(row[0]), page_content=row[1], metadata=row[2] or {}) for row in rows]
    except Exception:
        return []


def _split_production_vs_demo(docs: list[Document]) -> tuple[list[Document], list[Document]]:
    """Partition code chunks into production code vs. demo/test/sample code."""
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
    """Inline-annotate code chunks that contain Java format specifiers (%s, %d)."""
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
                id=doc.id,
                page_content=doc.page_content + annotation,
                metadata=doc.metadata,
            )
        annotated.append(doc)
    return annotated


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return the shared embedding model, initialising lazily."""
    return _ensure_embeddings()


def get_community_store(product: str | None = None) -> PGVector:
    """Shared community PGVector store (for dedup — no new connection per call)."""
    return _get_stores(product).community


def _embed_query(query: str) -> list[float]:
    """Embed once per unique query; serialise model access for thread safety."""
    key = query.strip()
    with _embed_cache_lock:
        cached = _embed_cache.get(key)
        if cached is not None:
            _embed_cache.move_to_end(key)
            return cached

    emb = get_embeddings()
    with _embed_lock:
        vector = emb.embed_query(query)

    with _embed_cache_lock:
        _embed_cache[key] = vector
        _embed_cache.move_to_end(key)
        while len(_embed_cache) > max(1, EMBED_CACHE_SIZE):
            _embed_cache.popitem(last=False)
    return vector


def _relevance(store: PGVector, distance: float) -> float:
    """Convert store distance to [0, 1] relevance."""
    try:
        return float(store._select_relevance_score_fn()(distance))  # noqa: SLF001
    except Exception:
        # Cosine / L2 fallback when score fn unavailable
        return float(max(0.0, min(1.0, 1.0 - distance)))


def _mmr_search(
    store: PGVector,
    embedding: list[float],
    k: int,
) -> tuple[list[Document], float]:
    """MMR search by precomputed vector; return docs + best relevance in the set."""
    try:
        pairs = store.max_marginal_relevance_search_with_score_by_vector(
            embedding=embedding,
            k=k,
            fetch_k=RETRIEVAL_FETCH_K,
        )
    except Exception:
        logger.exception("MMR search failed for collection")
        return [], 0.0

    if not pairs:
        return [], 0.0
    docs = [doc for doc, _ in pairs]
    best = max(_relevance(store, score) for _, score in pairs)
    return docs, best


def retrieve(
    query: str,
    k: int = RETRIEVAL_K,
    product: str | None = None,
) -> tuple[list[Document], str]:
    """Search all available collections and return merged results with confidence label.

    Embeds the query once, then searches collections in parallel (MMR). When the
    query contains a MOSIP-style error code, also runs exact SQL ILIKE matches
    and sibling-file chunk pulls on the code collection. Production code ranks
    ahead of demo/test packages; format-specifier annotations are appended for
    the LLM when relevant.

    Args:
        query: Standalone search query (already condensed by the query engine).
        k: MMR ``k`` for docs and community collections.
        product: Optional product slug (``mosip`` / ``inji``); defaults to request context.

    Returns:
        A tuple ``(docs, confidence)`` where ``docs`` is a deduplicated list of
        ``Document`` objects (capped by ``MAX_CONTEXT_DOCS``) and ``confidence``
        is ``"high"``, ``"medium"``, or ``"low"``.
    """
    stores = _get_stores(product)
    profile = stores.profile
    query_vec = _embed_query(query)

    _error_match = _ERROR_CODE_RE.search(query)
    _is_targeted_code = bool(_error_match or _CODE_QUERY_RE.search(query))
    code_k = (CODE_RETRIEVAL_K * 2 if _is_targeted_code else CODE_RETRIEVAL_K)

    jobs: list[tuple[str, PGVector, int]] = [
        ("docs", stores.docs, k),
        ("community", stores.community, k),
    ]
    if stores.esignet is not None:
        jobs.append(("esignet", stores.esignet, k))
    if stores.website is not None:
        jobs.append(("website", stores.website, k))
    if stores.github is not None:
        jobs.append(("github", stores.github, GITHUB_RETRIEVAL_K))
    if stores.code is not None:
        jobs.append(("code", stores.code, code_k))

    results_by_name: dict[str, list[Document]] = {}
    best_score = 0.0
    pool = _get_search_pool()
    futures = {
        pool.submit(_mmr_search, store, query_vec, store_k): name
        for name, store, store_k in jobs
    }
    for fut in as_completed(futures):
        name = futures[fut]
        docs, score = fut.result()
        results_by_name[name] = docs
        best_score = max(best_score, score)

    doc_results = results_by_name.get("docs", [])
    community_results = results_by_name.get("community", [])
    esignet_results = results_by_name.get("esignet", [])
    website_results = results_by_name.get("website", [])
    github_results = results_by_name.get("github", [])
    code_results = results_by_name.get("code", [])

    exact_results: list[Document] = []
    sibling_results: list[Document] = []
    if stores.code is not None and _error_match:
        error_code = _error_match.group()
        exact_results = _exact_code_search(error_code, profile.code_collection)
        seen_titles: set[str] = set()
        for doc in exact_results + code_results:
            title = doc.metadata.get("title", "")
            if title and _SIBLING_FILE_RE.search(title) and title not in seen_titles:
                seen_titles.add(title)
                sibling_results.extend(_sibling_chunks(title, profile.code_collection))

    _prod_code, _demo_code = _split_production_vs_demo(
        exact_results + sibling_results + code_results
    )

    _seen: set[str] = set()
    _deduped: list[Document] = []
    for doc in _prod_code + doc_results + esignet_results + website_results + community_results + github_results + _demo_code:
        if doc.page_content not in _seen:
            _seen.add(doc.page_content)
            _deduped.append(doc)

    final_docs = _annotate_format_specifiers(_deduped[:MAX_CONTEXT_DOCS])

    # Upsert chunk_scores + blend this-query relevance with each chunk's historical
    # reliability (source-type weight, retrieval consistency, agreement, recency,
    # feedback). Falls back to relevance-only for any doc missing a scorable id.
    try:
        confidence_scorer.record_retrieval(final_docs, product_slug=profile.slug)
        confidence = confidence_scorer.score_answer(final_docs, mmr_relevance=best_score)
    except Exception:
        logger.exception("Confidence scoring failed — falling back to relevance-only")
        from config.settings import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM
        if best_score >= CONFIDENCE_HIGH:
            confidence = "high"
        elif best_score >= CONFIDENCE_MEDIUM:
            confidence = "medium"
        else:
            confidence = "low"

    return final_docs, confidence

"""Multi-product profiles for a single Nexus Server process.

Built-in profiles:
  * ``mosip`` / ``inji`` — RAG over product docs, community, GitHub, code, …
  * ``generic`` — white-label / open-source reuse: **direct BYOK LLM** answers
    with no required docs/community URLs or vector collections

Crawl/ingest jobs still use process-level ``PRODUCT_SLUG`` in ``settings``.
Interactive chat picks a profile per request via ``X-Nexus-Product`` or body
``product``. Callers can also set ``answer_mode`` to ``rag`` or ``direct``.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

AnswerMode = Literal["rag", "direct", "web"]


@dataclass(frozen=True)
class ProductProfile:
    """Public branding + optional knowledge-base URLs + pgvector collection names."""

    slug: str
    name: str
    short: str
    docs_base_url: str
    community_base_url: str
    community_new_topic_path: str
    github_org: str
    logo_url: str
    docs_collection: str
    community_collection: str
    github_collection: str
    code_collection: str
    confluence_collection: str
    jira_collection: str
    esignet_collection: str = ""
    website_collection: str = ""
    # When False, chat defaults to direct BYOK LLM (no vector retrieval).
    retrieval_enabled: bool = True
    default_answer_mode: AnswerMode = "rag"

    @property
    def community_new_topic_url(self) -> str:
        base = (self.community_base_url or "").rstrip("/")
        if not base:
            return ""
        path = self.community_new_topic_path or ""
        if path and not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}" if path else base

    def public_dict(self) -> dict[str, Any]:
        # Build the sources list dynamically so the UI renders whatever is
        # actually configured for this product — no hardcoded labels.
        sources: list[dict[str, str]] = []
        if self.docs_collection:
            sources.append({"key": "docs", "label": "Documentation"})
        if self.esignet_collection:
            sources.append({"key": "esignet", "label": "eSignet Docs"})
        if self.website_collection:
            sources.append({"key": "website", "label": f"{self.short} Website"})
        if self.community_collection:
            sources.append({"key": "community", "label": "Community Forum"})
        if self.github_collection:
            sources.append({"key": "github", "label": "GitHub Issues"})
        if self.confluence_collection:
            sources.append({"key": "confluence", "label": "Confluence"})
        if self.code_collection:
            sources.append({"key": "code", "label": "Source Code"})
        return {
            "product_name": self.name,
            "product_short": self.short,
            "product_slug": self.slug,
            "docs_base_url": self.docs_base_url,
            "community_base_url": self.community_base_url,
            "community_new_topic_url": self.community_new_topic_url,
            "github_org": self.github_org,
            "logo_url": self.logo_url,
            "retrieval_enabled": self.retrieval_enabled,
            "default_answer_mode": self.default_answer_mode,
            "sources": sources,
        }


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def _build_catalog() -> dict[str, ProductProfile]:
    """Load MOSIP + Inji + generic profiles (env overrides allowed)."""
    mosip = ProductProfile(
        slug="mosip",
        name=_env("MOSIP_PRODUCT_NAME", "MOSIP Nexus"),
        short=_env("MOSIP_PRODUCT_SHORT", "MOSIP"),
        docs_base_url=_env("MOSIP_DOCS_BASE_URL", "https://docs.mosip.io/1.2.0"),
        community_base_url=_env("MOSIP_COMMUNITY_BASE_URL", "https://community.mosip.io"),
        community_new_topic_path=_env("MOSIP_COMMUNITY_NEW_TOPIC_PATH", "/new-topic"),
        github_org=_env("MOSIP_GITHUB_ORG", "mosip"),
        logo_url="/logos/mosip.png",
        docs_collection=_env("MOSIP_DOCS_COLLECTION", "mosip_docs"),
        community_collection=_env("MOSIP_COMMUNITY_COLLECTION", "mosip_community"),
        github_collection=_env("MOSIP_GITHUB_COLLECTION", "mosip_github"),
        code_collection=_env("MOSIP_CODE_COLLECTION", "mosip_code"),
        confluence_collection=_env("MOSIP_CONFLUENCE_COLLECTION", "mosip_confluence"),
        jira_collection=_env("MOSIP_JIRA_COLLECTION", "mosip_jira"),
        esignet_collection=_env("ESIGNET_COLLECTION", "esignet_docs"),
        website_collection=_env("WEBSITE_COLLECTION", "mosip_website"),
        retrieval_enabled=True,
        default_answer_mode="rag",
    )
    inji = ProductProfile(
        slug="inji",
        name=_env("INJI_PRODUCT_NAME", "Inji Nexus"),
        short=_env("INJI_PRODUCT_SHORT", "Inji"),
        docs_base_url=_env("INJI_DOCS_BASE_URL", "https://docs.inji.io"),
        community_base_url=_env(
            "INJI_COMMUNITY_BASE_URL",
            "https://community.mosip.io/c/inji/16",
        ),
        community_new_topic_path=_env(
            "INJI_COMMUNITY_NEW_TOPIC_PATH",
            "/new-topic?category=inji",
        ),
        github_org=_env("INJI_GITHUB_ORG", "mosip"),
        logo_url="/logos/inji.png",
        docs_collection=_env("INJI_DOCS_COLLECTION", "inji_docs"),
        # Falls back to the shared MOSIP community collection (contains Inji posts too).
        # Set INJI_COMMUNITY_COLLECTION=inji_community once a dedicated crawl is populated.
        community_collection=_env("INJI_COMMUNITY_COLLECTION", "mosip_community"),
        github_collection=_env("INJI_GITHUB_COLLECTION", "inji_github"),
        code_collection=_env("INJI_CODE_COLLECTION", "inji_code"),
        confluence_collection=_env("INJI_CONFLUENCE_COLLECTION", "inji_confluence"),
        jira_collection=_env("INJI_JIRA_COLLECTION", "inji_jira"),
        retrieval_enabled=True,
        default_answer_mode="rag",
    )
    # White-label / BYOK-only — no docs URLs or vector KB required.
    generic = ProductProfile(
        slug="generic",
        name=_env("GENERIC_PRODUCT_NAME", "Nexus"),
        short=_env("GENERIC_PRODUCT_SHORT", "Assistant"),
        docs_base_url=_env("GENERIC_DOCS_BASE_URL", ""),
        community_base_url=_env("GENERIC_COMMUNITY_BASE_URL", ""),
        community_new_topic_path=_env("GENERIC_COMMUNITY_NEW_TOPIC_PATH", ""),
        github_org=_env("GENERIC_GITHUB_ORG", ""),
        logo_url=_env("GENERIC_LOGO_URL", "/logos/generic.svg"),
        docs_collection=_env("GENERIC_DOCS_COLLECTION", "generic_docs"),
        community_collection=_env("GENERIC_COMMUNITY_COLLECTION", "generic_community"),
        github_collection=_env("GENERIC_GITHUB_COLLECTION", "generic_github"),
        code_collection=_env("GENERIC_CODE_COLLECTION", "generic_code"),
        confluence_collection=_env("GENERIC_CONFLUENCE_COLLECTION", "generic_confluence"),
        jira_collection=_env("GENERIC_JIRA_COLLECTION", "generic_jira"),
        retrieval_enabled=_env("GENERIC_RETRIEVAL_ENABLED", "false").lower()
        in ("1", "true", "yes"),
        default_answer_mode=_env("GENERIC_DEFAULT_ANSWER_MODE", "web").lower()  # type: ignore[arg-type]
        if _env("GENERIC_DEFAULT_ANSWER_MODE", "web").lower() in ("rag", "direct", "web")
        else "web",
    )
    return {"mosip": mosip, "inji": inji, "generic": generic}


PRODUCTS: dict[str, ProductProfile] = _build_catalog()
DEFAULT_PRODUCT_SLUG = _env("DEFAULT_PRODUCT", "mosip").lower()
if DEFAULT_PRODUCT_SLUG not in PRODUCTS:
    DEFAULT_PRODUCT_SLUG = "mosip"

_current: ContextVar[ProductProfile] = ContextVar(
    "nexus_product",
    default=PRODUCTS[DEFAULT_PRODUCT_SLUG],
)


def normalize_product_slug(raw: str | None) -> str:
    """Map aliases to a known slug; fall back to default."""
    if not raw:
        return DEFAULT_PRODUCT_SLUG
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "mosip": "mosip",
        "mosip_nexus": "mosip",
        "inji": "inji",
        "inji_nexus": "inji",
        "generic": "generic",
        "direct": "generic",
        "byok": "generic",
        "llm": "generic",
        "custom": "generic",
        "white_label": "generic",
        "whitelabel": "generic",
    }
    return aliases.get(key, key if key in PRODUCTS else DEFAULT_PRODUCT_SLUG)


def normalize_answer_mode(
    raw: str | None,
    *,
    product: ProductProfile | None = None,
) -> AnswerMode:
    """Resolve ``rag`` | ``direct`` | ``web`` from request or product default."""
    profile = product or current_product()
    if not raw or not str(raw).strip():
        return profile.default_answer_mode
    key = str(raw).strip().lower()
    if key in ("direct", "llm", "byok", "chat", "passthrough"):
        return "direct"
    if key in ("rag", "retrieve", "knowledge", "docs"):
        return "rag"
    if key in ("web", "search", "websearch", "internet"):
        return "web"
    # Unknown → product default
    return profile.default_answer_mode


def get_product(slug: str | None = None) -> ProductProfile:
    """Return a product profile by slug (or the request/default current)."""
    if slug is None:
        return _current.get()
    return PRODUCTS[normalize_product_slug(slug)]


def set_current_product(slug: str | None) -> ProductProfile:
    """Bind the product for this async/request context."""
    profile = get_product(slug)
    _current.set(profile)
    return profile


def current_product() -> ProductProfile:
    """Product bound to the current request (or process default)."""
    return _current.get()


def list_products() -> list[ProductProfile]:
    """Stable order: mosip, inji, generic, then any extras."""
    order = ["mosip", "inji", "generic"]
    out = [PRODUCTS[s] for s in order if s in PRODUCTS]
    for slug, p in PRODUCTS.items():
        if slug not in order:
            out.append(p)
    return out


def public_config_payload(active_slug: str | None = None) -> dict[str, Any]:
    """Payload for ``GET /config`` — active product + full catalog."""
    active = get_product(active_slug)
    catalog = {p.slug: p.public_dict() for p in list_products()}
    payload = active.public_dict()
    payload["default_product"] = DEFAULT_PRODUCT_SLUG
    payload["active_product"] = active.slug
    payload["products"] = catalog
    payload["answer_modes"] = ["rag", "direct"]
    return payload

"""
Nexus MCP Server (MOSIP + Inji)

Exposes the shared knowledge base as MCP tools so Claude Desktop (or any
MCP-compatible client) can search it using the client's own LLM subscription.
The LLM runs on the client side — this server only performs vector retrieval.

Tools:
    search_knowledge(query, product="mosip"|"inji")  — hybrid retrieval
    list_knowledge_sources(product=...)              — collection counts + URLs
    list_products()                                  — available product modes

Default product when ``product`` is omitted:
    MCP_DEFAULT_PRODUCT env (else DEFAULT_PRODUCT / mosip)

Run (SSE for Docker / remote Claude Desktop URL):
    set PYTHONPATH=Server
    set MCP_TRANSPORT=sse
    set MCP_PORT=8002
    uv run python Server/mcp_server/server.py

Claude Desktop — dual entries (stdio, pinned defaults)::

    {
      "mcpServers": {
        "mosip-nexus": {
          "command": "uv",
          "args": ["run", "python", "Server/mcp_server/server.py"],
          "env": {
            "PYTHONPATH": ".../Server",
            "MCP_TRANSPORT": "stdio",
            "MCP_DEFAULT_PRODUCT": "mosip"
          }
        },
        "inji-nexus": {
          "command": "uv",
          "args": ["run", "python", "Server/mcp_server/server.py"],
          "env": {
            "PYTHONPATH": ".../Server",
            "MCP_TRANSPORT": "stdio",
            "MCP_DEFAULT_PRODUCT": "inji"
          }
        }
      }
    }

See Server/docs/MCP_SERVER.md for SSE dual-port examples and troubleshooting.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from config.logging_config import setup_logging
from config.products import (
    DEFAULT_PRODUCT_SLUG,
    ProductProfile,
    get_product,
    list_products,
    normalize_product_slug,
)
from config.settings import MCP_PORT, MCP_TRANSPORT

setup_logging()
logger = logging.getLogger("nexus.mcp")

_MCP_DEFAULT = normalize_product_slug(
    os.getenv("MCP_DEFAULT_PRODUCT", DEFAULT_PRODUCT_SLUG)
)

# Pre-load the retriever in the background so the first tool call is instant.
_retrieve_fn = None
_ready = False
_ready_event = threading.Event()


def _resolve_product(raw: str | None) -> ProductProfile:
    """Map tool/env product arg to a profile (falls back to MCP_DEFAULT_PRODUCT)."""
    slug = (raw or "").strip()
    if not slug:
        return get_product(_MCP_DEFAULT)
    return get_product(slug)


def _warmup():
    global _retrieve_fn, _ready
    try:
        from retrieval.retriever import retrieve, warmup

        warmup()
        _retrieve_fn = retrieve
        _ready = True
        logger.info(
            "MCP retriever warmup complete (default_product=%s)",
            _MCP_DEFAULT,
        )
    except Exception:
        logger.exception("MCP retriever warmup failed")
    finally:
        _ready_event.set()


threading.Thread(target=_warmup, daemon=True).start()

_product_names = ", ".join(p.short for p in list_products())

mcp = FastMCP(
    "nexus",
    instructions=(
        f"You have access to the Nexus knowledge base for {_product_names}. "
        "Use search_knowledge to find documentation, community answers, GitHub issues, "
        "Confluence pages, and source code before answering.\n\n"
        "PRODUCT MODE:\n"
        "- Pass product=\"mosip\" for MOSIP Nexus knowledge (docs.mosip.io, mosip collections).\n"
        "- Pass product=\"inji\" for Inji Nexus knowledge (docs.inji.io, inji collections).\n"
        f"- If product is omitted, the server default is \"{_MCP_DEFAULT}\".\n"
        "- Call list_products when unsure which modes are available.\n\n"
        "ERROR CODE ANSWERS:\n"
        "- Read the constant NAME to identify what %s/%d placeholders represent "
        "(e.g. '%s Auth Type is Locked' → %s is an auth type like Fingerprint/Iris/Face/OTP/Demo).\n"
        "- For auth-type lockout errors (e.g. IDA-MLC-019), the unlock path is an admin "
        "action via the Partner Management portal or admin unlock API — not a client-side fix. "
        "Always state WHO must act and HOW, not just restate the condition.\n"
        "- Show neighboring error codes from the same constant file when relevant.\n\n"
        "CITATION AND SOURCE TRANSPARENCY RULES:\n"
        "- Always include the source URL inline when citing a result. Use the format: "
        "[Source: <url>] placed immediately after the fact you are citing.\n"
        "- For source code results, name the exact file and the constant or method you are referencing.\n"
        "- CRITICAL — never silently blend Nexus results with web search or training data. "
        "If the specific fact is NOT present in search_knowledge results, say so explicitly "
        "before supplementing."
    ),
    port=MCP_PORT,
    host="0.0.0.0",
)


@mcp.tool()
def search_knowledge(query: str, product: str = "") -> str:
    """Search a product knowledge base (docs, community, GitHub, Confluence, code).

    Performs hybrid vector retrieval only — no server-side LLM. The MCP client
    (e.g. Claude Desktop) reads the returned chunks and writes the answer.

    Args:
        query: Natural-language search query.
        product: ``mosip`` or ``inji``. Empty string uses the server default
            (``MCP_DEFAULT_PRODUCT`` / ``DEFAULT_PRODUCT``).

    Returns:
        Formatted string with confidence + chunks (title, URL, body), or a
        short status message if the embedder is still warming up / no hits.
    """
    profile = _resolve_product(product)
    if not profile.retrieval_enabled:
        return (
            f"Product `{profile.slug}` ({profile.name}) is configured for **direct BYOK LLM** "
            "answers via the REST `/chat` API (`answer_mode=direct`) — it has no vector "
            "knowledge base for MCP search.\n\n"
            "Use product=\"mosip\" or product=\"inji\" with search_knowledge, "
            "or call POST /chat with product=\"generic\" and your own llm_api_key."
        )
    if _retrieve_fn is None:
        logger.info("search_knowledge waiting for retriever warmup...")
        _ready_event.wait(timeout=90)
    if _retrieve_fn is None:
        return (
            f"The {profile.name} knowledge base failed to initialize. "
            "Check the MCP server logs for details."
        )
    logger.info(
        "MCP search_knowledge product=%s q_len=%d",
        profile.slug,
        len(query or ""),
    )
    docs, confidence = _retrieve_fn(query, product=profile.slug)

    if not docs:
        logger.info("MCP search_knowledge product=%s no hits", profile.slug)
        return (
            f"No relevant content found in the {profile.short} knowledge base "
            f"(product={profile.slug}) for this query."
        )

    logger.info(
        "MCP search_knowledge product=%s hits=%d confidence=%s",
        profile.slug,
        len(docs),
        confidence,
    )

    parts: list[str] = [
        f"Product: {profile.name} ({profile.slug})",
        f"Confidence: {confidence}\n",
    ]
    for doc in docs:
        meta = doc.metadata
        source_type = meta.get("source_type", "unknown")
        source_url = meta.get("source", "")
        title = meta.get("title", "")

        header = f"[{source_type.upper()}]"
        if title:
            header += f" {title}"
        if source_url:
            header += f"\n📎 {source_url}"

        parts.append(f"{header}\n\n{doc.page_content}")

    return "\n\n---\n\n".join(parts)


@mcp.tool()
def list_knowledge_sources(product: str = "") -> str:
    """List knowledge sources for one product with live record counts and URLs.

    Args:
        product: ``mosip`` or ``inji``. Empty string uses the server default.

    Returns:
        Human-readable summary of collection chunk counts and docs/community/GitHub URLs.
    """
    profile = _resolve_product(product)
    try:
        from retrieval.retriever import get_collection_counts

        counts = get_collection_counts(profile.slug)
    except Exception:
        counts = {}

    def _count(key: str) -> str:
        return f"{counts[key]:,} chunks" if key in counts else "not indexed"

    return (
        f"{profile.name} Knowledge Base (product={profile.slug}) — Available Sources:\n\n"
        f"1. **Documentation** ({_count('docs')}) — {profile.docs_base_url}\n"
        f"2. **Community Forum** ({_count('community')}) — {profile.community_base_url}\n"
        f"3. **GitHub Issues** ({_count('github')}) — org `{profile.github_org}`\n"
        f"4. **Confluence** ({_count('confluence')})\n"
        f"5. **Source Code** ({_count('code')}) — org `{profile.github_org}`\n\n"
        f"Use search_knowledge(query, product=\"{profile.slug}\") to search these sources.\n"
        "Call list_products() to see other product modes."
    )


@mcp.tool()
def list_products() -> str:
    """List product modes this Nexus MCP server can search (MOSIP, Inji, …).

    Returns:
        Slug, display name, docs URL, and whether each mode is the MCP default.
    """
    lines = [
        "Available Nexus product modes:",
        f"(MCP default when product arg is omitted: {_MCP_DEFAULT})\n",
    ]
    for p in list_products():
        marker = " ← default" if p.slug == _MCP_DEFAULT else ""
        lines.append(
            f"- **{p.slug}** — {p.name}{marker}\n"
            f"  Docs: {p.docs_base_url}\n"
            f"  Community: {p.community_base_url}\n"
            f"  GitHub org: {p.github_org}"
        )
    lines.append(
        "\nPass product=\"mosip\" or product=\"inji\" to search_knowledge / "
        "list_knowledge_sources."
    )
    return "\n".join(lines)


if __name__ == "__main__":
    logger.info(
        "Starting MCP server default_product=%s transport=%s port=%s",
        _MCP_DEFAULT,
        MCP_TRANSPORT,
        MCP_PORT,
    )
    mcp.run(transport=MCP_TRANSPORT)

"""
MOSIP Nexus MCP Server

Exposes the MOSIP knowledge base as MCP tools so Claude Desktop (or any
MCP-compatible client) can search it using the user's own Claude subscription.
The LLM runs on the client side — this server only performs vector retrieval.

Run standalone:
    uv run python mcp/server.py

Users add this to their Claude Desktop config (~/.claude/claude_desktop_config.json):

    For local Docker deployment:
    {
      "mcpServers": {
        "mosip-nexus": {
          "url": "http://localhost:8002/sse"
        }
      }
    }

    For production (after deployment):
    {
      "mcpServers": {
        "mosip-nexus": {
          "url": "https://mosip-nexus.env.mosip.net/mcp/sse"
        }
      }
    }
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

# Pre-load the retriever in the background so the first tool call is instant.
# The embedding model takes ~60s to load — doing it here avoids Claude Desktop
# timing out on the first search_mosip call.
_retrieve_fn = None

def _warmup():
    global _retrieve_fn
    from retrieval.retriever import retrieve
    retrieve("mosip warmup")   # triggers model + pgvector init
    _retrieve_fn = retrieve

threading.Thread(target=_warmup, daemon=True).start()

MCP_PORT = int(os.getenv("MCP_PORT", "8002"))

mcp = FastMCP(
    "mosip-nexus",
    instructions=(
        "You have access to the MOSIP (Modular Open Source Identity Platform) knowledge base. "
        "Use search_mosip to find relevant documentation, community answers, GitHub issues, "
        "Confluence pages, and source code before answering MOSIP questions.\n\n"
        "CITATION AND SOURCE TRANSPARENCY RULES:\n"
        "- Always include the source URL inline when citing a result. Use the format: "
        "[Source: <url>] placed immediately after the fact you are citing.\n"
        "- For source code results, name the exact file (e.g. IdAuthenticationErrorConstants.java) "
        "and the constant or method you are referencing.\n"
        "- CRITICAL — never silently blend Nexus results with web search or training data. "
        "If the specific fact (e.g. a hardware spec table, a version number, a config value) "
        "is NOT present in search_mosip results, say so explicitly before supplementing: "
        "'The Nexus knowledge base does not contain this specific detail — the following is from "
        "[web search / my training data]:'. This keeps the user informed about data provenance "
        "and prevents them from treating community forum posts as official verified specs.\n"
        "- If search_mosip returns general context but not the specific numbers or values the "
        "user asked for, state: 'Nexus confirmed the topic exists but did not return the exact "
        "figures — I found them via [source].' Do not present web-sourced numbers as if they "
        "came from Nexus.\n\n"
        "ERROR CODE RULES (applies when answering about codes like IDA-MLC-009):\n"
        "- Read the exact error message string from the source code constant. "
        "If it contains %s, %d, or any Java format specifier, state clearly that this is a "
        "RUNTIME PLACEHOLDER substituted with the actual offending field/value at runtime. "
        "NEVER replace %s with a specific example value and present it as the error definition.\n"
        "- Tell the user to read their actual error response — the substituted %s value in the "
        "JSON response body is the specific field that is missing or invalid in their case.\n"
        "- If the retrieved context includes sibling constants from the same file "
        "(e.g. IDA-MLC-008 and IDA-MLC-009 side by side), compare them explicitly so the user "
        "understands the distinction (e.g. 'missing parameter' vs 'present but invalid')."
    ),
    port=MCP_PORT,
    host="0.0.0.0",
)


@mcp.tool()
def search_mosip(query: str) -> str:
    """Search the MOSIP knowledge base.

    Returns relevant content from:
    - MOSIP official documentation (docs.mosip.io)
    - Community forum Q&A threads (community.mosip.io)
    - GitHub issues from 25 active MOSIP repositories
    - Confluence pages (engineering, QA, product management, support desk)
    - MOSIP source code (Java, YAML, SQL, XML, properties files)

    Args:
        query: The question or topic to search for (any language supported).

    Returns:
        Formatted context from the top matching chunks, with source metadata.
    """
    if _retrieve_fn is None:
        return (
            "The MOSIP Nexus knowledge base is still initializing "
            "(loading the embedding model — takes ~60 seconds on first start). "
            "Please try again in a moment."
        )
    docs, confidence = _retrieve_fn(query)

    if not docs:
        return "No relevant content found in the MOSIP knowledge base for this query."

    parts: list[str] = [f"Confidence: {confidence}\n"]
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
def list_knowledge_sources() -> str:
    """List all knowledge sources indexed in MOSIP Nexus with live record counts."""
    try:
        from retrieval.retriever import get_collection_counts
        counts = get_collection_counts()
    except Exception:
        counts = {}

    def _count(key: str) -> str:
        return f"{counts[key]:,} chunks" if key in counts else "not indexed"

    return (
        "MOSIP Nexus Knowledge Base — Available Sources:\n\n"
        f"1. **MOSIP Documentation** ({_count('docs')}) — docs.mosip.io/1.2.0\n"
        "   Covers: architecture, modules, deployment guides, API references, configuration\n\n"
        f"2. **Community Forum** ({_count('community')}) — community.mosip.io\n"
        "   Covers: real-world Q&A, accepted solutions, deployment issues, integration questions\n\n"
        f"3. **GitHub Issues** ({_count('github')}) — 25 active MOSIP repositories\n"
        "   Covers: bug reports, feature discussions, error resolutions, workarounds\n\n"
        f"4. **Confluence** ({_count('confluence')}) — QT, ENGG, PMS, MSD spaces\n"
        "   Covers: internal engineering docs, QA processes, product management, support desk\n\n"
        f"5. **Source Code** ({_count('code')}) — 71 MOSIP repositories\n"
        "   Covers: Java classes, YAML configs, SQL schemas, error constants, properties files\n\n"
        "Use search_mosip(query) to search across all sources simultaneously."
    )


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)

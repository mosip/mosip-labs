"""MCP (Model Context Protocol) server for Claude Desktop and compatible clients.

Runs as a separate process from FastAPI. Tools perform retrieval only; the
client LLM writes the final answer. See ``docs/MCP_SERVER.md``.
"""

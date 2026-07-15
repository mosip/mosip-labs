"""RAG answer generation (LLM + retrieval).

``query_engine.ask`` is the primary entry used by ``POST /chat``.
``summarizer`` supports ingestion-time summarisation when a server Groq key
is configured.
"""

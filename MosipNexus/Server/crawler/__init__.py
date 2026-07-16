"""Knowledge crawlers — fetch external content into ``Server/data/*.json``.

Each module exposes a crawl entrypoint used by ``run_update.py`` and one-off
scripts. Downstream ingestion (``ingestion.store``) embeds JSON into pgvector.
"""

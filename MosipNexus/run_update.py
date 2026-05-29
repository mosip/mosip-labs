"""
Incremental Update — run this after the initial full pipeline.

What it does in each run:
  Docs:      fetches sitemap, hashes each page, embeds ONLY new/changed pages.
  Community: fetches only topics newer than the last known topic ID.
  GitHub:    fetches only issues newer than the last known issue number per repo.

Time per update run:
  Full pipeline (first time): 3–4 hours (all chunks embedded)
  Incremental update:         5–15 minutes (only delta embedded)

Usage:
    uv run python MosipNexus/run_update.py

State is persisted in MosipNexus/data/crawl_state.json between runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import shutil

from crawler.community_crawler import crawl_incremental as community_incremental
from crawler.docs_crawler import crawl_incremental as docs_incremental
from crawler.github_crawler import crawl_incremental as github_incremental
from crawler.state import load, now_iso, save
from config.settings import (
    CHROMA_DIR, COMMUNITY_COLLECTION, DOCS_COLLECTION,
    GITHUB_COLLECTION, GITHUB_REPOS, PIPELINE_VERSION,
)
from ingestion.store import build_embeddings, ingest_incremental


def _full_rebuild() -> None:
    """Delete chroma_db + state and re-run the full ingestion pipeline.

    Called automatically when EMBED_MODEL, CHUNK_SIZE, or CHUNK_OVERLAP changes,
    because existing vectors are incompatible with the new pipeline settings.
    """
    print("  Deleting chroma_db/ and crawl_state.json ...")
    shutil.rmtree(CHROMA_DIR, ignore_errors=True)

    from crawler.state import STATE_FILE
    STATE_FILE.unlink(missing_ok=True)

    print("  Running full ingestion pipeline ...")
    import subprocess, sys
    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "ingestion" / "store.py")],
        check=True,
    )
    print("  Full rebuild complete.")


def run() -> None:
    state = load()

    # ── Pipeline version check ─────────────────────────────────────────────────
    saved_version = state.get("pipeline_version")
    if saved_version and saved_version != PIPELINE_VERSION:
        print(
            f"\n⚠️  Pipeline configuration changed "
            f"(saved: {saved_version}, current: {PIPELINE_VERSION}).\n"
            f"   EMBED_MODEL, CHUNK_SIZE, or CHUNK_OVERLAP was modified.\n"
            f"   A full rebuild is required — existing vectors are stale.\n"
        )
        _full_rebuild()
        return

    embeddings = build_embeddings()

    # ── Docs ───────────────────────────────────────────────────────────────────
    print("\n══ DOCS ══════════════════════════════════════════════════════════")
    new_docs, changed_docs, unchanged_count = docs_incremental(state)
    print(f"\nResult: {len(new_docs)} new | {len(changed_docs)} changed | {unchanged_count} unchanged")

    if new_docs or changed_docs:
        print(f"\nIngesting into '{DOCS_COLLECTION}'...")
        ingest_incremental(new_docs, changed_docs, DOCS_COLLECTION, embeddings, source_type="docs")

        # Update state: store hashes for new and changed pages
        url_hashes = state.setdefault("docs", {}).setdefault("url_hashes", {})
        for page in new_docs + changed_docs:
            url_hashes[page["url"]] = page["_hash"]
        state["docs"]["last_run"] = now_iso()
    else:
        print("Docs: nothing to update.")

    # ── Community ──────────────────────────────────────────────────────────────
    print("\n══ COMMUNITY ═════════════════════════════════════════════════════")
    new_topics = community_incremental(state)
    print(f"\nResult: {len(new_topics)} new topics")

    if new_topics:
        print(f"\nIngesting into '{COMMUNITY_COLLECTION}'...")
        ingest_incremental(new_topics, [], COMMUNITY_COLLECTION, embeddings, source_type="community")

        # Update state: advance max topic ID
        max_id = max(
            int(t["url"].rstrip("/").split("/")[-1])
            for t in new_topics
        )
        community_state = state.setdefault("community", {})
        community_state["max_topic_id"] = max(
            max_id, community_state.get("max_topic_id", 0)
        )
        community_state["last_run"] = now_iso()
    else:
        print("Community: nothing to update.")

    # ── GitHub ─────────────────────────────────────────────────────────────────
    print("\n══ GITHUB ════════════════════════════════════════════════════════")
    new_github_issues = github_incremental(state)
    print(f"\nResult: {len(new_github_issues)} new issues")

    if new_github_issues:
        print(f"\nIngesting into '{GITHUB_COLLECTION}'...")
        # GitHub issues are ingested as plain documents (not Q&A pairs)
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_chroma import Chroma
        from config.settings import CHROMA_DIR as _CHROMA_DIR, CHUNK_SIZE, CHUNK_OVERLAP

        lc_docs = [
            Document(
                page_content=f"GitHub Issue: {i['title']}\nRepo: {i['repo']}\n\n{i['content']}",
                metadata={
                    "source":      i["url"],
                    "source_type": "github",
                    "title":       i["title"],
                    "repo":        i["repo"],
                    "state":       i.get("state", ""),
                    "labels":      i.get("labels", ""),
                },
            )
            for i in new_github_issues
            if i.get("content", "").strip()
        ]
        splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        chunks = splitter.split_documents(lc_docs)
        print(f"  → {len(chunks)} chunks to embed")
        store = Chroma(
            persist_directory=_CHROMA_DIR,
            embedding_function=embeddings,
            collection_name=GITHUB_COLLECTION,
        )
        store.add_documents(chunks)

        # Update state: advance max issue number per repo
        github_state = state.setdefault("github", {})
        for issue in new_github_issues:
            repo   = issue.get("repo", "")
            number = issue.get("number", 0)
            if repo:
                repo_state = github_state.setdefault(repo, {})
                repo_state["max_issue_number"] = max(
                    repo_state.get("max_issue_number", 0), number
                )
                repo_state["last_run"] = now_iso()
    else:
        print("GitHub: nothing to update.")

    # ── Persist state ──────────────────────────────────────────────────────────
    save(state)
    print("\n✓ State saved. Next run will only process new/changed content.")


if __name__ == "__main__":
    run()

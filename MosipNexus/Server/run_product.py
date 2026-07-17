"""
Product-aware crawl + ingest runner.

Lets you build or update the knowledge base for any product (MOSIP, Inji, or a
custom slug) without touching a single line of code — just set env vars.

Usage
-----
Full rebuild for a product (first-time setup):

    uv run python run_product.py --product inji --full

Incremental update (only new/changed content):

    uv run python run_product.py --product inji

Or set ACTIVE_PRODUCT in the environment and omit --product:

    ACTIVE_PRODUCT=inji uv run python run_product.py --full

Env vars per product
--------------------
Set INJI_* (or <SLUG>_*) to configure each product independently:

    INJI_DOCS_BASE_URL       = https://docs.inji.io
    INJI_COMMUNITY_BASE_URL  = https://community.mosip.io/c/inji/16
    INJI_GITHUB_ORG          = mosip
    INJI_GITHUB_REPOS        = mosip/inji,mosip/inji-wallet,mosip/inji-openid4vp
    INJI_WEBSITE_URLS        = https://inji.io
    INJI_CONFLUENCE_URL      = https://your-confluence.atlassian.net   (optional)
    INJI_JIRA_URL            = https://your-jira.atlassian.net         (optional)

Any env var listed in config/settings.py can be prefixed with <SLUG>_ to
override it for a specific product run.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_SERVER_DIR = Path(__file__).parent


def _run(script: str, env: dict) -> None:
    result = subprocess.run(
        ["uv", "run", "python", script],
        cwd=_SERVER_DIR,
        env=env,
    )
    if result.returncode != 0:
        print(f"\nFAILED: {script} exited with code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Product-aware crawler + ingestion runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--product",
        default=os.getenv("ACTIVE_PRODUCT", "mosip"),
        help="Product slug (mosip | inji | any custom slug). Default: ACTIVE_PRODUCT env or mosip.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full rebuild: run all crawlers then ingest. Default: incremental update only.",
    )
    parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub crawler (slow; useful during testing).",
    )
    parser.add_argument(
        "--skip-website",
        action="store_true",
        help="Skip website crawler.",
    )
    args = parser.parse_args()

    slug = args.product.strip().lower().replace("-", "_").replace(" ", "_")
    env = {**os.environ, "ACTIVE_PRODUCT": slug}

    bar = "═" * 60
    mode = "FULL REBUILD" if args.full else "INCREMENTAL UPDATE"
    print(f"\n{bar}")
    print(f"  Product : {slug.upper()}")
    print(f"  Mode    : {mode}")
    print(f"{bar}\n")

    if args.full:
        print("── Docs ────────────────────────────────────────────────────")
        _run("crawler/docs_crawler.py", env)

        print("\n── Community ───────────────────────────────────────────────")
        _run("crawler/community_crawler.py", env)

        if not args.skip_github:
            print("\n── GitHub ──────────────────────────────────────────────────")
            _run("crawler/github_crawler.py", env)
        else:
            print("\n── GitHub (skipped) ────────────────────────────────────────")

        if not args.skip_website:
            print("\n── Website ─────────────────────────────────────────────────")
            _run("crawler/website_crawler.py", env)
        else:
            print("\n── Website (skipped) ───────────────────────────────────────")

        print("\n── Ingesting all sources → pgvector ────────────────────────")
        _run("ingestion/store.py", env)

    else:
        print("Running incremental update (only new / changed content)...")
        _run("run_update.py", env)

    print(f"\n{bar}")
    print(f"  Done — {slug.upper()} knowledge base is up to date.")
    print(f"{bar}\n")


if __name__ == "__main__":
    main()

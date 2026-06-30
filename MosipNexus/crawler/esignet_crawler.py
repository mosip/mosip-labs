"""
eSignet Documentation Crawler.

Uses the generic web crawler to crawl the eSignet documentation
and store the output as JSON.
"""

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    ESIGNET_BASE_URL,
    ESIGNET_FILE,
)


def crawl_esignet():
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "web_crawler.py"),
        "--base-url",
        ESIGNET_BASE_URL,
        "--output",
        str(ESIGNET_FILE),
    ]

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    crawl_esignet()
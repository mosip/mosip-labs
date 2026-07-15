"""Central logging setup for Nexus Server.

Call ``setup_logging()`` once at process start (API lifespan, MCP ``__main__``,
CLI jobs). Configuration::

    LOG_LEVEL=INFO          # DEBUG | INFO | WARNING | ERROR
    LOG_FORMAT=text         # text | json
    LOG_ACCESS=true         # HTTP access lines from middleware

Never log secrets (API keys, SMTP passwords, full PG DSNs).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from config.settings import LOG_ACCESS, LOG_FORMAT, LOG_LEVEL

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """Minimal JSON line formatter (stdlib only — no extra deps)."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("request_id", "session_id", "path", "method", "status", "elapsed_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(*, force: bool = False) -> None:
    """Configure root + nexus loggers. Idempotent unless ``force=True``."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    level_name = (LOG_LEVEL or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if (LOG_FORMAT or "text").lower() == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for name in (
        "httpx",
        "httpcore",
        "urllib3",
        "asyncio",
        "multipart",
        "watchfiles",
        "sentence_transformers",
        "transformers",
        "torch",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)

    # SQLAlchemy engine echo stays off unless DEBUG
    if level > logging.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _CONFIGURED = True
    logging.getLogger("nexus").info(
        "Logging configured level=%s format=%s access=%s",
        level_name,
        (LOG_FORMAT or "text").lower(),
        LOG_ACCESS,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module logger (prefer ``logging.getLogger(__name__)``)."""
    return logging.getLogger(name)

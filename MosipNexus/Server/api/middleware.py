"""HTTP request logging + product-mode middleware."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.products import set_current_product
from config.settings import LOG_ACCESS

logger = logging.getLogger("nexus.access")

# High-frequency probes — log at DEBUG unless status >= 400
_QUIET_PATHS = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
})


class ProductModeMiddleware(BaseHTTPMiddleware):
    """Bind MOSIP/Inji product profile from ``X-Nexus-Product`` or ``?product=``."""

    async def dispatch(self, request: Request, call_next) -> Response:
        slug = (
            request.headers.get("x-nexus-product")
            or request.query_params.get("product")
        )
        profile = set_current_product(slug)
        request.state.product = profile.slug
        response = await call_next(request)
        response.headers["X-Nexus-Product"] = profile.slug
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach ``X-Request-Id`` and emit one access line per request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = (
            request.headers.get("x-request-id")
            or request.headers.get("x-correlation-id")
            or str(uuid.uuid4())
        )
        request.state.request_id = rid
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-Id"] = rid
            return response
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "%s %s failed after %.1fms rid=%s",
                request.method,
                request.url.path,
                elapsed_ms,
                rid,
            )
            raise
        finally:
            if LOG_ACCESS:
                elapsed_ms = (time.perf_counter() - started) * 1000
                path = request.url.path
                quiet = path in _QUIET_PATHS and status < 400
                level = logging.DEBUG if quiet else logging.INFO
                product = getattr(request.state, "product", "-")
                logger.log(
                    level,
                    "%s %s → %s %.1fms rid=%s product=%s",
                    request.method,
                    path,
                    status,
                    elapsed_ms,
                    rid,
                    product,
                )

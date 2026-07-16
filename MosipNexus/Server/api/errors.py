"""FastAPI exception handlers — maps domain errors to structured JSON.

Domain exception classes live in ``errors`` (not this module) so controllers
never import ``api.*``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from errors import AppError

logger = logging.getLogger("nexus.api.errors")

# Re-export domain errors for existing ``from api.errors import …`` call sites
from errors import (  # noqa: E402
    BadRequestError,
    CapacityError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    UpstreamError,
    map_llm_exception,
)

__all__ = [
    "AppError",
    "BadRequestError",
    "CapacityError",
    "ConflictError",
    "NotFoundError",
    "ServiceUnavailableError",
    "UpstreamError",
    "error_body",
    "map_llm_exception",
    "register_exception_handlers",
]


def _request_id(request: Request) -> str:
    existing = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    return existing or str(uuid.uuid4())


def error_body(
    *,
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
) -> dict[str, Any]:
    return {
        "detail": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global handlers so every error returns a consistent JSON shape."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        rid = _request_id(request)
        logger.warning(
            "AppError %s %s → %s [%s]",
            exc.code,
            request.method,
            request.url.path,
            rid,
            extra={"code": exc.code, "status": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                code=exc.code,
                message=exc.message,
                request_id=rid,
                details=exc.details,
            ),
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        rid = _request_id(request)
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            code = str(detail.get("code", "HTTP_ERROR"))
            message = str(detail.get("message", ""))
            details = detail.get("details")
        elif isinstance(detail, dict):
            code = "HTTP_ERROR"
            message = str(detail.get("message") or detail.get("detail") or detail)
            details = detail
        else:
            code = "HTTP_ERROR"
            message = str(detail)
            details = None
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code=code, message=message, request_id=rid, details=details),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        rid = _request_id(request)
        errors = exc.errors()
        clean = []
        for err in errors:
            item = {k: v for k, v in err.items() if k != "ctx"}
            clean.append(item)
        message = "Request validation failed."
        if clean:
            loc = ".".join(str(x) for x in clean[0].get("loc", []) if x != "body")
            msg = clean[0].get("msg", "")
            if loc:
                message = f"Invalid field '{loc}': {msg}"
            elif msg:
                message = str(msg)
        logger.info("Validation error on %s [%s]: %s", request.url.path, rid, message)
        return JSONResponse(
            status_code=422,
            content=error_body(
                code="VALIDATION_ERROR",
                message=message,
                request_id=rid,
                details=clean,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = _request_id(request)
        logger.exception("Unhandled error on %s %s [%s]", request.method, request.url.path, rid)
        return JSONResponse(
            status_code=500,
            content=error_body(
                code="INTERNAL_ERROR",
                message="An internal error occurred. Please try again.",
                request_id=rid,
                details=None,
            ),
        )

"""Domain / application errors — shared by controllers and API handlers.

HTTP packaging lives in ``api.errors`` (FastAPI exception handlers). Controllers
must import from this module, never from ``api.*``.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error mapped to a structured HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "APP_ERROR",
        status_code: int = 400,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        self.headers = headers


class BadRequestError(AppError):
    def __init__(self, message: str, *, code: str = "BAD_REQUEST", details: Any = None) -> None:
        super().__init__(message, code=code, status_code=400, details=details)


class NotFoundError(AppError):
    def __init__(self, message: str, *, code: str = "NOT_FOUND", details: Any = None) -> None:
        super().__init__(message, code=code, status_code=404, details=details)


class ConflictError(AppError):
    def __init__(self, message: str, *, code: str = "CONFLICT", details: Any = None) -> None:
        super().__init__(message, code=code, status_code=409, details=details)


class CapacityError(AppError):
    """Server at concurrency limit — clients should retry."""

    def __init__(
        self,
        message: str = (
            "Server is at capacity (too many parallel chats). "
            "Retry shortly, or raise MAX_CONCURRENT_CHATS."
        ),
        *,
        retry_after: int = 2,
    ) -> None:
        super().__init__(
            message,
            code="CAPACITY_EXCEEDED",
            status_code=503,
            details={"retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )


class UpstreamError(AppError):
    """LLM / external provider failure."""

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(
            message,
            code="UPSTREAM_ERROR",
            status_code=502,
            details=details,
        )


class ServiceUnavailableError(AppError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "SERVICE_UNAVAILABLE",
        details: Any = None,
    ) -> None:
        super().__init__(message, code=code, status_code=503, details=details)


def map_llm_exception(exc: BaseException) -> AppError:
    """Convert LLM / LangChain failures into BadRequest or Upstream errors."""
    text = str(exc) or exc.__class__.__name__
    lower = text.lower()
    if any(k in lower for k in ("api key", "authentication", "unauthorized", "401", "invalid_api_key")):
        return BadRequestError(
            "LLM provider rejected the API key. Check Settings and try again.",
            code="LLM_AUTH_FAILED",
            details={"provider_message": text[:500]},
        )
    if any(k in lower for k in ("rate limit", "429", "quota", "too many requests")):
        return UpstreamError(
            "LLM provider rate limit reached. Wait a moment and retry.",
            details={"provider_message": text[:500]},
        )
    if any(k in lower for k in ("timeout", "timed out", "deadline")):
        return UpstreamError(
            "LLM provider timed out. Please try again.",
            details={"provider_message": text[:500]},
        )
    return UpstreamError(
        "The language model failed to generate an answer. Please try again.",
        details={"provider_message": text[:500]},
    )

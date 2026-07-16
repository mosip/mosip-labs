"""FastAPI application package.

Entry point: ``api.main:app`` (uvicorn). HTTP surface for chat, search,
sessions, feedback, stats, and notifications.

Pydantic request/response models with OpenAPI examples live in
``api.schemas``. Prefer importing those DTOs rather than inventing ad-hoc
dicts in clients.
"""

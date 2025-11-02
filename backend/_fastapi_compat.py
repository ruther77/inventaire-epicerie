"""Centralized FastAPI imports with a user-friendly error message.

This project relies on FastAPI for the HTTP layer. When contributors run the
API without installing the Python dependencies first, the default Python error
message (`ModuleNotFoundError: No module named 'fastapi'`) can be confusing.

This helper wraps the import so that every module importing FastAPI symbols
surfaced through a consistent and explicit hint about how to install the
missing dependency.
"""

from __future__ import annotations

FASTAPI_INSTALL_HINT = (
    "FastAPI is required to run the backend API. "
    "Install the dependencies with `python -m pip install -r requirements.txt` "
    "(or `requirements-dev.txt` for local development)."
)


def _raise_fastapi_import_error(exc: ModuleNotFoundError) -> None:
    """Re-raise a missing FastAPI error with installation guidance."""

    message = f"{FASTAPI_INSTALL_HINT}\nOriginal error: {exc}"
    raise ModuleNotFoundError(message) from exc


try:  # pragma: no cover - exercised indirectly via imports in tests
    from fastapi import (  # type: ignore import
        APIRouter,
        Depends,
        FastAPI,
        HTTPException,
        Query,
        Response,
        Security,
        status,
    )
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore import
    from fastapi.responses import JSONResponse  # type: ignore import
    from fastapi.security import (  # type: ignore import
        HTTPAuthorizationCredentials,
        HTTPBearer,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - validated via message
    if exc.name == "fastapi":
        _raise_fastapi_import_error(exc)
    raise


__all__ = [
    "APIRouter",
    "CORSMiddleware",
    "Depends",
    "FastAPI",
    "HTTPAuthorizationCredentials",
    "HTTPBearer",
    "HTTPException",
    "JSONResponse",
    "Query",
    "Response",
    "Security",
    "status",
]

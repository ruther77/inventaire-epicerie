"""Backend package exposing the FastAPI application for the SPA."""

from .main import app  # re-export for convenience

__all__ = ["app"]

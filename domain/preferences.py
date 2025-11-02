"""Domain-level helpers for user preferences such as saved views."""

from __future__ import annotations

from data_repository import get_engine
from services import SavedViewsService


_saved_views_service: SavedViewsService | None = None


def get_saved_views_service() -> SavedViewsService:
    """Return a cached :class:`SavedViewsService` tied to the configured engine."""

    global _saved_views_service
    if _saved_views_service is None:
        _saved_views_service = SavedViewsService(engine_factory=get_engine)
    return _saved_views_service


def set_saved_views_service(service: SavedViewsService | None) -> None:
    """Allow callers to override the saved views service instance."""

    global _saved_views_service
    _saved_views_service = service


__all__ = ["get_saved_views_service", "set_saved_views_service"]

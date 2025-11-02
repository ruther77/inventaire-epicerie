"""Domain-level entry points for sale-related features."""

from __future__ import annotations

from typing import Iterable

from data_repository import get_engine
from services import SaleService


_sale_service: SaleService | None = None


def get_sale_service() -> SaleService:
    """Return a cached :class:`SaleService` instance backed by the configured engine."""

    global _sale_service
    if _sale_service is None:
        _sale_service = SaleService(engine_factory=get_engine)
    return _sale_service


def set_sale_service(service: SaleService | None) -> None:
    """Allow tests and alternative clients to override the sale service instance."""

    global _sale_service
    _sale_service = service


def process_sale_transaction(
    cart: Iterable[dict], username: str | None
) -> tuple[bool, str | None, dict[str, bytes] | None]:
    """Proxy the sale transaction through the configured :class:`SaleService`."""

    return get_sale_service().process_sale_transaction(cart, username)


__all__ = ["get_sale_service", "set_sale_service", "process_sale_transaction"]

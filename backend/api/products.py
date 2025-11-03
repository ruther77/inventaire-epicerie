"""Product catalogue endpoints."""

from __future__ import annotations

from typing import Iterable

from .._fastapi_compat import APIRouter, Depends, HTTPException, status

from domain.catalogue import (
    InvalidBarcodeError,
    ProductNotFoundError,
    fetch_products as domain_fetch_products,
    load_active_products_map as domain_load_active_products_map,
    update_catalog_entry,
)

from ..security import get_current_user_optional, require_catalog_editor
from .schemas import ProductPayload, ProductUpdateRequest

router = APIRouter(prefix="/products", tags=["products"])


def fetch_products(include_inactive: bool = False, search: str | None = None) -> list[ProductPayload]:
    try:
        records = domain_fetch_products(include_inactive=include_inactive, search=search)
    except TypeError:
        records = domain_fetch_products()
    if not records:
        return []
    return [ProductPayload(**record) for record in records]


def load_active_products_map(product_ids: Iterable[int]) -> dict[int, dict[str, object]]:
    return domain_load_active_products_map(product_ids)


@router.get("", response_model=list[ProductPayload])
def list_products(
    _: dict | None = Depends(get_current_user_optional),
    include_inactive: bool = False,
    search: str | None = None,
) -> list[ProductPayload]:
    return fetch_products(include_inactive=include_inactive, search=search)


@router.patch("/{product_id}")
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    current_user: dict = Depends(require_catalog_editor),
) -> dict:
    updates = {
        key: value
        for key, value in payload.model_dump(exclude={"barcodes"}).items()
        if value is not None
    }

    role = (current_user.get("role") or "standard").lower()
    if role == "moderator":
        allowed_updates = {"actif", "nom", "categorie"}
        forbidden = set(updates) - allowed_updates
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Modifications non autorisées pour ce rôle",
            )
        if payload.barcodes is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Les modérateurs ne peuvent pas modifier les codes-barres",
            )

    barcodes = payload.barcodes
    if role == "moderator":
        barcodes = None

    try:
        result = update_catalog_entry(product_id, updates, barcodes)
    except ProductNotFoundError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidBarcodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "updated", "result": result}

"""Product catalogue endpoints."""

from __future__ import annotations

from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from data_repository import query_df
from product_service import InvalidBarcodeError, ProductNotFoundError, update_catalog_entry

from ..security import get_current_active_user, require_admin
from .schemas import ProductPayload, ProductUpdateRequest
from .utils import get_main_module

router = APIRouter(prefix="/products", tags=["products"])


def fetch_products() -> list[ProductPayload]:
    sql = """
        SELECT
            p.id,
            p.nom,
            p.categorie,
            COALESCE(p.prix_vente, 0) AS prix_vente,
            p.prix_achat,
            p.stock_actuel,
            p.tva
        FROM produits p
        ORDER BY p.nom ASC
    """
    df = query_df(sql)
    if df.empty:
        return []
    return [ProductPayload(**record) for record in df.to_dict("records")]


def load_active_products_map(product_ids: Iterable[int]) -> dict[int, dict[str, object]]:
    ids = list(product_ids)
    if not ids:
        return {}
    placeholders = ", ".join(f":pid_{index}" for index, _ in enumerate(ids))
    params = {f"pid_{index}": pid for index, pid in enumerate(ids)}
    sql = text(
        f"""
        SELECT id,
               nom,
               COALESCE(prix_vente, 0) AS prix_vente,
               COALESCE(tva, 0) AS tva
        FROM produits
        WHERE id IN ({placeholders})
          AND (actif IS NULL OR actif = TRUE)
    """
    )
    df = query_df(sql, params)
    if df.empty:
        return {}
    return {int(row["id"]): dict(row) for row in df.to_dict("records")}


@router.get("", response_model=list[ProductPayload])
def list_products(_: dict = Depends(get_current_active_user)) -> list[ProductPayload]:
    return get_main_module()._fetch_products()


@router.patch("/{product_id}")
def update_product(product_id: int, payload: ProductUpdateRequest, _: dict = Depends(require_admin)) -> dict:
    updates = {
        key: value
        for key, value in payload.model_dump(exclude={"barcodes"}).items()
        if value is not None
    }
    try:
        result = get_main_module().update_catalog_entry(product_id, updates, payload.barcodes)
    except ProductNotFoundError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidBarcodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "updated", "result": result}

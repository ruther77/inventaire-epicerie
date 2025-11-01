"""Inventory reporting endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from data_repository import query_df

from ..security import get_current_active_user

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _compute_inventory_value() -> dict[str, float]:
    sql = """
        SELECT
            SUM(COALESCE(prix_achat, 0) * COALESCE(stock_actuel, 0)) AS total_achat,
            SUM(COALESCE(prix_vente, 0) * COALESCE(stock_actuel, 0)) AS total_vente
        FROM produits
    """
    df = query_df(sql)
    if df.empty:
        return {"total_purchase_value": 0.0, "total_sale_value": 0.0}
    row = df.iloc[0]
    return {
        "total_purchase_value": float(row.get("total_achat") or 0),
        "total_sale_value": float(row.get("total_vente") or 0),
    }


@router.get("/summary")
def read_inventory_summary(_: dict = Depends(get_current_active_user)) -> dict[str, float]:
    return _compute_inventory_value()

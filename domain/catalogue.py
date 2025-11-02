"""Catalogue-related domain helpers shared across clients."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from data_repository import query_df
from product_service import (
    InvalidBarcodeError,
    ProductNotFoundError,
    delete_product_by_barcode as _delete_product_by_barcode,
    update_catalog_entry as _update_catalog_entry,
)
from sqlalchemy import text


def fetch_products(include_inactive: bool = False, search: str | None = None) -> list[dict[str, Any]]:
    """Return the product catalogue optionally filtered by activity or search term."""

    segments = [
        "SELECT",
        "    p.id,",
        "    p.nom,",
        "    p.categorie,",
        "    COALESCE(p.prix_vente, 0) AS prix_vente,",
        "    p.prix_achat,",
        "    COALESCE(p.stock_actuel, 0) AS stock_actuel,",
        "    COALESCE(p.tva, 0) AS tva,",
        "    COALESCE(p.actif, 1) AS actif",
        "FROM produits p",
    ]

    params: dict[str, Any] = {}
    conditions: list[str] = []

    if not include_inactive:
        conditions.append("(p.actif IS NULL OR p.actif = 1)")

    if search:
        term = search.strip()
        if term:
            params["search_name"] = f"%{term.lower()}%"
            params["search_barcode"] = f"%{term}%"
            conditions.append(
                "(LOWER(p.nom) LIKE :search_name OR EXISTS ("
                "    SELECT 1 FROM produits_barcodes pb"
                "    WHERE pb.produit_id = p.id AND pb.code LIKE :search_barcode"
                "))"
            )

    if conditions:
        segments.append("WHERE " + " AND ".join(conditions))

    segments.append("ORDER BY p.nom ASC")
    sql = "\n".join(segments)

    df = query_df(sql, params)
    if df.empty:
        return []
    records = []
    for record in df.to_dict("records"):
        entry = dict(record)
        entry.pop("actif", None)
        records.append(entry)
    return records


def load_active_products_map(product_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    """Return active products keyed by their identifier."""

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


def update_catalog_entry(
    product_id: int,
    field_changes: Mapping[str, Any] | None,
    barcode_field: str | Iterable[str] | None = None,
) -> dict[str, Any]:
    """Apply catalogue updates using the underlying product service."""

    return _update_catalog_entry(product_id, field_changes, barcode_field)


def delete_product_by_barcode(raw_code: str | None) -> dict[str, Any]:
    """Delete a product or barcode via the underlying product service."""

    return _delete_product_by_barcode(raw_code)


__all__ = [
    "InvalidBarcodeError",
    "ProductNotFoundError",
    "delete_product_by_barcode",
    "fetch_products",
    "load_active_products_map",
    "update_catalog_entry",
]

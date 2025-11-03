"""Shared analytical queries for inventory dashboards and UIs."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from data_repository import query_df


def fetch_customer_catalog_dataframe() -> pd.DataFrame:
    """Return the customer-facing catalogue with aggregated metrics."""

    sql_query = """
        SELECT
            p.id,
            p.nom,
            p.categorie,
            COALESCE(p.prix_achat, 0) AS prix_achat,
            COALESCE(p.prix_vente, 0) AS prix_vente,
            COALESCE(p.stock_actuel, 0) AS stock_actuel,
            COALESCE(tv.qte_sorties_30j, 0) AS ventes_30j,
            barcode.code AS ean
        FROM produits p
        LEFT JOIN v_top_ventes_30j tv ON tv.id = p.id
        LEFT JOIN LATERAL (
            SELECT pb.code
            FROM produits_barcodes pb
            WHERE pb.produit_id = p.id
            ORDER BY pb.is_principal DESC, pb.created_at ASC, pb.id ASC
            LIMIT 1
        ) AS barcode ON TRUE
        WHERE p.actif = TRUE
        ORDER BY p.categorie, p.nom;
    """
    return query_df(sql_query)


def fetch_recent_suppliers_dataframe() -> pd.DataFrame:
    """Return the most recent supplier associated with each product."""

    sql = """
        SELECT DISTINCT ON (m.produit_id)
            m.produit_id,
            COALESCE(NULLIF(TRIM(m.source), ''), 'Non renseigné') AS fournisseur,
            m.date_mvt
        FROM mouvements_stock m
        WHERE m.type = 'ENTREE'
        ORDER BY m.produit_id, m.date_mvt DESC
    """
    return query_df(sql)


def fetch_duplicate_barcodes_dataframe() -> pd.DataFrame:
    """Return duplicated barcodes with the associated products."""

    sql = """
        SELECT
            LOWER(pb.code) AS code,
            COUNT(*) AS occurrences,
            string_agg(p.nom, ', ' ORDER BY p.nom) AS produits
        FROM produits_barcodes pb
        JOIN produits p ON p.id = pb.produit_id
        GROUP BY LOWER(pb.code)
        HAVING COUNT(*) > 1
        ORDER BY occurrences DESC, code
    """
    return query_df(sql)


def fetch_products_list_dataframe() -> pd.DataFrame:
    """Return the enriched product list including barcodes."""

    sql_query = """
        SELECT
            p.id,
            p.nom,
            COALESCE(p.prix_achat, 0) AS prix_achat,
            p.prix_vente,
            p.tva,
            COALESCE(p.categorie::text, 'Non renseignée') AS categorie,
            COALESCE(p.stock_actuel, 0) AS stock_actuel,
            COALESCE(p.stock_actuel, 0) AS quantite_stock,
            COALESCE(string_agg(pb.code, ', ' ORDER BY pb.code), '') AS codes_barres
        FROM produits p
        LEFT JOIN produits_barcodes pb ON p.id = pb.produit_id
        GROUP BY p.id, p.nom, p.prix_vente, p.tva, p.stock_actuel, p.categorie
        ORDER BY p.nom;
    """
    return query_df(sql_query)


def fetch_movement_timeseries(window_days: int, product_id: int | None = None) -> pd.DataFrame:
    """Return aggregated movements for the given time window and optional product."""

    base_sql = """
        SELECT
            date_trunc('day', m.date_mvt) AS jour,
            m.type,
            SUM(m.quantite) AS quantite
        FROM mouvements_stock m
        WHERE m.date_mvt >= now() - (:window * INTERVAL '1 day')
    """
    params: dict[str, int] = {"window": int(window_days)}

    if product_id is not None:
        base_sql += " AND m.produit_id = :product_id"
        params["product_id"] = int(product_id)

    base_sql += " GROUP BY jour, m.type ORDER BY jour ASC"

    return query_df(base_sql, params=params)


def fetch_recent_movements(limit: int, product_id: int | None = None) -> pd.DataFrame:
    """Return the most recent stock movements with optional filtering."""

    sql = [
        "SELECT id, produit_id, type, quantite, source, date_mvt",
        "FROM mouvements_stock",
    ]
    params: dict[str, int] = {}

    if product_id is not None:
        sql.append("WHERE produit_id = :product_id")
        params["product_id"] = int(product_id)

    sql.append("ORDER BY date_mvt DESC, id DESC LIMIT :limit")
    params["limit"] = max(1, int(limit))

    return query_df("\n".join(sql), params=params)


def preview_table_dataframe(table_name: str, limit: int) -> pd.DataFrame:
    """Return a preview of a whitelisted table."""

    allowed = {"produits", "produits_barcodes", "mouvements_stock"}
    if table_name not in allowed:
        raise ValueError(f"Table non autorisée pour l'aperçu: {table_name}")

    limit_value = max(1, int(limit))
    sql = text(f"SELECT * FROM public.{table_name} ORDER BY id DESC LIMIT {limit_value}")
    return query_df(sql)


def count_table_rows_dataframe() -> pd.DataFrame:
    """Return the row counts for the main inventory tables."""

    sql = """
        SELECT 'produits' AS table, COUNT(*) AS lignes FROM produits
        UNION ALL
        SELECT 'produits_barcodes' AS table, COUNT(*) AS lignes FROM produits_barcodes
        UNION ALL
        SELECT 'mouvements_stock' AS table, COUNT(*) AS lignes FROM mouvements_stock
    """
    return query_df(sql)


def compute_stock_diagnostics_dataframe() -> pd.DataFrame:
    """Return stock reconciliation diagnostics."""

    sql = """
        WITH stock_compare AS (
            SELECT
                p.id,
                p.nom,
                p.stock_actuel,
                COALESCE(SUM(CASE
                    WHEN m.type = 'ENTREE' THEN m.quantite
                    WHEN m.type = 'SORTIE' THEN -m.quantite
                    WHEN m.type = 'INVENTAIRE' THEN m.quantite
                    WHEN m.type = 'TRANSFERT' THEN m.quantite
                    ELSE 0
                END), 0) AS stock_calcule
            FROM produits p
            LEFT JOIN mouvements_stock m ON m.produit_id = p.id
            GROUP BY p.id, p.nom, p.stock_actuel
        )
        SELECT
            id,
            nom,
            stock_actuel,
            stock_calcule,
            ROUND(stock_actuel - stock_calcule, 3) AS ecart
        FROM stock_compare
        WHERE ABS(stock_actuel - stock_calcule) > 0.001
        ORDER BY ABS(stock_actuel - stock_calcule) DESC, nom
    """
    return query_df(sql)


def fetch_stock_kpis() -> pd.DataFrame:
    """Return aggregated KPI metrics for the dashboard."""

    sql = """
        SELECT
            COUNT(id) AS total_produits,
            SUM(quantite_stock * prix_vente) AS valeur_stock_ht,
            SUM(quantite_stock) AS quantite_stock_total,
            SUM(CASE WHEN quantite_stock <= 5 AND quantite_stock > 0 THEN 1 ELSE 0 END) AS alerte_stock_bas,
            SUM(CASE WHEN quantite_stock = 0 THEN 1 ELSE 0 END) AS stock_epuise
        FROM v_stock_produits
    """
    return query_df(sql)


def fetch_top_stock_value_products(limit: int = 5) -> pd.DataFrame:
    """Return the products with the highest stock value."""

    sql = text(
        """
        SELECT nom, (quantite_stock * prix_vente) as valeur_stock
        FROM v_stock_produits
        ORDER BY valeur_stock DESC
        LIMIT :limit
        """
    )
    return query_df(sql, {"limit": max(1, int(limit))})


def fetch_top_sales_products(limit: int = 5) -> pd.DataFrame:
    """Return the top selling products based on stock movements."""

    sql = text(
        """
        SELECT
            p.nom,
            SUM(m.quantite) AS quantite_vendue
        FROM mouvements_stock m
        JOIN produits p ON m.produit_id = p.id
        WHERE m.type = 'SORTIE'
        GROUP BY p.nom
        ORDER BY quantite_vendue DESC
        LIMIT :limit
        """
    )
    return query_df(sql, {"limit": max(1, int(limit))})


def lookup_product_name_by_barcode(code: str) -> str | None:
    """Return the product name associated with the provided barcode."""

    sanitized = (code or "").strip()
    if not sanitized:
        return None

    df = query_df(
        text(
            """
            SELECT p.nom
            FROM produits p
            JOIN produits_barcodes pb ON p.id = pb.produit_id
            WHERE pb.code = :code
            LIMIT 1
            """
        ),
        {"code": sanitized},
    )
    if df.empty:
        return None
    return str(df.iloc[0]["nom"])


__all__ = [
    "fetch_customer_catalog_dataframe",
    "fetch_recent_suppliers_dataframe",
    "fetch_duplicate_barcodes_dataframe",
    "fetch_products_list_dataframe",
    "fetch_movement_timeseries",
    "fetch_recent_movements",
    "preview_table_dataframe",
    "count_table_rows_dataframe",
    "compute_stock_diagnostics_dataframe",
    "fetch_stock_kpis",
    "fetch_top_stock_value_products",
    "fetch_top_sales_products",
    "lookup_product_name_by_barcode",
]

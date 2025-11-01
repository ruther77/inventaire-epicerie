"""Stock related data loaders used by the Streamlit workspace."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from domain import (
    compute_stock_diagnostics_dataframe,
    count_table_rows_dataframe,
    fetch_movement_timeseries,
    fetch_products_list_dataframe,
    fetch_recent_movements,
    preview_table_dataframe,
)

from .cache import register_cache


@st.cache_data(ttl=300)
def load_products_list() -> pd.DataFrame:
    """Return the enriched product list used across tabs."""

    df = fetch_products_list_dataframe()
    if "prix_achat" not in df.columns:
        df["prix_achat"] = 0.0
    if "categorie" not in df.columns:
        df["categorie"] = "Non renseignée"
    if "stock_actuel" not in df.columns:
        df["stock_actuel"] = df.get("quantite_stock", 0)
    if "quantite_stock" not in df.columns:
        df["quantite_stock"] = df.get("stock_actuel", 0)

    def _stock_status(value: Any) -> str:
        try:
            qty = float(value)
        except (TypeError, ValueError):
            qty = 0.0
        if qty > 5:
            return "Stock OK"
        if qty > 0:
            return "Alerte Basse"
        return "Épuisé"

    df["statut_stock"] = df["quantite_stock"].apply(_stock_status)
    return df


@st.cache_data(ttl=120)
def load_movement_timeseries(window_days: int = 30, product_id: int | None = None) -> pd.DataFrame:
    """Return aggregated stock movements."""

    return fetch_movement_timeseries(window_days, product_id)


@st.cache_data(ttl=120)
def load_recent_movements(limit: int = 100, product_id: int | None = None) -> pd.DataFrame:
    """Return the most recent stock movements."""

    return fetch_recent_movements(limit, product_id)


@st.cache_data(ttl=60)
def load_table_preview(table_name: str, limit: int = 20) -> pd.DataFrame:
    """Return an excerpt of a whitelisted table."""

    try:
        return preview_table_dataframe(table_name, limit)
    except ValueError as exc:
        st.warning(str(exc))
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_table_counts() -> pd.DataFrame:
    """Return row counts for key tables."""

    return count_table_rows_dataframe()


@st.cache_data(ttl=60)
def load_stock_diagnostics() -> pd.DataFrame:
    """Return stock vs movement diagnostics."""

    return compute_stock_diagnostics_dataframe()


register_cache("products_list", load_products_list)
register_cache("movement_timeseries", load_movement_timeseries)
register_cache("recent_movements", load_recent_movements)
register_cache("table_preview", load_table_preview)
register_cache("table_counts", load_table_counts)
register_cache("stock_diagnostics", load_stock_diagnostics)


__all__ = [
    "load_movement_timeseries",
    "load_products_list",
    "load_recent_movements",
    "load_stock_diagnostics",
    "load_table_counts",
    "load_table_preview",
]

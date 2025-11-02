"""Streamlit entrypoint for the workspace application."""

from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from data_repository import query_df
from streamlit_app.pages.workspace import render_app


@st.cache_data(ttl=60)
def load_table_preview(table_name: str, limit: int | str = 20) -> pd.DataFrame:
    """Fetch a small excerpt of a table for the admin dashboard preview."""

    try:
        safe_limit = int(limit)
    except (TypeError, ValueError):
        safe_limit = 20
    if safe_limit <= 0:
        safe_limit = 20

    raw = str(table_name or "").strip()
    if not raw:
        st.warning("Table name is required")
        return pd.DataFrame()

    if "." in raw:
        schema, name = raw.split(".", 1)
    else:
        schema, name = "public", raw

    def _is_valid(segment: str) -> bool:
        if not segment:
            return False
        first = segment[0]
        if not (first.isalpha() or first == "_"):
            return False
        for char in segment[1:]:
            if not (char.isalnum() or char == "_"):
                return False
        return True

    if not (_is_valid(schema) and _is_valid(name)):
        st.warning("Invalid table name")
        return pd.DataFrame()

    qualified_name = f"{schema}.{name}"

    sql = f"SELECT * FROM {qualified_name} ORDER BY id DESC LIMIT {safe_limit}"
    try:
        return query_df(sql)
    except Exception as exc:  # pragma: no cover - defensive, mirrors streamlit behaviour
        st.error(str(exc))
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_stock_diagnostics() -> pd.DataFrame:
    """Return the stock diagnostics ordered by discrepancy magnitude."""

    sql = (
        "SELECT id, nom, stock_actuel, stock_calcule, ecart "
        "FROM public.stock_diagnostics "
        "ORDER BY ABS(stock_actuel - stock_calcule) DESC, nom"
    )
    try:
        return query_df(sql)
    except Exception as exc:
        st.error(str(exc))
        return pd.DataFrame(columns=["id", "nom", "stock_actuel", "stock_calcule", "ecart"])
def to_float(x, default: float = 0.0, minv: float | None = None, maxv: float | None = None) -> float:
    """Convert monetary strings into floats while respecting optional bounds."""

    if x is None:
        return default

    try:
        if isinstance(x, float) and math.isnan(x):
            return default
    except Exception:
        return default

    sanitized = (
        str(x)
        .replace("€", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    try:
        value = float(sanitized)
    except Exception:
        return default

    if minv is not None:
        value = max(value, minv)
    if maxv is not None:
        value = min(value, maxv)
    return round(value, 4)


if __name__ == "__main__":  # pragma: no cover - entrypoint for ``streamlit run``
    render_app()


__all__ = [
    "load_stock_diagnostics",
    "load_table_preview",
    "render_app",
    "to_float",
]

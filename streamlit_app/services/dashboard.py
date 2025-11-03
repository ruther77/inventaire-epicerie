"""Dashboard oriented data loaders."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from domain import fetch_stock_kpis, fetch_top_sales_products, fetch_top_stock_value_products

from .cache import register_cache


@st.cache_data(ttl=60)
def load_stock_kpis() -> pd.DataFrame:
    """Return the aggregated stock KPIs."""

    return fetch_stock_kpis()


@st.cache_data(ttl=60)
def load_top_stock_value(limit: int = 5) -> pd.DataFrame:
    """Return the top products by stock value."""

    return fetch_top_stock_value_products(limit)


@st.cache_data(ttl=60)
def load_top_sales(limit: int = 5) -> pd.DataFrame:
    """Return the top selling products."""

    return fetch_top_sales_products(limit)


register_cache("dashboard_kpis", load_stock_kpis)
register_cache("dashboard_top_stock", load_top_stock_value)
register_cache("dashboard_top_sales", load_top_sales)


__all__ = ["load_stock_kpis", "load_top_sales", "load_top_stock_value"]

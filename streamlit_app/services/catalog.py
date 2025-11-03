"""Catalogue related data loaders used by the Streamlit workspace."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter, Retry

from data_repository import get_product_options
from domain import (
    fetch_customer_catalog_dataframe,
    fetch_duplicate_barcodes_dataframe,
    fetch_recent_suppliers_dataframe,
    lookup_product_name_by_barcode,
)

from .cache import register_cache

_IMAGE_REQUEST_RETRIES = Retry(
    total=2,
    read=2,
    connect=2,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 503, 504),
)
_IMAGE_SESSION = requests.Session()
_IMAGE_SESSION.headers.update(
    {
        "User-Agent": "Inventaire-Streamlit/1.0 (https://inventaire-epicerie.fr)",
        "Accept": "application/json",
    }
)
_IMAGE_SESSION.mount("https://", HTTPAdapter(max_retries=_IMAGE_REQUEST_RETRIES))
_IMAGE_SESSION.mount("http://", HTTPAdapter(max_retries=_IMAGE_REQUEST_RETRIES))


@lru_cache(maxsize=128)
def _fetch_product_image_url(ean: Any) -> str | None:
    if ean is None:
        return None

    sanitized = str(ean).strip()
    if not sanitized:
        return None

    if not sanitized.isdigit():
        return None

    if len(sanitized) < 8:
        return None

    api_url = f"https://world.openfoodfacts.org/api/v0/product/{sanitized}.json"

    try:
        response = _IMAGE_SESSION.get(api_url, timeout=(2, 5))
    except requests.RequestException:
        return None

    if not response.ok:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    if not isinstance(payload, dict) or payload.get("status") != 1:
        return None

    product = payload.get("product") or {}
    preferred_keys = (
        "image_front_small_url",
        "image_small_url",
        "image_front_url",
        "image_url",
    )

    for key in preferred_keys:
        url = product.get(key)
        if url:
            return str(url)

    return None


@st.cache_data(ttl=180)
def load_customer_catalog() -> pd.DataFrame:
    """Return the curated customer-facing catalogue."""

    df = fetch_customer_catalog_dataframe()
    if df.empty:
        return df.assign(
            categorie=[], prix_vente=[], stock_actuel=[], ventes_30j=[]
        )

    expected_cols = {"categorie", "prix_achat", "prix_vente", "stock_actuel", "ventes_30j"}
    for col in expected_cols:
        if col not in df.columns:
            df[col] = 0

    numeric_cols = ["prix_achat", "prix_vente", "stock_actuel", "ventes_30j"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)

    if "categorie" in df.columns:
        df["categorie"] = df["categorie"].fillna("Autre")
    else:
        df["categorie"] = "Autre"

    if "ean" in df.columns:
        df["ean"] = df["ean"].fillna("").astype(str)
    else:
        df["ean"] = ""

    unique_eans = {
        ean.strip()
        for ean in df["ean"].tolist()
        if isinstance(ean, str) and ean.strip()
    }
    image_map: dict[str, str | None] = {}
    if unique_eans:
        for ean in unique_eans:
            image_map[ean] = _fetch_product_image_url(ean)
    df["image_url"] = df["ean"].map(lambda e: image_map.get(e) if e else None)

    return df


@st.cache_data(ttl=300)
def load_recent_suppliers() -> pd.DataFrame:
    """Return the latest supplier seen in stock movements."""

    df = fetch_recent_suppliers_dataframe()
    if not df.empty and "fournisseur" in df.columns:
        df["fournisseur"] = df["fournisseur"].fillna("Non renseigné")
    return df


@st.cache_data(ttl=300)
def load_duplicate_barcodes() -> pd.DataFrame:
    """Return duplicated barcodes for audit purposes."""

    df = fetch_duplicate_barcodes_dataframe()
    return df


@st.cache_data(ttl=120)
def load_trending_products(limit: int = 6) -> pd.DataFrame:
    """Return the top selling products based on the cached catalogue."""

    try:
        safe_limit = max(1, int(limit))
    except (TypeError, ValueError):
        safe_limit = 6

    catalog_df = load_customer_catalog()
    if catalog_df.empty:
        return catalog_df

    ranked = catalog_df.sort_values(
        by=["ventes_30j", "stock_actuel", "prix_vente"],
        ascending=[False, False, False],
    ).head(safe_limit)

    return ranked.reset_index(drop=True)


@st.cache_data(ttl=300)
def cached_product_options() -> dict[str, int]:
    """Return a cached mapping between product names and ids for selectors."""

    return {name: pid for name, pid in get_product_options()}


@st.cache_data(ttl=30)
def lookup_product_name(barcode: str) -> str | None:
    """Return the product name for a given barcode when available."""

    return lookup_product_name_by_barcode(barcode)


register_cache("catalog", load_customer_catalog)
register_cache("trending", load_trending_products)
register_cache("product_options", cached_product_options)
register_cache("recent_suppliers", load_recent_suppliers)
register_cache("duplicate_barcodes", load_duplicate_barcodes)


__all__ = [
    "cached_product_options",
    "load_customer_catalog",
    "load_duplicate_barcodes",
    "load_recent_suppliers",
    "load_trending_products",
    "lookup_product_name",
]

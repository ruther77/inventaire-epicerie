"""Shared cache helpers used across Streamlit services."""

from __future__ import annotations

from typing import Any, Callable, Dict

import streamlit as st

CACHE_REGISTRY: Dict[str, Callable[..., Any]] = {}


def register_cache(name: str, func: Callable[..., Any]) -> None:
    """Register a cached callable for coordinated invalidation."""

    CACHE_REGISTRY[name] = func


def invalidate_data_caches(*names: str) -> None:
    """Clear the selected caches to keep data fresh across the UI."""

    targets = names or tuple(CACHE_REGISTRY.keys())
    for cache_name in targets:
        cache_func = CACHE_REGISTRY.get(cache_name)
        if cache_func is None:
            continue
        try:
            cache_func.clear()
        except Exception as exc:  # pragma: no cover - Streamlit clears swallow errors
            st.warning(
                f"Impossible de vider le cache '{cache_name}'. Détail: {exc}",
                icon="⚠️",
            )


__all__ = ["CACHE_REGISTRY", "invalidate_data_caches", "register_cache"]

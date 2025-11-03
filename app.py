"""Streamlit entrypoint for the workspace application."""

from __future__ import annotations

import math
from typing import List

import pandas as pd
import streamlit as st

import invoice_extractor
from data_repository import query_df
from inventory_service import apply_invoice_price_updates, prepare_invoice_price_updates
from streamlit_app.pages.workspace import render_app as render_workspace_app
from streamlit_app.services.cache import invalidate_data_caches


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


def _reset_metro_invoice_state() -> None:
    """Remove cached state for the Metro invoice price updater."""

    st.session_state.pop("metro_invoice_df", None)
    st.session_state.pop("metro_invoice_raw_text", None)
    st.session_state.pop("metro_invoice_source_name", None)


def _get_invoice_dataframe() -> pd.DataFrame | None:
    """Return the currently cached Metro invoice dataframe if available."""

    invoice_df = st.session_state.get("metro_invoice_df")
    if isinstance(invoice_df, pd.DataFrame) and not invoice_df.empty:
        return invoice_df
    return None


def _display_invoice_preview(invoice_df: pd.DataFrame) -> None:
    """Render a compact preview of the parsed invoice lines."""

    if invoice_df.empty:
        return

    display_columns: List[str] = [
        "nom",
        "codes",
        "qte_init",
        "prix_achat",
        "montant_total_facture",
    ]
    available_columns = [col for col in display_columns if col in invoice_df.columns]
    st.dataframe(
        invoice_df[available_columns],
        hide_index=True,
        use_container_width=True,
        column_config={
            "nom": st.column_config.TextColumn("Produit"),
            "codes": st.column_config.TextColumn("EAN"),
            "qte_init": st.column_config.NumberColumn("Quantité", format="%.2f"),
            "prix_achat": st.column_config.NumberColumn("Prix unitaire TTC (€)", format="%.2f"),
            "montant_total_facture": st.column_config.NumberColumn(
                "Montant total (€)", format="%.2f"
            ),
        },
    )


def render_invoice_price_update_tool() -> None:
    """Standalone interface to update catalogue prices from a Metro invoice."""

    st.title("Mise à jour des tarifs METRO")
    st.write(
        "Téléversez une facture METRO pour rapprocher automatiquement les produits du "
        "catalogue grâce au code-barres EAN. Les prix de vente sont recalculés avec une "
        "marge minimale de 40 % et appliqués uniquement si l'écart dépasse 10 % par rapport "
        "aux tarifs actuels."
    )

    upload_col, text_col = st.columns(2)
    uploaded_invoice = upload_col.file_uploader(
        "Déposer la facture METRO (PDF, DOCX ou TXT)",
        type=["pdf", "doc", "docx", "txt"],
        key="metro_invoice_upload",
    )
    manual_text = text_col.text_area(
        "Ou collez directement la section produits de la facture",
        key="metro_invoice_text",
        height=220,
        placeholder="Collez le tableau des produits METRO ici...",
    )

    action_cols = st.columns([1, 1, 1])
    analyse_clicked = action_cols[0].button("Analyser la facture", key="metro_invoice_analyse")
    reset_clicked = action_cols[1].button("Réinitialiser", key="metro_invoice_reset")

    if reset_clicked:
        _reset_metro_invoice_state()
        st.success("Facture réinitialisée. Déposez un nouveau fichier pour recommencer.")
        st.rerun()

    if analyse_clicked:
        raw_text = ""
        if uploaded_invoice is not None:
            try:
                raw_text = invoice_extractor.extract_text_from_file(uploaded_invoice) or ""
                st.session_state["metro_invoice_source_name"] = uploaded_invoice.name
            except Exception as exc:  # pragma: no cover - depends on optional deps
                st.error(f"Impossible de lire le fichier de facture: {exc}")
                raw_text = ""
        elif manual_text.strip():
            raw_text = manual_text

        if not raw_text.strip():
            st.warning("Veuillez fournir un fichier ou un texte de facture contenant des produits.")
        else:
            try:
                parsed_df = invoice_extractor.extract_products_from_metro_invoice(raw_text)
            except Exception as exc:  # pragma: no cover - dépend des entrées utilisateurs
                st.error(f"Échec de l'analyse de la facture: {exc}")
            else:
                if parsed_df.empty:
                    st.warning("Aucune ligne produit n'a été détectée dans la facture fournie.")
                else:
                    st.session_state["metro_invoice_df"] = parsed_df
                    st.session_state["metro_invoice_raw_text"] = raw_text
                    st.success(
                        f"{len(parsed_df)} ligne(s) produit détectée(s) dans la facture METRO."
                    )

    invoice_df = _get_invoice_dataframe()
    if invoice_df is None:
        st.info(
            "Déposez une facture METRO ou collez les lignes produits pour lancer la mise à jour "
            "des tarifs."
        )
        return

    st.subheader("Lignes de facture interprétées")
    _display_invoice_preview(invoice_df)

    plan = prepare_invoice_price_updates(
        invoice_df,
        min_margin=0.40,
        delta_threshold=0.10,
    )

    if plan.get("errors"):
        for error_message in plan.get("errors", []):
            st.error(error_message)

    summary_cols = st.columns(3)
    summary_cols[0].metric("Produits rapprochés", plan.get("product_count", 0))
    summary_cols[1].metric("Mises à jour proposées", plan.get("updates_count", 0))
    summary_cols[2].metric("Lignes analysées", plan.get("matched_line_count", 0))

    updates_df = pd.DataFrame(plan.get("updates", []))
    if updates_df.empty:
        st.success("Aucun ajustement de prix n'est nécessaire : les tarifs actuels respectent la marge.")
    else:
        st.subheader("Tarifs à mettre à jour")
        display_columns = [
            "product_name",
            "ean",
            "current_purchase_price",
            "invoice_unit_price",
            "current_sale_price",
            "proposed_sale_price",
            "delta_percent",
        ]
        available_display = [col for col in display_columns if col in updates_df.columns]
        st.dataframe(
            updates_df[available_display],
            hide_index=True,
            use_container_width=True,
            column_config={
                "product_name": st.column_config.TextColumn("Produit"),
                "ean": st.column_config.TextColumn("EAN"),
                "current_purchase_price": st.column_config.NumberColumn(
                    "Achat actuel (€)", format="%.2f"
                ),
                "invoice_unit_price": st.column_config.NumberColumn(
                    "Achat facture TTC (€)", format="%.2f"
                ),
                "current_sale_price": st.column_config.NumberColumn(
                    "Vente actuelle (€)", format="%.2f"
                ),
                "proposed_sale_price": st.column_config.NumberColumn(
                    "Vente proposée (€)", format="%.2f"
                ),
                "delta_percent": st.column_config.NumberColumn("Delta (%)", format="%.1f"),
            },
        )

        if st.button("Appliquer les nouveaux tarifs", type="primary", key="metro_invoice_apply"):
            with st.spinner("Mise à jour des tarifs en cours..."):
                result = apply_invoice_price_updates(
                    invoice_df,
                    min_margin=0.40,
                    delta_threshold=0.10,
                )

            applied = int(result.get("applied_updates", 0))
            errors = result.get("errors", [])
            if applied:
                st.success(f"{applied} produit(s) ont été mis à jour selon la facture METRO.")
                invalidate_data_caches(
                    "products_list",
                    "catalog",
                    "trending",
                    "product_options",
                    "movement_timeseries",
                    "recent_movements",
                    "table_counts",
                    "table_preview",
                )
            if errors:
                for error_message in errors:
                    st.error(error_message)

    skipped_rows = plan.get("skipped", [])
    if skipped_rows:
        with st.expander("Produits conservés (écart inférieur à 10 %)"):
            skipped_df = pd.DataFrame(skipped_rows)
            keep_columns = [
                "product_name",
                "ean",
                "current_sale_price",
                "proposed_sale_price",
                "delta_percent",
                "reason",
            ]
            available = [col for col in keep_columns if col in skipped_df.columns]
            st.dataframe(
                skipped_df[available],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "current_sale_price": st.column_config.NumberColumn(
                        "Vente actuelle (€)", format="%.2f"
                    ),
                    "proposed_sale_price": st.column_config.NumberColumn(
                        "Vente proposée (€)", format="%.2f"
                    ),
                    "delta_percent": st.column_config.NumberColumn("Delta (%)", format="%.1f"),
                },
            )


def render_app() -> None:  # pragma: no cover - entrypoint for ``streamlit run``
    """Render the unified Streamlit application with Metro price updater."""

    st.set_page_config(page_title="Inventaire Épicerie", layout="wide", page_icon="📦")

    navigation = st.sidebar.radio(
        "Navigation",
        options=("Espace de pilotage", "Mise à jour tarifs METRO"),
        index=0,
    )

    if navigation == "Mise à jour tarifs METRO":
        render_invoice_price_update_tool()
    else:
        render_workspace_app(configure_page=False)


if __name__ == "__main__":  # pragma: no cover - entrypoint for ``streamlit run``
    render_app()


__all__ = [
    "load_stock_diagnostics",
    "load_table_preview",
    "render_app",
    "render_invoice_price_update_tool",
    "to_float",
]

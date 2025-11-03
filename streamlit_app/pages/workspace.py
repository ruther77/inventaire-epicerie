"""Main Streamlit workspace page implementing the unified UI."""

import os
import io
import math
from datetime import datetime
from html import escape as html_escape
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text
import streamlit_authenticator as stauth
import plotly.express as px
import invoice_extractor
from backup_manager import (
    BackupError,
    BinaryStatus,
    build_backup_timeline,
    check_backup_tools,
    compute_backup_statistics,
    create_backup,
    delete_backup,
    get_backup_directory,
    integrity_report,
    list_backups,
    load_backup_settings,
    plan_next_backup,
    restore_backup,
    save_backup_settings,
    suggest_retention_cleanup,
)

# Imports pour le Scanner et la Vidéo
import cv2 
from pyzbar.pyzbar import decode
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode, RTCConfiguration

# Importation des fonctions de gestion de la BDD et du chargeur 
from data_repository import (
    DATABASE_URL,
    exec_sql,
    exec_sql_return_id,
    get_engine,
    get_product_details,
)
from inventory_service import (
    apply_invoice_price_updates,
    match_invoice_products,
    prepare_invoice_price_updates,
    register_invoice_reception,
)
import products_loader
from product_service import parse_barcode_input
from domain import (
    InvalidBarcodeError,
    ProductNotFoundError,
    delete_product_by_barcode,
    process_sale_transaction,
    update_catalog_entry,
)
from streamlit_app.components.navigation import _PAGE_KEY_TO_INDEX
from streamlit_app.components.theme import THEME_LABELS, apply_ui_theme, local_css
from streamlit_app.services.cache import invalidate_data_caches
from streamlit_app.services.catalog import (
    cached_product_options,
    load_customer_catalog,
    load_duplicate_barcodes,
    load_recent_suppliers,
    load_trending_products,
    lookup_product_name,
    _fetch_product_image_url,
)
from streamlit_app.services.dashboard import (
    load_stock_kpis,
    load_top_sales,
    load_top_stock_value,
)
from streamlit_app.services.stock import (
    load_movement_timeseries,
    load_products_list,
    load_recent_movements,
    load_stock_diagnostics,
    load_table_counts,
    load_table_preview,
)

MAX_INVOICE_UPLOADS = 20
INVOICE_SELECTOR_KEYS = ("extract_invoice_selector", "import_invoice_selector")
INVOICE_FILE_UPLOADER_KEYS = (
    "extract_invoice_file_uploader",
    "import_invoice_file_uploader",
)


def _format_human_number(value: float | int, decimals: int = 0) -> str:
    """Formate un nombre en utilisant un séparateur fin non cassant."""

    return f"{value:,.{decimals}f}".replace(",", " ")


def _table_count_value(table_counts: pd.DataFrame | None, table_name: str) -> int | None:
    """Extract an integer count for the requested table if available."""

    if table_counts is None or table_counts.empty:
        return None
    try:
        matching = table_counts.loc[table_counts["table"] == table_name, "lignes"]
    except KeyError:
        return None
    if matching.empty:
        return None
    try:
        return int(matching.iloc[0])
    except (TypeError, ValueError):
        return None


def _format_overview_stat(raw_value: int | None) -> str:
    """Return a nicely formatted string for the overview statistics."""

    if raw_value is None:
        return "—"
    return _format_human_number(raw_value, 0)


def _tab_target_attr(page_key: str | None) -> str:
    """Return the data attributes allowing HTML buttons to switch Streamlit tabs."""

    if not page_key:
        return ""
    index = _PAGE_KEY_TO_INDEX.get(page_key)
    if index is None:
        return ""
    safe_key = html_escape(str(page_key))
    return f' data-tab-target="{index}" data-page-key="{safe_key}"'


def render_workspace_overview(
    *, user_name: str, user_role: str | None, table_counts: pd.DataFrame | None
) -> None:
    """Render the hero section aligning the workspace with the SPA design."""

    stats: List[Tuple[str, int | None]] = [
        ("Références catalogue", _table_count_value(table_counts, "produits")),
        ("Codes associés", _table_count_value(table_counts, "produits_barcodes")),
        ("Mouvements suivis", _table_count_value(table_counts, "mouvements_stock")),
    ]

    stats_markup = "".join(
        (
            "<div><dt>{label}</dt><dd>{value}</dd></div>".format(
                label=html_escape(label),
                value=_format_overview_stat(raw),
            )
            for label, raw in stats
        )
    )

    metrics_alert = ""
    if all(raw is None for _, raw in stats):
        metrics_alert = (
            "<p class=\"workspace-overview-card__subtitle workspace-overview-card__subtitle--warning\">"
            "Impossible de récupérer les métriques du catalogue pour le moment."
            "</p>"
        )

    name_fragment = html_escape(user_name.strip()) if user_name else "Invité"
    role_fragment = f" · {html_escape(user_role.strip())}" if user_role else ""

    dashboard_attrs = _tab_target_attr("dashboard")
    supply_attrs = _tab_target_attr("supply")
    catalog_attrs = _tab_target_attr("catalog")
    pos_attrs = _tab_target_attr("pos")
    showcase_attrs = _tab_target_attr("showcase")
    admin_attrs = _tab_target_attr("admin")

    hero_html = f"""
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" />
        <section class="workspace-overview workspace-overview--dropdown" data-workspace-overview>
            <header class="workspace-overview__intro">
                <span class="workspace-overview__eyebrow">Espace de pilotage</span>
                <h1 class="workspace-overview__title">Inventaire — Gestion complète</h1>
                <p class="workspace-overview__lead">Centralisez vos actions clés et naviguez rapidement entre les modules métier.</p>
                <p class="workspace-overview__welcome">Bonjour {name_fragment}{role_fragment}, choisissez un module pour continuer.</p>
                <dl class="workspace-overview__stats">
                    {stats_markup}
                </dl>
                {metrics_alert}
            </header>
            <div class="workspace-overview__body">
                <div class="workspace-modules">
                    <div class="workspace-modules__dropdown dropdown show" role="navigation" aria-label="Navigation principale">
                        <button class="workspace-modules__toggle" type="button" aria-haspopup="true" aria-expanded="true">
                            Modules & fonctionnalités
                            <span class="workspace-modules__chevron"><i class="bi bi-chevron-down" aria-hidden="true"></i></span>
                        </button>
                        <div class="workspace-modules__menu menu o_secondary nav" role="menu">
                            <div class="workspace-modules__group">
                                <p class="workspace-modules__group-title">Applications métier</p>
                                <ul class="workspace-modules__list">
                                    <li><a href="#" {showcase_attrs}>Vitrine produits</a></li>
                                    <li><a href="#" {supply_attrs}>Approvisionnement</a></li>
                                    <li><a href="#" {pos_attrs}>Vente (PoS)</a></li>
                                    <li><a href="#" {catalog_attrs}>Catalogue</a></li>
                                </ul>
                            </div>
                            <div class="workspace-modules__group">
                                <p class="workspace-modules__group-title">Support & pilotage</p>
                                <ul class="workspace-modules__list">
                                    <li><a href="#" {dashboard_attrs}>Tableau de bord</a></li>
                                    <li><a href="#" {admin_attrs}>Maintenance (Admin)</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div class="workspace-modules__grid">
                        <article class="workspace-module-card">
                            <header>
                                <h3>Vitrine produits</h3>
                                <p>Valorisez votre offre et surveillez les performances depuis la perspective client.</p>
                            </header>
                            <a class="workspace-module-card__cta" href="#" {showcase_attrs}>Accéder à la vitrine</a>
                        </article>
                        <article class="workspace-module-card">
                            <header>
                                <h3>Approvisionnement</h3>
                                <p>Gérez les commandes fournisseurs, les réceptions et les besoins de réassort.</p>
                            </header>
                            <a class="workspace-module-card__cta" href="#" {supply_attrs}>Ouvrir les approvisionnements</a>
                        </article>
                        <article class="workspace-module-card">
                            <header>
                                <h3>Vente (PoS)</h3>
                                <p>Encaissez rapidement et synchronisez les ventes avec votre inventaire.</p>
                            </header>
                            <a class="workspace-module-card__cta" href="#" {pos_attrs}>Lancer le PoS</a>
                        </article>
                        <article class="workspace-module-card">
                            <header>
                                <h3>Catalogue</h3>
                                <p>Maintenez vos fiches produits, variantes et rayons à jour en quelques clics.</p>
                            </header>
                            <a class="workspace-module-card__cta" href="#" {catalog_attrs}>Gérer le catalogue</a>
                        </article>
                        <article class="workspace-module-card">
                            <header>
                                <h3>Maintenance (Admin)</h3>
                                <p>Accédez aux outils techniques, sauvegardes et réglages critiques.</p>
                            </header>
                            <a class="workspace-module-card__cta" href="#" {admin_attrs}>Ouvrir l'administration</a>
                        </article>
                        <article class="workspace-module-card">
                            <header>
                                <h3>Tableau de bord</h3>
                                <p>Suivez vos indicateurs clés et comparez vos performances sur la période.</p>
                            </header>
                            <a class="workspace-module-card__cta" href="#" {dashboard_attrs}>Voir les indicateurs</a>
                        </article>
                    </div>
                </div>
            </div>
        </section>
        <script>
            (function () {{
                const rootDocument = window.parent?.document ?? document;
                if (!rootDocument) {{
                    return;
                }}

                const hero = rootDocument.querySelector('[data-workspace-overview]');
                if (!hero || hero.dataset.enhanced === 'true') {{
                    return;
                }}

                hero.dataset.enhanced = 'true';

                const getWorkspaceTabButtons = () =>
                    Array.from(rootDocument.querySelectorAll('[data-baseweb="tab"]'));

                const selectWorkspaceTab = (index) => {{
                    const tabButtons = getWorkspaceTabButtons();
                    const target = tabButtons?.[index];
                    if (target instanceof HTMLElement) {{
                        target.click();
                    }}
                }};

                const updateActiveLinks = (pageKey) => {{
                    if (!pageKey) {{
                        return;
                    }}

                    rootDocument.body?.setAttribute('data-current-page', pageKey);
                    hero.querySelectorAll('[data-page-key]').forEach((node) => {{
                        const isActive = node.getAttribute('data-page-key') === pageKey;
                        node.classList.toggle('is-active', isActive);
                        if (isActive) {{
                            node.setAttribute('aria-current', 'page');
                        }} else {{
                            node.removeAttribute('aria-current');
                        }}
                    }});
                }};

                const syncFromStreamlitTabs = () => {{
                    const tabButtons = getWorkspaceTabButtons();
                    const activeIndex = tabButtons.findIndex(
                        (tab) => tab.getAttribute('aria-selected') === 'true'
                    );
                    if (activeIndex >= 0) {{
                        const activeLink = hero.querySelector(
                            `[data-tab-target="{{activeIndex}}"][data-page-key]`
                        );
                        const pageKey = activeLink?.getAttribute('data-page-key');
                        if (pageKey) {{
                            updateActiveLinks(pageKey);
                        }}
                    }}
                }};

                hero.querySelectorAll('[data-tab-target]').forEach((link) => {{
                    link.addEventListener('click', (event) => {{
                        const targetIndex = Number(link.getAttribute('data-tab-target'));
                        const pageKey = link.getAttribute('data-page-key');
                        if (Number.isFinite(targetIndex)) {{
                            event.preventDefault();
                            selectWorkspaceTab(targetIndex);
                        }}
                        if (pageKey) {{
                            updateActiveLinks(pageKey);
                        }}
                    }});
                }});

                if (rootDocument.body) {{
                    const marker = 'workspaceTabsListener';
                    if (rootDocument.body.dataset[marker] !== 'true') {{
                        rootDocument.body.dataset[marker] = 'true';
                        rootDocument.addEventListener('click', (event) => {{
                            const target = event.target;
                            if (target && typeof target.closest === 'function') {{
                                const tab = target.closest('[data-baseweb="tab"]');
                                if (tab && getWorkspaceTabButtons().includes(tab)) {{
                                    window.requestAnimationFrame(syncFromStreamlitTabs);
                                }}
                            }}
                        }});
                    }}
                }}

                syncFromStreamlitTabs();
            }})();
        </script>
    """


    st.markdown(hero_html, unsafe_allow_html=True)

def _render_product_cards(
    dataframe: pd.DataFrame,
    *,
    columns: int = 3,
    coverage_target: float | None = None,
    alert_threshold: float | None = None,
) -> None:
    """Affiche une grille de cartes produits avec les informations clés."""

    if dataframe is None or dataframe.empty:
        st.caption("Aucun produit à afficher pour l'instant.")
        return

    try:
        per_row = max(1, int(columns))
    except (TypeError, ValueError):
        per_row = 3

    def _coerce_number(value: Any) -> float | None:
        """Convertit une valeur en float lorsque c'est pertinent."""

        if value is None:
            return None
        if isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                return None
            return float(value)
        if isinstance(value, str):
            sanitized = value.strip()
            if not sanitized:
                return None
            try:
                parsed = float(sanitized.replace(",", "."))
            except ValueError:
                return None
            if math.isnan(parsed):
                return None
            return parsed
        return None

    records = dataframe.to_dict(orient="records")
    effective_target = _coerce_number(coverage_target)
    effective_alert = _coerce_number(alert_threshold)

    for start in range(0, len(records), per_row):
        row_records = records[start : start + per_row]
        cols = st.columns(len(row_records))

        for col, record in zip(cols, row_records):
            with col:
                name = str(record.get("nom", "Produit")).strip() or "Produit"
                category = str(record.get("categorie", "")).strip()
                ean = str(record.get("ean", "")).strip()
                price = _coerce_number(record.get("prix_vente"))
                stock = _coerce_number(record.get("stock_actuel"))
                ventes_30j = _coerce_number(record.get("ventes_30j"))
                ventes_jour = _coerce_number(record.get("ventes_jour"))
                coverage_days = _coerce_number(record.get("couverture_jours"))
                reorder_qty = _coerce_number(record.get("quantite_a_commander"))
                margin_pct = _coerce_number(record.get("marge_pct"))
                supplier = str(record.get("fournisseur", "")).strip()
                priority = str(record.get("niveau_priorite", "")).strip()

                image_url = record.get("image_url")
                if not image_url and ean:
                    image_url = _fetch_product_image_url(ean)

                if isinstance(image_url, str) and image_url.strip():
                    st.image(image_url, use_column_width=True)

                title_parts = [f"**{name}**"]
                if priority:
                    priority_lower = priority.lower()
                    badge_color = "blue"
                    if priority_lower == "critique":
                        badge_color = "red"
                    elif priority_lower == "tendue":
                        badge_color = "orange"
                    elif priority_lower == "surveillance":
                        badge_color = "violet"
                    title_parts.append(f":{badge_color}[{priority}]")
                st.markdown(" ".join(title_parts))

                if category:
                    st.caption(category)

                info_lines: List[str] = []
                if price is not None:
                    info_lines.append(f"Prix : {_format_human_number(price, 2)} €")
                if stock is not None:
                    info_lines.append(f"Stock : {_format_human_number(stock, 0)} u")
                if ventes_30j is not None:
                    info_lines.append(
                        f"Ventes (30 j) : {_format_human_number(ventes_30j, 0)} u"
                    )
                elif ventes_jour is not None:
                    info_lines.append(
                        f"Ventes / jour : {_format_human_number(ventes_jour, 2)} u"
                    )

                if info_lines:
                    st.write("\n".join(info_lines))

                if coverage_days is not None:
                    coverage_text = f"Couverture : {_format_human_number(coverage_days, 1)} j"
                    if effective_target is not None:
                        delta = coverage_days - effective_target
                        coverage_text += f" (Δ {delta:+.1f} j / objectif {effective_target:.0f} j)"
                    st.write(coverage_text)
                    if (
                        effective_alert is not None
                        and coverage_days <= effective_alert
                    ):
                        st.caption(":red[⚠️ Sous le seuil d’alerte]")

                if reorder_qty is not None and reorder_qty > 0:
                    reorder_text = f"À commander : {_format_human_number(reorder_qty, 0)} u"
                    if margin_pct is not None:
                        reorder_text += f" — Marge : {margin_pct:.1f} %"
                    st.markdown(f"**{reorder_text}**")

                if supplier and supplier.lower() != "non renseigné":
                    st.caption(f"Fournisseur : {supplier}")

                if ean:
                    st.caption(f"EAN : {ean}")

def render_workspace_hero(
    *,
    eyebrow: str,
    title: str,
    description: str,
    badges: List[str] | None = None,
    metrics: List[Dict[str, str]] | None = None,
    tone: str = "sunset",
) -> None:
    """Affiche un bandeau héro en utilisant des composants Streamlit natifs."""

    tone_palette = {
        "sunset": "orange",
        "citrus": "orange",
        "lagoon": "blue",
        "marine": "blue",
        "violet": "violet",
        "emerald": "green",
        "amber": "orange",
        "teal": "green",
        "slate": "violet",
    }
    accent_color = tone_palette.get(tone, "blue")

    container = st.container()
    with container:
        st.markdown(
            f":{accent_color}[{eyebrow}]",
        )
        st.markdown(f"## {title}")
        st.write(description)

        if badges:
            badge_text = " ".join(f":{accent_color}[{badge}]" for badge in badges if badge)
            if badge_text:
                st.markdown(badge_text)

        if metrics:
            cols = st.columns(len(metrics))
            for col, metric in zip(cols, metrics):
                label = str(metric.get("label", "")).strip() or "–"
                value = str(metric.get("value", "")).strip() or "–"
                hint = str(metric.get("hint", "")).strip()
                col.metric(label=label, value=value)
                if hint:
                    col.caption(hint)


@contextmanager
def workspace_panel(
    title: str | None = None,
    description: str | None = None,
    *,
    icon: str | None = None,
    accent: str | None = None,
):
    """Crée un conteneur de panneau stylisé en s'appuyant sur les conteneurs Streamlit."""

    accent_palette = {
        "violet": "violet",
        "blue": "blue",
        "green": "green",
        "orange": "orange",
        "citrus": "orange",
        "lagoon": "blue",
        "marine": "blue",
        "emerald": "green",
        "amber": "orange",
        "teal": "green",
        "slate": "violet",
    }
    accent_color = accent_palette.get(accent or "", "blue")

    container = st.container()
    with container:
        if title or description:
            heading = title or ""
            heading_display = f":{accent_color}[{heading}]" if heading else ""
            if icon:
                heading_display = f"{icon} {heading_display}" if heading_display else icon
            if heading_display:
                st.markdown(f"### {heading_display}")
            if description:
                st.caption(description)

        try:
            yield
        finally:
            pass

def _normalize_cart_dataframe(cart_items: List[Dict[str, Any]]) -> pd.DataFrame:
    """Construit un DataFrame propre à partir des éléments du panier."""

    if not cart_items:
        return pd.DataFrame(columns=["nom", "qty", "prix_vente", "tva"])

    cart_df = pd.DataFrame.from_records(cart_items)

    defaults = {"nom": "", "qty": 0, "prix_vente": 0.0, "tva": 0.0}
    for column, default in defaults.items():
        if column not in cart_df.columns:
            cart_df[column] = default

    cart_df["qty"] = pd.to_numeric(cart_df["qty"], errors="coerce").fillna(0).astype(int)
    cart_df["prix_vente"] = pd.to_numeric(cart_df["prix_vente"], errors="coerce").fillna(0.0)
    cart_df["tva"] = pd.to_numeric(cart_df["tva"], errors="coerce").fillna(0.0)

    return cart_df


def _ensure_cart_state() -> List[Dict[str, Any]]:
    """Garantit que le panier en session est une liste de dictionnaires."""

    raw_cart = st.session_state.get("cart", [])

    if isinstance(raw_cart, pd.DataFrame):
        cart_items: List[Dict[str, Any]] = raw_cart.to_dict(orient="records")
    elif isinstance(raw_cart, Mapping):
        cart_items = [dict(raw_cart)]
    elif isinstance(raw_cart, Iterable) and not isinstance(raw_cart, (str, bytes, bytearray)):
        cart_items = []
        for item in raw_cart:
            if isinstance(item, Mapping):
                cart_items.append(dict(item))
    else:
        cart_items = []

    st.session_state["cart"] = cart_items
    return cart_items


def _clear_cart() -> None:
    """Réinitialise complètement le panier courant."""

    st.session_state["cart"] = []


def _reset_pos_inputs() -> None:
    """Replace les champs du formulaire PoS dans leur état initial."""

    st.session_state["pos_product_selectbox"] = "-- Sélectionner un produit --"
    st.session_state["pos_qty_input"] = 1


def _add_product_to_cart(
    product_id: int,
    quantity: int,
    products_df: pd.DataFrame,
) -> Tuple[bool, str]:
    """Ajoute un produit au panier ou met à jour sa quantité."""

    if products_df is None or products_df.empty:
        return False, "Catalogue produits indisponible."

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return False, "Identifiant produit invalide."

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return False, "Quantité invalide."

    if quantity <= 0:
        return False, "La quantité doit être supérieure à zéro."

    product_row = products_df.loc[products_df["id"] == product_id]
    if product_row.empty:
        return False, "Produit introuvable dans le catalogue."

    product = product_row.iloc[0]
    product_name = str(product.get("nom", "")).strip() or f"Produit {product_id}"
    prix_vente = float(product.get("prix_vente", 0.0) or 0.0)
    tva = float(product.get("tva", 0.0) or 0.0)

    cart_items = _ensure_cart_state()

    for item in cart_items:
        try:
            item_id = int(item.get("id")) if item.get("id") is not None else None
        except (TypeError, ValueError):
            item_id = None

        if item_id == product_id:
            existing_qty = int(item.get("qty", 0) or 0)
            item["qty"] = existing_qty + quantity
            item["nom"] = product_name
            item["prix_vente"] = prix_vente
            item["tva"] = tva
            st.session_state["cart"] = cart_items
            return True, f"Quantité mise à jour pour {product_name} ({item['qty']})"

    new_item = {
        "id": product_id,
        "nom": product_name,
        "qty": quantity,
        "prix_vente": prix_vente,
        "tva": tva,
    }
    cart_items.append(new_item)
    st.session_state["cart"] = cart_items

    return True, f"{product_name} ajouté au panier ({quantity})"


def _reset_invoice_session_state() -> None:
    """Réinitialise toutes les variables de session liées aux factures."""

    st.session_state["invoice_raw_text"] = ""
    st.session_state["invoice_text_input"] = ""
    st.session_state["extract_invoice_text_input"] = ""
    st.session_state["import_invoice_text_input"] = ""
    st.session_state["invoice_products_df"] = None
    st.session_state["invoice_import_summary"] = None
    st.session_state["invoice_uploaded_name"] = "facture.txt"
    st.session_state["invoice_uploaded_batches"] = []
    st.session_state["invoice_processed_signatures"] = set()
    st.session_state["invoice_selection_index"] = None

    for selector_key in INVOICE_SELECTOR_KEYS:
        st.session_state.pop(selector_key, None)
        st.session_state.pop(f"{selector_key}__sync", None)

    for uploader_key in INVOICE_FILE_UPLOADER_KEYS:
        st.session_state.pop(uploader_key, None)


def _queue_invoice_selector_sync(index: int) -> None:
    for selector_key in INVOICE_SELECTOR_KEYS:
        st.session_state[f"{selector_key}__sync"] = index


def _set_active_invoice_from_index(index: int) -> None:
    batches = st.session_state.get("invoice_uploaded_batches", [])
    if not batches:
        st.session_state["invoice_selection_index"] = None
        return

    index = max(0, min(index, len(batches) - 1))
    batch = batches[index]

    st.session_state["invoice_raw_text"] = batch["text"]
    st.session_state["invoice_text_input"] = batch["text"]
    st.session_state["extract_invoice_text_input"] = batch["text"]
    st.session_state["import_invoice_text_input"] = batch["text"]
    st.session_state["invoice_products_df"] = None
    st.session_state["invoice_import_summary"] = None
    st.session_state["invoice_uploaded_name"] = batch["download_name"]
    st.session_state["invoice_selection_index"] = index

    _queue_invoice_selector_sync(index)


def _process_uploaded_invoices(uploaded_files, context_label: str) -> None:
    if not uploaded_files:
        return

    if not isinstance(uploaded_files, (list, tuple)):
        uploaded_files = [uploaded_files]

    if len(uploaded_files) > MAX_INVOICE_UPLOADS:
        st.info(f"Seuls les {MAX_INVOICE_UPLOADS} premiers fichiers seront traités.")

    processed_signatures = st.session_state.setdefault("invoice_processed_signatures", set())
    batches = st.session_state.setdefault("invoice_uploaded_batches", [])
    seen_signatures = set(processed_signatures)

    new_batches = []
    for uploaded_invoice_file in uploaded_files[:MAX_INVOICE_UPLOADS]:
        signature = f"{uploaded_invoice_file.name}|{getattr(uploaded_invoice_file, 'size', '0')}"
        if signature in seen_signatures:
            st.info(f"{uploaded_invoice_file.name} a déjà été traité.")
            continue

        try:
            raw_bytes = uploaded_invoice_file.getvalue()
        except Exception as exc:  # pragma: no cover - protection runtime Streamlit
            st.error(f"Erreur lors de la lecture du fichier {uploaded_invoice_file.name} : {exc}")
            continue

        proxy_file = io.BytesIO(raw_bytes)
        proxy_file.name = uploaded_invoice_file.name
        proxy_file.type = uploaded_invoice_file.type

        try:
            extracted_text = invoice_extractor.extract_text_from_file(proxy_file)
        except Exception as exc:  # pragma: no cover - protection runtime Streamlit
            st.error(f"Erreur lors de la lecture du fichier {uploaded_invoice_file.name} : {exc}")
            continue

        if extracted_text is None or not str(extracted_text).strip():
            st.warning(f"{uploaded_invoice_file.name} : aucun texte exploitable détecté.")
            continue

        if str(extracted_text).lower().startswith("erreur"):
            st.error(f"{uploaded_invoice_file.name} : {extracted_text}")
            continue

        base_name, _ = os.path.splitext(uploaded_invoice_file.name)
        safe_name = base_name or "facture"
        download_name = f"{safe_name}_extraction.txt"

        new_batches.append(
            {
                "name": uploaded_invoice_file.name,
                "text": extracted_text,
                "download_name": download_name,
                "signature": signature,
            }
        )
        seen_signatures.add(signature)
        st.success(f"Texte extrait depuis {uploaded_invoice_file.name} ({context_label}).")

    if not new_batches:
        return

    batches.extend(new_batches)
    if len(batches) > MAX_INVOICE_UPLOADS:
        batches[:] = batches[-MAX_INVOICE_UPLOADS:]

    processed_signatures.clear()
    processed_signatures.update(batch["signature"] for batch in batches)
    _set_active_invoice_from_index(len(batches) - 1)


def _render_invoice_selector(label: str, widget_key: str) -> None:
    batches = st.session_state.get("invoice_uploaded_batches", [])
    if not batches:
        return

    current_index = st.session_state.get("invoice_selection_index")
    if current_index is None or current_index >= len(batches):
        current_index = len(batches) - 1
        _set_active_invoice_from_index(current_index)

    pending_key = f"{widget_key}__sync"
    if pending_key in st.session_state:
        st.session_state[widget_key] = st.session_state.pop(pending_key)
    elif widget_key not in st.session_state:
        st.session_state[widget_key] = current_index

    options = list(range(len(batches)))

    selected_index = st.selectbox(
        label,
        options,
        format_func=lambda idx: batches[idx]["name"],
        key=widget_key,
    )

    if selected_index != st.session_state.get("invoice_selection_index"):
        _set_active_invoice_from_index(selected_index)
    
# --- Configuration de l'Authentification ---
SECRET_KEY = os.getenv("STREAMLIT_SECRET_KEY", "__auth_token_inventaire_secure_2025")

PASSWORD_HASHES = {
    "admin": os.getenv(
        "ADMIN_PASSWORD_HASH", "$2b$12$JA6jQijn5i21uQquBDOkR.gFIeXD82mri3DS0dcQ8HjB8.ycjYdI2"
    ),
    "user": os.getenv(
        "USER_PASSWORD_HASH", "$2b$12$onUKmKMoVtAfpr.Lus9iW.bz.Q69Y/Ylf8nfSPzSL/avBHqeuuvTi"
    ),
}

credentials = {
    "usernames": {
        "admin": {
            "email": "ulrich@inventaire.fr",
            "name": "ulrich",
            "password": PASSWORD_HASHES["admin"],
            "role": "admin"
        },
        "user": {
            "email": "user@inventaire.fr",
            "name": "user",
            "password": PASSWORD_HASHES["user"],
            "role": "standard"
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    'inventaire_cookie',
    SECRET_KEY,
    cookie_expiry_days=30
)

# --- Gestion de la persistance d'authentification ---

def authenticate_user() -> tuple[str | None, bool | None, str | None]:
    """Récupère l'état d'authentification en évitant de redemander inutilement."""

    if "authentication_status" not in st.session_state:
        st.session_state["authentication_status"] = None
    if "name" not in st.session_state:
        st.session_state["name"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "logout" not in st.session_state:
        st.session_state["logout"] = False

    stored_status = st.session_state.get("authentication_status")
    stored_name = st.session_state.get("name")
    stored_username = st.session_state.get("username")

    if stored_status and stored_name and stored_username and not st.session_state.get("logout"):
        return stored_name, True, stored_username

    name, authentication_status, username = authenticator.login('Connexion à l\'Inventaire', 'main')

    if authentication_status:
        st.session_state["authentication_status"] = True
        st.session_state["name"] = name
        st.session_state["username"] = username
        st.session_state["logout"] = False

    return name, authentication_status, username

# --- Fonctions Utilitaires et Caching ---

def to_float(x, default=0.0, minv=None, maxv=None):
    """Convertit une chaîne en float en gérant les formats monétaires et les NaN."""
    if x is None:
        return default
    try:
        if isinstance(x, float) and math.isnan(x):
            return default
    except Exception:
        pass
    s = str(x).replace("€","").replace("\xa0","").replace(" ","").replace(",", ".").strip()
    try:
        v = float(s)
        if minv is not None:
            v = max(v, minv)
        if maxv is not None:
            v = min(v, maxv)
        return round(v, 4)
    except Exception:
        return default


# --- Classe Barcode Detector (pour le Scanner) ---
class BarcodeDetector(VideoTransformerBase):
    """Détecte les codes-barres dans chaque frame vidéo. Déclenche le Rerun Streamlit."""
    
    SKIP_FRAMES = 5
    
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        st.session_state["current_frame_count"] += 1
        
        if st.session_state["current_frame_count"] % self.SKIP_FRAMES == 0:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            barcodes = decode(gray)
            
            for barcode in barcodes:
                barcode_data = barcode.data.decode("utf-8")
                
                if st.session_state["last_barcode"] != barcode_data:
                    st.session_state["last_barcode"] = barcode_data
                    st.rerun() 
                
                (x, y, w, h) = barcode.rect
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                text = f"{barcode_data}"
                cv2.putText(img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return img


# ==============================================================================
# --- DÉBUT DU FLUX PRINCIPAL (CONTRÔLE D'ACCÈS) ---
# ==============================================================================

def render_app() -> None:
    st.set_page_config(page_title="Inventaire Épicerie", layout="wide", page_icon="📦")
    local_css("style.css")
    if "ui_theme" not in st.session_state:
        st.session_state["ui_theme"] = "light"
    if "pos_receipt" not in st.session_state:
        st.session_state["pos_receipt"] = None
    st.session_state.setdefault("pos_product_selectbox", "-- Sélectionner un produit --")
    st.session_state.setdefault("pos_qty_input", 1)
    st.session_state.setdefault("_pos_processing_notice", False)
    if "last_barcode" not in st.session_state:
        st.session_state["last_barcode"] = None
    if "current_frame_count" not in st.session_state:
        st.session_state["current_frame_count"] = 0
    if "cart" not in st.session_state:
        st.session_state["cart"] = []
    if "pos_processing" not in st.session_state:
        st.session_state["pos_processing"] = False
    if "invoice_raw_text" not in st.session_state:
        st.session_state["invoice_raw_text"] = ""
    if "invoice_text_input" not in st.session_state:
        st.session_state["invoice_text_input"] = ""
    if "invoice_products_df" not in st.session_state:
        st.session_state["invoice_products_df"] = None
    if "invoice_import_summary" not in st.session_state:
        st.session_state["invoice_import_summary"] = None
    if "invoice_uploaded_name" not in st.session_state:
        st.session_state["invoice_uploaded_name"] = "facture.txt"
    if "invoice_uploaded_batches" not in st.session_state:
        st.session_state["invoice_uploaded_batches"] = []
    if "invoice_selection_index" not in st.session_state:
        st.session_state["invoice_selection_index"] = None
    if "invoice_processed_signatures" not in st.session_state:
        st.session_state["invoice_processed_signatures"] = set()
    st.session_state.setdefault("audit_assignments", {})
    st.session_state.setdefault("audit_resolution_log", [])
    st.session_state.setdefault("audit_count_tasks", {})

    apply_ui_theme(st.session_state.get("ui_theme", "light"))

    name, authentication_status, username = authenticate_user()

    if authentication_status:

        # --- UI Setup et Définition des Onglets ---
        st.session_state["user_role"] = credentials["usernames"][username]["role"]
        st.session_state["username"] = username

        try:
            table_counts_df = load_table_counts()
        except Exception:
            table_counts_df = None

        render_workspace_overview(
            user_name=name,
            user_role=st.session_state.get("user_role"),
            table_counts=table_counts_df,
        )
        st.sidebar.caption(f'Bienvenue, **{name}** (Rôle: **{st.session_state["user_role"]}**)')
        theme_labels = list(THEME_LABELS.keys())
        current_theme_label = {
            value: label for label, value in THEME_LABELS.items()
        }.get(st.session_state.get("ui_theme", "light"), theme_labels[0])
        selected_label = st.sidebar.selectbox(
            "Apparence",
            options=theme_labels,
            index=theme_labels.index(current_theme_label),
        )
        chosen_theme = THEME_LABELS[selected_label]
        if chosen_theme != st.session_state.get("ui_theme"):
            st.session_state["ui_theme"] = chosen_theme
            apply_ui_theme(chosen_theme)
        else:
            apply_ui_theme(chosen_theme)
        authenticator.logout('Déconnexion', 'sidebar')

        # Définition des onglets fonctionnels de l'application
        st.markdown('<div class="workspace-tab-shell">', unsafe_allow_html=True)
        (
            showcase_tab,
            supply_tab,
            pos_tab,
            catalog_tab,
            mvt_tab,
            audit_tab,
            dash_tab,
            scanner_tab,
            extract_tab,
            import_tab,
            admin_tab,
        ) = st.tabs([
            "Vitrine",
            "Approvisionnement",
            "Vente (PoS)",
            "Catalogue",
            "Stock & Mvt",
            "Audit & écarts",
            "Dashboard",
            "Scanner",
            "Extraction Facture",
            "Importation",
            "Maintenance (Admin)",
        ])

        # Chargement des données (en cache)
        df_products = load_products_list()


        # ---------------- Vitrine ----------------
        with showcase_tab:
            st.header("Vitrine Produits — vue client")

            catalog_df = load_customer_catalog()

            if catalog_df.empty:
                st.info("Aucun produit actif n'est actuellement disponible.")
            else:
                total_products = int(catalog_df["id"].nunique())
                total_categories = int(catalog_df["categorie"].nunique())
                total_stock = float(catalog_df["stock_actuel"].sum())
                total_sales = float(catalog_df["ventes_30j"].sum())

                stock_value = float((catalog_df["stock_actuel"] * catalog_df["prix_vente"]).sum())
                avg_price = float(catalog_df["prix_vente"].mean()) if total_products else 0.0
                potential_sales = float((catalog_df["ventes_30j"] * catalog_df["prix_vente"]).sum())
                default_low_stock_threshold = 5
                low_stock_count = int((catalog_df["stock_actuel"] <= default_low_stock_threshold).sum())

                def _format_number(value: float, decimals: int = 0, suffix: str = "") -> str:
                    formatted = f"{value:,.{decimals}f}".replace(",", " ")
                    return f"{formatted}{suffix}".strip()

                render_workspace_hero(
                    eyebrow="Expérience boutique",
                    title="Animez votre vitrine digitale avec des insights temps réel.",
                    description=(
                        "Visualisez la vitalité de vos rayons, identifiez les alertes prioritaires et "
                        "préparez vos opérations commerciales en toute confiance."
                    ),
                    badges=["Nouveautés", f"{total_products} références suivies"],
                    metrics=[
                        {"label": "Valeur stock", "value": f"{_format_number(stock_value)} €"},
                        {"label": "Potentiel 30 j", "value": f"{_format_number(potential_sales)} €"},
                        {"label": "Alertes actives", "value": f"{low_stock_count}"},
                    ],
                    tone="sunset",
                )

                metrics_cols = st.columns(4)
                metrics_cols[0].metric("Produits actifs", f"{total_products}")
                metrics_cols[1].metric("Catégories", f"{total_categories}")
                metrics_cols[2].metric("Stock disponible", _format_number(total_stock))
                metrics_cols[3].metric("Ventes 30j", _format_number(total_sales))

                insight_tab, category_tab, alerts_tab = st.tabs([
                    "Vue synthèse",
                    "Catégories & tendances",
                    "Alertes & opportunités",
                ])

                with insight_tab:
                    insight_cols = st.columns(3)
                    insight_cols[0].metric(
                        "Valeur de stock estimée",
                        f"{_format_number(stock_value)} €",
                    )
                    insight_cols[1].metric(
                        "Prix moyen au catalogue",
                        f"{_format_number(avg_price, decimals=2)} €",
                    )
                    insight_cols[2].metric(
                        "Produits en alerte",
                        f"{low_stock_count}",
                        delta=f"{(low_stock_count / total_products * 100):.0f}% du catalogue" if total_products else None,
                    )

                    top_sales_df = (
                        catalog_df.sort_values(by="ventes_30j", ascending=False)
                        .head(10)
                        .assign(ventes_30j=lambda df_: df_["ventes_30j"].round(0))
                    )
                    if not top_sales_df.empty:
                        top_sales_chart = px.bar(
                            top_sales_df,
                            x="nom",
                            y="ventes_30j",
                            color="categorie",
                            title="Top 10 des ventes (30 derniers jours)",
                            labels={"nom": "Produit", "ventes_30j": "Ventes (u)", "categorie": "Catégorie"},
                        )
                        top_sales_chart.update_layout(margin=dict(l=20, r=20, t=60, b=20))
                        st.plotly_chart(top_sales_chart, use_container_width=True)
                    else:
                        st.caption("Aucune donnée de vente disponible pour le moment.")

                    trending_limit = st.slider(
                        "Nombre de produits mis en avant",
                        min_value=3,
                        max_value=12,
                        step=3,
                        value=6,
                        key="showcase_trending_limit",
                    )
                    columns_count = st.slider(
                        "Produits par rangée",
                        min_value=1,
                        max_value=4,
                        value=3,
                        key="showcase_trending_columns",
                    )

                    trending_df = load_trending_products(limit=trending_limit)
                    st.subheader("Produits populaires")
                    if trending_df.empty or trending_df["ventes_30j"].sum() <= 0:
                        st.caption("Les données de vente récentes ne sont pas encore disponibles.")
                    else:
                        _render_product_cards(trending_df, columns=columns_count)

                with category_tab:
                    category_summary = (
                        catalog_df.groupby("categorie")
                        .agg(
                            produits=("id", "count"),
                            stock_total=("stock_actuel", "sum"),
                            ventes_30j=("ventes_30j", "sum"),
                            panier_moyen=("prix_vente", "mean"),
                        )
                        .reset_index()
                        .sort_values(by=["ventes_30j", "stock_total"], ascending=False)
                    )

                    if not category_summary.empty:
                        category_fig = px.bar(
                            category_summary,
                            x="categorie",
                            y="ventes_30j",
                            color="stock_total",
                            color_continuous_scale="Sunset",
                            title="Dynamiques par catégorie",
                            labels={
                                "categorie": "Catégorie",
                                "ventes_30j": "Ventes (30 j)",
                                "stock_total": "Stock total",
                            },
                        )
                        category_fig.update_layout(coloraxis_showscale=False, margin=dict(l=20, r=20, t=60, b=20))
                        st.plotly_chart(category_fig, use_container_width=True)

                    st.dataframe(
                        category_summary,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "categorie": "Catégorie",
                            "produits": st.column_config.NumberColumn("Produits"),
                            "stock_total": st.column_config.NumberColumn("Stock total", format="%.0f"),
                            "ventes_30j": st.column_config.NumberColumn("Ventes 30j", format="%.0f"),
                            "panier_moyen": st.column_config.NumberColumn("Prix moyen", format="%.2f €"),
                        },
                    )

                with alerts_tab:
                    alert_cols = st.columns([1, 1, 1.2])
                    threshold = alert_cols[0].slider(
                        "Seuil d'alerte stock",
                        min_value=0,
                        max_value=20,
                        value=default_low_stock_threshold,
                        key="showcase_alert_threshold",
                    )
                    recent_focus = alert_cols[1].slider(
                        "Minimum ventes 30 j",
                        min_value=0,
                        max_value=20,
                        value=1,
                        key="showcase_alert_sales",
                    )
                    alert_cols[2].metric(
                        "Produits critiques",
                        f"{int((catalog_df['stock_actuel'] <= threshold).sum())}",
                    )

                    low_stock_df = catalog_df[catalog_df["stock_actuel"] <= threshold].copy()
                    low_stock_df = low_stock_df.sort_values(by=["stock_actuel", "ventes_30j"], ascending=[True, False])

                    if low_stock_df.empty:
                        st.success("Aucune alerte critique sur le seuil sélectionné. 🎉")
                    else:
                        st.subheader("Stocks à sécuriser")
                        st.dataframe(
                            low_stock_df[["nom", "categorie", "stock_actuel", "ventes_30j"]],
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "nom": "Produit",
                                "categorie": "Catégorie",
                                "stock_actuel": st.column_config.NumberColumn("Stock", format="%.0f"),
                                "ventes_30j": st.column_config.NumberColumn("Ventes 30j", format="%.0f"),
                            },
                        )

                    slow_movers = catalog_df[
                        (catalog_df["stock_actuel"] > threshold)
                        & (catalog_df["ventes_30j"] <= recent_focus)
                    ].copy()
                    slow_movers = slow_movers.sort_values(by="stock_actuel", ascending=False).head(10)
                    if not slow_movers.empty:
                        st.subheader("Produits à animer (rotation lente)")
                        st.dataframe(
                            slow_movers[["nom", "categorie", "stock_actuel", "ventes_30j", "prix_vente"]],
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "nom": "Produit",
                                "categorie": "Catégorie",
                                "stock_actuel": st.column_config.NumberColumn("Stock", format="%.0f"),
                                "ventes_30j": st.column_config.NumberColumn("Ventes 30j", format="%.0f"),
                                "prix_vente": st.column_config.NumberColumn("Prix", format="%.2f €"),
                            },
                        )

                st.subheader("Explorer le catalogue")

                filter_col1, filter_col2, filter_col3 = st.columns([2.4, 2.4, 1.6])
                categories = ["Toutes"] + sorted(catalog_df["categorie"].unique())
                selected_category = filter_col1.selectbox("Catégorie", categories)
                search_term = filter_col2.text_input("Recherche produit", placeholder="Nom, catégorie...")
                sort_options = {
                    "ventes": "Popularité (ventes 30j)",
                    "stock": "Stock disponible",
                    "prix": "Prix croissant",
                }
                sort_key = filter_col3.selectbox(
                    "Ordre d'affichage",
                    options=list(sort_options.keys()),
                    format_func=sort_options.get,
                    index=0,
                )

                extra_filters = st.columns([2, 1, 1])
                max_preview = extra_filters[0].slider(
                    "Nombre de résultats affichés",
                    min_value=6,
                    max_value=60,
                    step=6,
                    value=24,
                    key="catalog_preview_limit",
                )
                card_columns = extra_filters[1].slider(
                    "Cartes par ligne",
                    min_value=1,
                    max_value=4,
                    value=3,
                    key="catalog_preview_columns",
                )
                show_data_table = extra_filters[2].checkbox(
                    "Voir le tableau",
                    value=True,
                    key="catalog_show_table",
                )

                filtered_df = catalog_df.copy()

                if selected_category != "Toutes":
                    filtered_df = filtered_df[filtered_df["categorie"] == selected_category]

                if search_term:
                    filtered_df = filtered_df[
                        filtered_df["nom"].str.contains(search_term, case=False, na=False)
                        | filtered_df["categorie"].str.contains(search_term, case=False, na=False)
                    ]

                if sort_key == "ventes":
                    filtered_df = filtered_df.sort_values(by="ventes_30j", ascending=False)
                elif sort_key == "stock":
                    filtered_df = filtered_df.sort_values(by="stock_actuel", ascending=False)
                else:
                    filtered_df = filtered_df.sort_values(by="prix_vente", ascending=True)

                filtered_df = filtered_df.reset_index(drop=True)
                preview_df = filtered_df.head(max_preview)

                st.caption(
                    f"{len(filtered_df)} produit(s) correspondant(s). Aperçu des {len(preview_df)} premiers résultats."
                )
                _render_product_cards(
                    preview_df,
                    columns=card_columns if len(preview_df) >= card_columns else max(len(preview_df), 1),
                )

                if show_data_table and not filtered_df.empty:
                    st.dataframe(
                        filtered_df[["nom", "categorie", "prix_vente", "stock_actuel", "ventes_30j", "ean"]],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "nom": "Produit",
                            "categorie": "Catégorie",
                            "prix_vente": st.column_config.NumberColumn("Prix", format="%.2f €"),
                            "stock_actuel": st.column_config.NumberColumn("Stock", format="%.0f"),
                            "ventes_30j": st.column_config.NumberColumn("Ventes 30j", format="%.0f"),
                            "ean": st.column_config.TextColumn("EAN"),
                        },
                    )

                with st.expander("Consulter une fiche produit détaillée"):
                    options = {
                        f"{row.nom} — {row.categorie}": int(row.id)
                        for row in catalog_df.itertuples()
                    }

                    if not options:
                        st.info("Aucun produit n'est disponible pour l'instant.")
                    else:
                        selected_detail = st.selectbox(
                            "Produit",
                            options=list(options.keys()),
                            index=0,
                        )

                        detail_id = options[selected_detail]
                        detail_row = catalog_df[catalog_df["id"] == detail_id].iloc[0]
                        ean_value = str(detail_row.get("ean", "")).strip()
                        st.markdown(
                            f"**Nom :** {detail_row['nom']}  \n"
                            f"**Catégorie :** {detail_row['categorie']}  \n"
                            f"**Prix de vente :** {detail_row['prix_vente']:.2f} €  \n"
                            f"**Stock disponible :** {detail_row['stock_actuel']:.0f}  \n"
                            f"**Ventes (30 jours) :** {detail_row['ventes_30j']:.0f}  \n"
                            f"**EAN :** {ean_value or '—'}"
                        )
                        detail_image: str | None = None
                        raw_detail = detail_row.get("image_url")
                        if isinstance(raw_detail, str) and raw_detail.strip():
                            detail_image = raw_detail.strip()
                        elif raw_detail is not None and not pd.isna(raw_detail):
                            candidate = str(raw_detail).strip()
                            detail_image = candidate or None

                        if not detail_image and ean_value:
                            detail_image = _fetch_product_image_url(ean_value)

                        if detail_image:
                            st.image(detail_image, caption=f"EAN {ean_value}" if ean_value else None, width=240)
                        elif ean_value:
                            st.caption("Aucun visuel trouvé pour ce code-barres.")


        # ---------------- Approvisionnement dynamique ----------------

        with supply_tab:
            st.header("Plan d’approvisionnement dynamique")

            catalog_df = load_customer_catalog()

            if catalog_df.empty:
                st.info("Aucune donnée produit disponible pour établir un plan de réassort.")
            else:
                config_cols = st.columns(3)
                target_coverage = config_cols[0].slider(
                    "Objectif de couverture (jours)",
                    min_value=7,
                    max_value=60,
                    value=21,
                    step=1,
                    key="supply_target_coverage",
                )
                raw_alert_threshold = config_cols[1].slider(
                    "Seuil d’alerte (jours de stock restant)",
                    min_value=1,
                    max_value=30,
                    value=7,
                    step=1,
                    key="supply_alert_threshold",
                )
                min_daily_sales = config_cols[2].number_input(
                    "Ignorer les articles sous (ventes/jour)",
                    min_value=0.0,
                    max_value=50.0,
                    value=0.0,
                    step=0.1,
                    key="supply_min_daily_sales",
                    help=(
                        "Fixez un seuil pour concentrer les recommandations sur les produits à rotation suffisante."
                    ),
                )

                effective_alert = max(1, min(int(raw_alert_threshold), int(target_coverage)))
                if raw_alert_threshold > target_coverage:
                    st.caption(
                        f"ℹ️ Le seuil d’alerte est plafonné à {effective_alert} jour(s) pour rester cohérent avec l’objectif de couverture."
                    )
                min_sales_threshold = float(min_daily_sales)

                daily_sales = (catalog_df["ventes_30j"].fillna(0.0) / 30.0).clip(lower=0.0)
                stock_levels = catalog_df["stock_actuel"].fillna(0.0).clip(lower=0.0)

                coverage_days = np.where(
                    daily_sales > 0,
                    stock_levels / daily_sales,
                    np.where(stock_levels > 0, np.inf, 0.0),
                )

                planning_df = catalog_df.assign(
                    ventes_jour=daily_sales,
                    couverture_jours=coverage_days,
                )

                supplier_info = load_recent_suppliers()
                if not supplier_info.empty:
                    planning_df = planning_df.merge(
                        supplier_info.rename(columns={"produit_id": "id"}),
                        on="id",
                        how="left",
                    )
                if "fournisseur" not in planning_df.columns:
                    planning_df["fournisseur"] = "Non renseigné"
                else:
                    planning_df["fournisseur"] = planning_df["fournisseur"].fillna("Non renseigné")

                planning_df["objectif_stock"] = np.maximum(target_coverage * planning_df["ventes_jour"], 0.0)
                raw_reorder = planning_df["objectif_stock"] - planning_df["stock_actuel"]
                planning_df["quantite_a_commander"] = np.maximum(np.ceil(raw_reorder), 0).astype(int)
                planning_df["valeur_commande"] = planning_df["quantite_a_commander"] * planning_df["prix_vente"].fillna(0.0)
                planning_df["ecart_couverture"] = planning_df["couverture_jours"] - float(target_coverage)
                planning_df["marge_unitaire"] = planning_df["prix_vente"].fillna(0.0) - planning_df["prix_achat"].fillna(0.0)
                planning_df["marge_pct"] = np.where(
                    planning_df["prix_vente"].fillna(0.0) > 0,
                    (planning_df["marge_unitaire"] / planning_df["prix_vente"].replace(0, np.nan)) * 100,
                    np.nan,
                )
                planning_df["marge_commande"] = planning_df["marge_unitaire"] * planning_df["quantite_a_commander"]

                if min_sales_threshold > 0:
                    planning_df = planning_df[planning_df["ventes_jour"] >= min_sales_threshold]

                if min_sales_threshold <= 0:
                    rotation_mask = planning_df["ventes_jour"] > 0
                else:
                    rotation_mask = planning_df["ventes_jour"] >= min_sales_threshold

                priority_levels = np.select(
                    [
                        rotation_mask & (planning_df["couverture_jours"] <= effective_alert),
                        rotation_mask & (planning_df["quantite_a_commander"] > 0),
                        planning_df["quantite_a_commander"] > 0,
                    ],
                    ["Critique", "Tendue", "Surveillance"],
                    default="Confort",
                )
                planning_df["niveau_priorite"] = priority_levels
                priority_order = {"Critique": 0, "Tendue": 1, "Surveillance": 2, "Confort": 3}
                planning_df["ordre_priorite"] = planning_df["niveau_priorite"].map(priority_order)

                categories = sorted(planning_df["categorie"].dropna().unique().tolist())
                category_selection = st.multiselect(
                    "Catégories à analyser",
                    options=categories,
                    default=categories,
                    key="supply_category_filter",
                )
                filtered_df = (
                    planning_df
                    if not category_selection
                    else planning_df[planning_df["categorie"].isin(category_selection)]
                )

                search_term = st.text_input(
                    "Recherche produit ou EAN",
                    key="supply_search_term",
                    placeholder="Nom, catégorie ou code-barres…",
                ).strip()
                if search_term:
                    lowered = search_term.lower()
                    filtered_df = filtered_df[
                        filtered_df["nom"].str.contains(lowered, case=False, na=False)
                        | filtered_df["categorie"].str.contains(lowered, case=False, na=False)
                        | filtered_df["ean"].astype(str).str.contains(lowered, case=False, na=False)
                    ]

                if filtered_df.empty:
                    st.info("Aucun article ne correspond aux filtres appliqués.")
                else:
                    filtered_df = filtered_df.copy()
                    filtered_df["ventes_jour"] = filtered_df["ventes_jour"].round(2)
                    filtered_df["couverture_jours"] = filtered_df["couverture_jours"].replace(-np.inf, 0.0)
                    filtered_df["valeur_commande"] = filtered_df["valeur_commande"].round(2)
                    filtered_df["ecart_couverture"] = filtered_df["ecart_couverture"].round(1)

                    filtered_df["marge_pct"] = filtered_df["marge_pct"].round(1)
                    filtered_df["marge_commande"] = filtered_df["marge_commande"].round(2)
                    filtered_df["fournisseur"] = filtered_df["fournisseur"].fillna("Non renseigné")

                    filtered_df = filtered_df.sort_values(
                        by=["ordre_priorite", "couverture_jours", "ventes_jour"],
                        ascending=[True, True, False],
                    )

                    metrics_cols = st.columns(5)
                    metrics_cols[0].metric(
                        "Articles analysés",
                        f"{len(filtered_df):,}".replace(",", " "),
                    )
                    metrics_cols[1].metric(
                        "Réassorts recommandés",
                        f"{int((filtered_df['quantite_a_commander'] > 0).sum()):,}".replace(",", " "),
                    )
                    metrics_cols[2].metric(
                        "Unités à commander",
                        f"{int(filtered_df['quantite_a_commander'].sum()):,}".replace(",", " "),
                    )
                    metrics_cols[3].metric(
                        "Valeur estimée",
                        f"{filtered_df['valeur_commande'].sum():,.2f} €".replace(",", " "),
                    )
                    metrics_cols[4].metric(
                        "Marge potentielle",
                        f"{filtered_df['marge_commande'].sum():,.2f} €".replace(",", " "),
                    )

                    urgent_df = filtered_df[
                        (filtered_df["niveau_priorite"].isin(["Critique", "Tendue"]))
                        & (filtered_df["quantite_a_commander"] > 0)
                    ].head(6)
                    if not urgent_df.empty:
                        st.subheader("Alertes produits prioritaires")
                        _render_product_cards(
                            urgent_df,
                            columns=min(3, len(urgent_df)),
                            coverage_target=target_coverage,
                            alert_threshold=effective_alert,
                        )

                    display_columns = [
                        "nom",
                        "categorie",
                        "ventes_jour",
                        "stock_actuel",
                        "couverture_jours",
                        "ecart_couverture",
                        "niveau_priorite",
                        "quantite_a_commander",
                        "valeur_commande",
                        "marge_pct",
                        "marge_commande",
                        "fournisseur",
                        "ean",
                    ]

                    st.dataframe(
                        filtered_df[display_columns],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "nom": st.column_config.TextColumn("Produit"),
                            "categorie": st.column_config.TextColumn("Catégorie"),
                            "ventes_jour": st.column_config.NumberColumn(
                                "Ventes / jour", format="%.2f"
                            ),
                            "stock_actuel": st.column_config.NumberColumn("Stock", format="%.0f"),
                            "couverture_jours": st.column_config.NumberColumn(
                                "Couverture (j)", format="%.1f"
                            ),
                            "ecart_couverture": st.column_config.NumberColumn(
                                "Écart vs objectif", format="%.1f"
                            ),
                            "niveau_priorite": st.column_config.TextColumn("Priorité"),
                            "quantite_a_commander": st.column_config.NumberColumn(
                                "Qté à commander", format="%d"
                            ),
                            "valeur_commande": st.column_config.NumberColumn(
                                "Valeur (€)", format="%.2f €"
                            ),
                            "marge_pct": st.column_config.NumberColumn("Marge %", format="%.1f %%"),
                            "marge_commande": st.column_config.NumberColumn("Marge (€)", format="%.2f €"),
                            "fournisseur": st.column_config.TextColumn("Fournisseur"),
                            "ean": st.column_config.TextColumn("EAN"),
                        },
                    )

                    order_candidates = filtered_df[filtered_df["quantite_a_commander"] > 0]
                    if not order_candidates.empty:
                        st.subheader("Préparation des commandes fournisseurs")
                        supplier_summary = (
                            order_candidates.groupby("fournisseur", as_index=False)
                            .agg(
                                articles=("id", "count"),
                                quantite=("quantite_a_commander", "sum"),
                                valeur=("valeur_commande", "sum"),
                                marge=("marge_commande", "sum"),
                            )
                            .sort_values("valeur", ascending=False)
                        )

                        st.dataframe(
                            supplier_summary,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "fournisseur": "Fournisseur",
                                "articles": st.column_config.NumberColumn("Références", format="%d"),
                                "quantite": st.column_config.NumberColumn("Qté totale", format="%d"),
                                "valeur": st.column_config.NumberColumn("Valeur (€)", format="%.2f €"),
                                "marge": st.column_config.NumberColumn("Marge (€)", format="%.2f €"),
                            },
                        )

                        selected_supplier = st.selectbox(
                            "Fournisseur à détailler",
                            supplier_summary["fournisseur"].tolist(),
                            index=0,
                            key="supply_supplier_focus",
                        )

                        supplier_lines = order_candidates[
                            order_candidates["fournisseur"] == selected_supplier
                        ]
                        detail_columns = [
                            "nom",
                            "quantite_a_commander",
                            "valeur_commande",
                            "marge_commande",
                            "ventes_jour",
                            "couverture_jours",
                            "niveau_priorite",
                            "ean",
                        ]
                        st.dataframe(
                            supplier_lines[detail_columns],
                            hide_index=True,
                            use_container_width=True,
                        )

                        export_columns = detail_columns + ["fournisseur"]
                        supplier_csv = (
                            supplier_lines[export_columns]
                            .rename(
                                columns={
                                    "nom": "Produit",
                                    "quantite_a_commander": "Quantite",
                                    "valeur_commande": "Valeur",
                                    "marge_commande": "Marge",
                                    "ventes_jour": "Ventes_Jour",
                                    "couverture_jours": "Couverture",
                                    "niveau_priorite": "Priorite",
                                    "ean": "EAN",
                                    "fournisseur": "Fournisseur",
                                }
                            )
                            .to_csv(index=False)
                            .encode("utf-8")
                        )
                        st.download_button(
                            f"Exporter la proposition {selected_supplier}",
                            data=supplier_csv,
                            file_name=f"commande_{selected_supplier.replace(' ', '_').lower()}.csv",
                            mime="text/csv",
                            key="supplier_order_export",
                        )

                    with st.expander("Exporter la proposition"):
                        export_df = filtered_df[display_columns].rename(
                            columns={
                                "nom": "Produit",
                                "categorie": "Catégorie",
                                "ventes_jour": "Ventes_Jour",
                                "stock_actuel": "Stock",
                                "couverture_jours": "Couverture_Jours",
                                "ecart_couverture": "Ecart_Couverture",
                                "niveau_priorite": "Priorite",
                                "quantite_a_commander": "Quantite_Commander",
                                "valeur_commande": "Valeur_Commande",
                                "marge_pct": "Marge_Pourcent",
                                "marge_commande": "Marge_Commande",
                                "fournisseur": "Fournisseur",
                                "ean": "EAN",
                            }
                        )
                        csv_buffer = export_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Télécharger le plan (CSV)",
                            data=csv_buffer,
                            file_name="plan_approvisionnement.csv",
                            mime="text/csv",
                        )

        # ---------------- Vente (PoS) ----------------

        with pos_tab:
            for legacy_key in ("product_to_add_id", "product_to_add_qty", "add_to_cart_triggered"):
                st.session_state.pop(legacy_key, None)

            cart_items = list(_ensure_cart_state())
            cart_df = _normalize_cart_dataframe(cart_items)
            cart_df = cart_df.assign(
                prix_total=lambda df_: df_["prix_vente"] * df_["qty"],
            )
            cart_df = cart_df.assign(
                total_tva=lambda df_: df_["prix_total"] * (df_["tva"] / 100),
            )

            total_ttc = float(cart_df["prix_total"].sum()) if not cart_df.empty else 0.0
            total_tva = float(cart_df["total_tva"].sum()) if not cart_df.empty else 0.0
            total_ht = total_ttc - total_tva
            cart_quantity = int(cart_df["qty"].sum()) if not cart_df.empty else 0
            references_count = int(cart_df.shape[0])

            render_workspace_hero(
                eyebrow="Terminal de vente",
                title="Encaissez en douceur chaque passage en caisse",
                description="Ajoutez, scannez et finalisez vos ventes tout en maintenant l'inventaire à jour automatiquement.",
                badges=["Panier connecté", "Synchro stock"],
                metrics=[
                    {"label": "Articles panier", "value": str(cart_quantity), "hint": f"{references_count} référence(s)" if references_count else "Aucun produit"},
                    {"label": "Total TTC", "value": f"{_format_human_number(total_ttc, 2)} €", "hint": f"HT {_format_human_number(total_ht, 2)} €"},
                    {"label": "TVA cumulée", "value": f"{_format_human_number(total_tva, 2)} €", "hint": "Incluse dans le total"},
                ],
                tone="citrus",
            )

            diag_df = load_stock_diagnostics()
            with workspace_panel(
                "Diagnostic stock", 
                "Surveille les écarts entre stocks comptés et mouvements enregistrés en temps réel.",
                icon="🚨",
                accent="amber",
            ):
                if diag_df is None or diag_df.empty:
                    st.success("Aucun écart détecté, les stocks sont alignés ✅")
                else:
                    diag_display = diag_df.copy()
                    diag_display["ecart_abs"] = diag_display["ecart"].abs()
                    top_rows = diag_display.sort_values("ecart_abs", ascending=False).head(5)
                    st.dataframe(
                        top_rows.rename(
                            columns={
                                "nom": "Produit",
                                "stock_actuel": "Stock système",
                                "stock_calcule": "Stock mouvements",
                                "ecart": "Écart",
                            }
                        )[["Produit", "Stock système", "Stock mouvements", "Écart"]],
                        hide_index=True,
                        use_container_width=True,
                    )

                    worst_row = top_rows.iloc[0]
                    st.warning(
                        f"Écart maximal sur {worst_row['nom']} : {worst_row['ecart']:+.2f} unité(s)",
                        icon="⚠️",
                    )
                    st.caption("Liste limitée aux 5 écarts les plus importants. Rafraîchir la page pour recharger les données.")

            cart_col, input_col = st.columns([1.35, 1])

            success_message = st.session_state.pop("pos_success_message", None)

            with cart_col:
                with workspace_panel(
                    "Panier en direct",
                    "Visualisez les lignes en cours avant validation.",
                    icon="🛍️",
                    accent="citrus",
                ):
                    if success_message:
                        st.success(success_message)
                        receipt_data = st.session_state.get("pos_receipt")
                        if receipt_data:
                            st.download_button(
                                "Télécharger le ticket (PDF)",
                                data=receipt_data.get("content", b""),
                                file_name=receipt_data.get("filename", "ticket.pdf"),
                                mime="application/pdf",
                                key="download_pos_receipt",
                            )

                    if cart_df.empty:
                        st.info("Le panier est vide. Ajoutez un produit pour démarrer la vente.")
                    else:
                        st.dataframe(
                            cart_df[["nom", "qty", "prix_vente", "prix_total"]],
                            column_config={
                                "nom": "Produit",
                                "qty": "Quantité",
                                "prix_vente": st.column_config.NumberColumn("P.U. (€)", format="%.2f €"),
                                "prix_total": st.column_config.NumberColumn("Total ligne (€)", format="%.2f €"),
                            },
                            hide_index=True,
                            use_container_width=True,
                        )

                    metric_cols = st.columns(3)
                    metric_cols[0].metric("Total HT", f"{total_ht:.2f} €")
                    metric_cols[1].metric("Total TVA", f"{total_tva:.2f} €")
                    metric_cols[2].metric("Total TTC", f"{total_ttc:.2f} €", delta_color="off")

                    action_cols = st.columns(2)
                    with action_cols[0]:
                        if st.button(
                            "Vider le panier",
                            help="Annule la transaction en cours.",
                            key="clear_cart_btn",
                        ):
                            _clear_cart()
                            _reset_pos_inputs()
                            st.rerun()

                    with action_cols[1]:
                        processing_sale = bool(st.session_state.get("pos_processing", False))
                        processing_status_slot = st.empty()
                        if processing_sale and not st.session_state.get("_pos_processing_notice"):
                            processing_status_slot.info("Traitement d'une vente en cours…")
                        st.session_state["_pos_processing_notice"] = processing_sale
                        finalize_clicked = st.button(
                            "Finaliser la vente",
                            key="btn_finalize_sale",
                            type="primary",
                            disabled=processing_sale,
                        )

                        if cart_items and finalize_clicked:
                            if processing_sale:
                                st.info("Une vente est déjà en cours de traitement…")
                            else:
                                st.session_state["pos_processing"] = True
                                processing_status_slot.info("Traitement de la vente en cours…")
                                try:
                                    with st.spinner("Traitement de la vente en cours..."):
                                        sale_result = process_sale_transaction(
                                            cart_items,
                                            st.session_state.get("username", "inconnu"),
                                        )

                                    sale_ok: bool
                                    sale_msg: str | None
                                    receipt_payload: dict[str, bytes] | None

                                    if isinstance(sale_result, tuple):
                                        if len(sale_result) == 3:
                                            sale_ok, sale_msg, receipt_payload = sale_result
                                        elif len(sale_result) == 2:
                                            sale_ok, sale_msg = sale_result
                                            receipt_payload = None
                                        else:
                                            padded = list(sale_result) + [None, None]
                                            sale_ok = bool(padded[0])
                                            sale_msg = padded[1]
                                            receipt_payload = padded[2]
                                    else:
                                        sale_ok = bool(sale_result)
                                        sale_msg = None
                                        receipt_payload = None

                                    if sale_ok:
                                        st.session_state["pos_success_message"] = (
                                            "Vente finalisée et stock mis à jour ✅"
                                        )
                                        _clear_cart()
                                        st.session_state["pos_receipt"] = receipt_payload
                                        invalidate_data_caches(
                                            "products_list",
                                            "catalog",
                                            "trending",
                                            "product_options",
                                            "movement_timeseries",
                                            "recent_movements",
                                            "table_counts",
                                            "table_preview",
                                            "stock_diagnostics",
                                        )
                                        st.session_state["_pos_processing_notice"] = False
                                        st.session_state["pos_processing"] = False
                                        st.rerun()
                                    else:
                                        error_msg = (
                                            sale_msg
                                            or "Échec de la vente. Vérifiez le stock disponible et réessayez."
                                        )
                                        st.error(error_msg)
                                        st.session_state["pos_receipt"] = None
                                        st.session_state["_pos_processing_notice"] = False
                                finally:
                                    st.session_state["_pos_processing_notice"] = False
                                    st.session_state["pos_processing"] = False
                                    processing_status_slot.empty()

            with input_col:
                with workspace_panel(
                    "Ajout rapide",
                    "Scannez ou recherchez un produit pour l'ajouter au panier.",
                    icon="✨",
                    accent="citrus",
                ):
                    try:
                        product_options = cached_product_options()
                        product_names = ["-- Sélectionner un produit --"] + list(product_options.keys())

                        if st.session_state.get("last_barcode"):
                            st.session_state["last_barcode"] = None

                    except Exception as e:
                        st.error(f"Erreur lors du chargement des produits: {e}")
                        product_names = ["-- Erreur de chargement --"]
                        product_options = {}

                    feedback_slot = st.empty()

                    with st.form("pos_input_form", clear_on_submit=False):
                        selected_product_name = st.selectbox(
                            "Sélectionner un produit (nom)",
                            options=product_names,
                            key="pos_product_selectbox",
                        )
                        qty_to_add = st.number_input(
                            "Quantité",
                            min_value=1,
                            step=1,
                            key="pos_qty_input",
                        )
                        add_button = st.form_submit_button("Ajouter au panier")

                    if add_button:
                        if selected_product_name == "-- Sélectionner un produit --":
                            feedback_slot.warning(
                                "Veuillez sélectionner un produit pour l'ajouter au panier."
                            )
                        else:
                            selected_product_id = product_options.get(selected_product_name)

                            if not selected_product_id:
                                feedback_slot.error(
                                    "Erreur: ID produit non trouvé après sélection."
                                )
                            else:
                                success, message = _add_product_to_cart(
                                    int(selected_product_id),
                                    int(qty_to_add),
                                    df_products,
                                )

                                if success:
                                    _reset_pos_inputs()
                                    st.toast(f"✅ {message}", icon="🛒")
                                    st.rerun()
                                else:
                                    feedback_slot.warning(message)

        # ---------------- Catalogue ----------------

        with catalog_tab:
            total_products = int(df_products.shape[0])
            low_stock_count = int((df_products["quantite_stock"] < 5).sum()) if not df_products.empty else 0
            average_price = float(df_products["prix_vente"].mean()) if not df_products.empty else 0.0
            barcode_ratio = 0
            if not df_products.empty:
                coverage_series = df_products.get("codes_barres", pd.Series(dtype=str)).fillna("")
                barcode_ratio = int((coverage_series.str.strip() != "").mean() * 100)

            render_workspace_hero(
                eyebrow="Catalogue produits",
                title="Pilotez votre base articles avec précision",
                description="Éditez les fiches, gérez les codes-barres et synchronisez votre catalogue avec le terrain.",
                badges=["Administration", "Qualité des données"],
                metrics=[
                    {"label": "Références actives", "value": str(total_products), "hint": f"{low_stock_count} alerte(s) < 5"},
                    {"label": "Prix moyen", "value": f"{_format_human_number(average_price, 2)} €"},
                    {"label": "Codes-barres", "value": f"{barcode_ratio}%", "hint": "Couverture"},
                ],
                tone="lagoon",
            )

            non_editable_columns = ['id', 'quantite_stock', 'statut_stock']
            if st.session_state.get("user_role") == "admin":
                disabled_cols = non_editable_columns
            else:
                disabled_cols = ['nom', 'prix_vente', 'tva', 'quantite_stock', 'statut_stock', 'codes_barres']

            with workspace_panel(
                "Gestion du catalogue",
                "Consultez et ajustez les informations clés de vos références.",
                icon="📚",
                accent="lagoon",
            ):
                st.caption("Le stock ne peut être modifié que via les mouvements — utilisez cette grille pour corriger les fiches.")

                if df_products.empty:
                    st.info("Aucun produit n'est actuellement enregistré.")
                else:
                    editable_df = st.data_editor(
                        df_products,
                        key="catalog_editor",
                        hide_index=True,
                        use_container_width=True,
                        num_rows="dynamic" if st.session_state.get("user_role") == "admin" else "fixed",
                        disabled=disabled_cols,
                        column_config={
                            "id": "ID",
                            "nom": "Nom du Produit",
                            "prix_vente": st.column_config.NumberColumn("Prix Vente (€)", format="%.2f"),
                            "tva": st.column_config.NumberColumn("TVA (%)", format="%.2f"),
                            "quantite_stock": st.column_config.NumberColumn("Stock Actuel", format="%.2f"),
                            "codes_barres": st.column_config.TextColumn("Codes-barres (Séparés par ', ')", help="Séparation par virgule"),
                            "statut_stock": st.column_config.TextColumn("Statut Stock"),
                        },
                    )

                    if st.session_state.get("user_role") == "admin":
                        action_cols = st.columns([2, 1.3])

                        with action_cols[0]:
                            if st.button(
                                "Enregistrer les modifications du catalogue",
                                key="save_catalog_changes",
                                type="primary",
                            ):
                                try:
                                    editor_state = st.session_state.get("catalog_editor", {})
                                    changes = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}

                                    if changes:
                                        field_updates = 0
                                        barcode_totals = {"added": 0, "removed": 0, "skipped": 0, "conflicts": 0}
                                        row_errors: list[str] = []

                                        for index, row_changes in changes.items():
                                            try:
                                                base_row = df_products.iloc[index]
                                            except (IndexError, KeyError):
                                                row_errors.append(
                                                    f"Ligne {index + 1}: produit introuvable dans le tableau."
                                                )
                                                continue

                                            product_id = int(base_row["id"])
                                            change_payload = dict(row_changes)
                                            barcode_field = change_payload.pop("codes_barres", None)

                                            try:
                                                result = update_catalog_entry(
                                                    product_id,
                                                    change_payload,
                                                    barcode_field,
                                                )
                                            except ProductNotFoundError as exc:
                                                row_errors.append(str(exc))
                                                continue
                                            except ValueError as exc:
                                                row_errors.append(f"Produit ID {product_id}: {exc}")
                                                continue

                                            field_updates += int(result.get("fields_updated", 0))
                                            barcode_result = result.get("barcodes", {})
                                            for key, value in barcode_result.items():
                                                if key in barcode_totals:
                                                    barcode_totals[key] += int(value or 0)

                                        for error_msg in row_errors:
                                            st.error(error_msg)

                                        applied_changes = (
                                            field_updates > 0
                                            or barcode_totals["added"] > 0
                                            or barcode_totals["removed"] > 0
                                        )

                                        summary_parts: list[str] = []
                                        if field_updates:
                                            summary_parts.append(f"{field_updates} champ(s) mis à jour")

                                        barcode_parts: list[str] = []
                                        if barcode_totals["added"]:
                                            barcode_parts.append(f"+{barcode_totals['added']} code(s)")
                                        if barcode_totals["removed"]:
                                            barcode_parts.append(f"-{barcode_totals['removed']} code(s)")
                                        if barcode_totals["skipped"]:
                                            barcode_parts.append(f"{barcode_totals['skipped']} doublon(s)")
                                        if barcode_totals["conflicts"]:
                                            barcode_parts.append(f"{barcode_totals['conflicts']} conflit(s)")

                                        if barcode_parts:
                                            summary_parts.append("Codes-barres: " + ", ".join(barcode_parts))

                                        if not summary_parts:
                                            summary_parts.append("Aucun changement appliqué.")

                                        summary_message = " · ".join(summary_parts)

                                        if barcode_totals["conflicts"]:
                                            st.warning(
                                                "Certains codes-barres sont déjà utilisés par d'autres produits et n'ont pas été modifiés."
                                            )

                                        if applied_changes:
                                            st.toast(summary_message, icon='💾')
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
                                            st.rerun()
                                        else:
                                            if not row_errors:
                                                st.info("Aucune modification n'a été détectée dans le tableau.")
                                    else:
                                        st.info("Aucune modification n'a été détectée dans le tableau.")

                                except Exception as e:
                                    st.error(f"Erreur lors de l'enregistrement: {e}")

                        with action_cols[1]:
                            barcode_to_delete = st.text_input(
                                "Code-barres à retirer / supprimer",
                                key="catalog_delete_barcode",
                                help=(
                                    "Saisissez un code existant pour le détacher du produit. "
                                    "Si c'était le dernier code-barres, le produit sera supprimé."
                                ),
                            )

                            if st.button(
                                "Supprimer via le code-barres",
                                key="confirm_delete_barcode",
                            ):
                                try:
                                    outcome = delete_product_by_barcode(barcode_to_delete)
                                except InvalidBarcodeError:
                                    st.warning("Veuillez saisir un code-barres valide (minimum 8 caractères).")
                                except ProductNotFoundError:
                                    st.error("Aucun produit ne correspond à ce code-barres.")
                                except Exception as exc:
                                    st.error(f"Erreur lors de la suppression: {exc}")
                                else:
                                    action = outcome.get("action")
                                    product_name = outcome.get("product_name") or "Produit"
                                    removed_code = outcome.get("removed_code")
                                    if action == "barcode_removed":
                                        remaining = outcome.get("remaining_barcodes", 0)
                                        st.toast(
                                            f"🎯 Code {removed_code} dissocié de {product_name} ({remaining} restant).",
                                            icon='🎯',
                                        )
                                    else:
                                        st.toast(
                                            f"🗑️ Produit '{product_name}' supprimé (code {removed_code}).",
                                            icon='🗑️',
                                        )
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
                                    st.rerun()

                            st.divider()
                            st.caption("Produits sans code-barres — suppression directe")

                            products_without_codes = df_products[
                                df_products["codes_barres"].fillna("").str.strip() == ""
                            ]

                            if products_without_codes.empty:
                                st.info("Tous les produits possèdent au moins un code-barres.")
                            else:
                                product_options = {
                                    f"{row.nom} (ID {row.id})": int(row.id)
                                    for row in products_without_codes.itertuples()
                                }
                                selected_product_label = st.selectbox(
                                    "Produit sans code-barres",
                                    list(product_options.keys()),
                                    index=None,
                                    key="catalog_delete_select",
                                )

                                if selected_product_label and st.button(
                                    "Supprimer ce produit",
                                    key="confirm_delete_product",
                                ):
                                    product_id = product_options[selected_product_label]
                                    try:
                                        engine = get_engine()
                                        with engine.begin() as conn:
                                            barcode_count = conn.execute(
                                                text(
                                                    "SELECT COUNT(*) FROM produits_barcodes WHERE produit_id = :pid"
                                                ),
                                                {"pid": product_id},
                                            ).scalar() or 0

                                            if barcode_count > 0:
                                                st.warning(
                                                    "Ce produit possède maintenant des codes-barres. Utilisez la suppression par code."
                                                )
                                            else:
                                                conn.execute(
                                                    text("DELETE FROM produits WHERE id = :pid"),
                                                    {"pid": product_id},
                                                )
                                                st.toast(
                                                    f"🗑️ Produit '{selected_product_label}' supprimé.",
                                                    icon='🗑️',
                                                )
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
                                                st.rerun()
                                    except Exception as exc:
                                        st.error(f"Erreur lors de la suppression: {exc}")

            quality_catalog = load_customer_catalog()
            duplicates_df = load_duplicate_barcodes()
            missing_price_df = df_products[df_products["prix_vente"].fillna(0) <= 0]
            missing_purchase_df = df_products[df_products.get("prix_achat", 0).fillna(0) <= 0]
            missing_barcode_df = df_products[df_products["codes_barres"].fillna("").str.strip() == ""]
            margin_alert_df = quality_catalog[
                (quality_catalog["prix_vente"].fillna(0) > 0)
                & (quality_catalog["prix_vente"] < quality_catalog["prix_achat"].fillna(0))
            ]

            with workspace_panel(
                "Qualité catalogue & codes-barres",
                "Identifiez les données manquantes, les doublons et les incohérences tarifaires.",
                icon="🧪",
                accent="lagoon",
            ):
                quality_cols = st.columns(4)
                quality_cols[0].metric("Prix vente manquants", str(len(missing_price_df)))
                quality_cols[1].metric("Prix achat manquants", str(len(missing_purchase_df)))
                quality_cols[2].metric("Sans code-barres", str(len(missing_barcode_df)))
                quality_cols[3].metric("Marge négative", str(len(margin_alert_df)))

                st.caption("Les sections ci-dessous permettent désormais de consulter, corriger ou supprimer les éléments problématiques.")

                tabs = st.tabs(
                    [
                        "Prix vente manquants",
                        "Prix achat manquants",
                        "Sans code-barres",
                        "Marge négative",
                        "Doublons",
                    ]
                )

                # --- Prix de vente manquants ---
                with tabs[0]:
                    st.subheader("Prix de vente à compléter", divider="rainbow")
                    view_df = missing_price_df[[
                        "id",
                        "nom",
                        "categorie",
                        "prix_achat",
                        "prix_vente",
                        "stock_actuel",
                    ]].reset_index(drop=True) if not missing_price_df.empty else pd.DataFrame()

                    if view_df.empty:
                        st.success("Tous les produits possèdent un prix de vente.")
                    elif st.session_state.get("user_role") == "admin":
                        st.caption("Modifiez les prix directement puis appliquez les changements.")
                        editor_df = view_df.copy()
                        st.data_editor(
                            editor_df,
                            key="quality_missing_price_editor",
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "id": st.column_config.NumberColumn("ID", disabled=True),
                                "nom": st.column_config.TextColumn("Produit", disabled=True),
                                "categorie": st.column_config.TextColumn("Catégorie", disabled=True),
                                "prix_achat": st.column_config.NumberColumn("Prix achat (€)", format="%.2f", disabled=True),
                                "prix_vente": st.column_config.NumberColumn("Prix vente (€)", format="%.2f"),
                                "stock_actuel": st.column_config.NumberColumn("Stock", format="%.2f", disabled=True),
                            },
                        )

                        if st.button(
                            "Mettre à jour les prix de vente manquants",
                            key="apply_missing_sale_price",
                            type="primary",
                        ):
                            editor_state = st.session_state.get("quality_missing_price_editor", {})
                            changes = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
                            if not changes:
                                st.info("Aucune modification détectée dans le tableau.")
                            else:
                                applied = 0
                                for index, row_changes in changes.items():
                                    try:
                                        base_row = editor_df.iloc[int(index)]
                                    except (IndexError, ValueError):
                                        continue
                                    payload = {k: v for k, v in row_changes.items() if k == "prix_vente"}
                                    if not payload:
                                        continue
                                    try:
                                        update_catalog_entry(int(base_row["id"]), payload, None)
                                    except Exception as exc:
                                        st.error(f"Erreur lors de la mise à jour de {base_row['nom']}: {exc}")
                                    else:
                                        applied += len(payload)
                                if applied:
                                    st.success(f"{applied} champ(s) mis à jour.")
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
                                    st.rerun()
                                else:
                                    st.info("Aucune correction n'a été appliquée.")
                    else:
                        st.dataframe(view_df, use_container_width=True, hide_index=True)

                # --- Prix d'achat manquants ---
                with tabs[1]:
                    st.subheader("Prix d'achat à compléter", divider="rainbow")
                    purchase_df = missing_purchase_df[[
                        "id",
                        "nom",
                        "categorie",
                        "prix_achat",
                        "prix_vente",
                        "stock_actuel",
                    ]].reset_index(drop=True) if not missing_purchase_df.empty else pd.DataFrame()

                    if purchase_df.empty:
                        st.success("Tous les produits possèdent un prix d'achat.")
                    elif st.session_state.get("user_role") == "admin":
                        st.caption("Renseignez les prix d'achat puis appliquez les changements.")
                        st.data_editor(
                            purchase_df,
                            key="quality_missing_purchase_editor",
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "id": st.column_config.NumberColumn("ID", disabled=True),
                                "nom": st.column_config.TextColumn("Produit", disabled=True),
                                "categorie": st.column_config.TextColumn("Catégorie", disabled=True),
                                "prix_achat": st.column_config.NumberColumn("Prix achat (€)", format="%.2f"),
                                "prix_vente": st.column_config.NumberColumn("Prix vente (€)", format="%.2f", disabled=True),
                                "stock_actuel": st.column_config.NumberColumn("Stock", format="%.2f", disabled=True),
                            },
                        )

                        if st.button(
                            "Mettre à jour les prix d'achat manquants",
                            key="apply_missing_purchase_price",
                            type="primary",
                        ):
                            editor_state = st.session_state.get("quality_missing_purchase_editor", {})
                            changes = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
                            if not changes:
                                st.info("Aucune modification détectée dans le tableau.")
                            else:
                                applied = 0
                                for index, row_changes in changes.items():
                                    try:
                                        base_row = purchase_df.iloc[int(index)]
                                    except (IndexError, ValueError):
                                        continue
                                    payload = {k: v for k, v in row_changes.items() if k == "prix_achat"}
                                    if not payload:
                                        continue
                                    try:
                                        update_catalog_entry(int(base_row["id"]), payload, None)
                                    except Exception as exc:
                                        st.error(f"Erreur lors de la mise à jour de {base_row['nom']}: {exc}")
                                    else:
                                        applied += len(payload)
                                if applied:
                                    st.success(f"{applied} champ(s) mis à jour.")
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
                                    st.rerun()
                                else:
                                    st.info("Aucune correction n'a été appliquée.")
                    else:
                        st.dataframe(purchase_df, use_container_width=True, hide_index=True)

                # --- Produits sans code-barres ---
                with tabs[2]:
                    st.subheader("Produits sans codes-barres", divider="rainbow")
                    barcode_df = missing_barcode_df[[
                        "id",
                        "nom",
                        "categorie",
                        "prix_vente",
                        "codes_barres",
                        "stock_actuel",
                    ]].reset_index(drop=True) if not missing_barcode_df.empty else pd.DataFrame()

                    if barcode_df.empty:
                        st.success("Tous les produits possèdent un code-barres.")
                    else:
                        if st.session_state.get("user_role") == "admin":
                            st.caption("Ajoutez des codes-barres ou supprimez les références inutiles.")
                            st.data_editor(
                                barcode_df,
                                key="quality_missing_barcode_editor",
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "id": st.column_config.NumberColumn("ID", disabled=True),
                                    "nom": st.column_config.TextColumn("Produit", disabled=True),
                                    "categorie": st.column_config.TextColumn("Catégorie", disabled=True),
                                    "prix_vente": st.column_config.NumberColumn("Prix vente (€)", format="%.2f", disabled=True),
                                    "codes_barres": st.column_config.TextColumn(
                                        "Codes-barres",
                                        help="Séparez plusieurs codes par une virgule.",
                                    ),
                                    "stock_actuel": st.column_config.NumberColumn("Stock", format="%.2f", disabled=True),
                                },
                            )

                            if st.button(
                                "Enregistrer les codes-barres saisis",
                                key="apply_missing_barcodes",
                                type="primary",
                            ):
                                editor_state = st.session_state.get("quality_missing_barcode_editor", {})
                                changes = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
                                if not changes:
                                    st.info("Aucune modification détectée dans le tableau.")
                                else:
                                    applied_updates = 0
                                    barcode_summary = {"added": 0, "removed": 0, "skipped": 0, "conflicts": 0}
                                    for index, row_changes in changes.items():
                                        try:
                                            base_row = barcode_df.iloc[int(index)]
                                        except (IndexError, ValueError):
                                            continue
                                        change_payload = dict(row_changes)
                                        barcode_field = change_payload.pop("codes_barres", None)
                                        try:
                                            result = update_catalog_entry(
                                                int(base_row["id"]),
                                                {k: v for k, v in change_payload.items() if k in {"prix_vente"}},
                                                barcode_field,
                                            )
                                        except Exception as exc:
                                            st.error(f"Erreur lors de la mise à jour de {base_row['nom']}: {exc}")
                                            continue
                                        applied_updates += int(result.get("fields_updated", 0))
                                        for key, value in (result.get("barcodes") or {}).items():
                                            if key in barcode_summary:
                                                barcode_summary[key] += int(value or 0)

                                    if applied_updates or any(barcode_summary.values()):
                                        summary_parts: list[str] = []
                                        if any(barcode_summary.values()):
                                            barcode_parts = []
                                            if barcode_summary["added"]:
                                                barcode_parts.append(f"+{barcode_summary['added']} code(s)")
                                            if barcode_summary["removed"]:
                                                barcode_parts.append(f"-{barcode_summary['removed']} code(s)")
                                            if barcode_summary["skipped"]:
                                                barcode_parts.append(f"{barcode_summary['skipped']} doublon(s)")
                                            if barcode_summary["conflicts"]:
                                                barcode_parts.append(f"{barcode_summary['conflicts']} conflit(s)")
                                            if barcode_parts:
                                                summary_parts.append("Codes-barres: " + ", ".join(barcode_parts))
                                        if applied_updates:
                                            summary_parts.append(f"{applied_updates} champ(s) mis à jour")
                                        st.success(" · ".join(summary_parts) or "Mises à jour effectuées.")
                                        if barcode_summary["conflicts"]:
                                            st.warning("Certains codes-barres sont déjà utilisés par d'autres produits.")
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
                                        st.rerun()
                                    else:
                                        st.info("Aucune correction n'a été appliquée.")

                            st.divider()
                            delete_options = {
                                f"{row.nom} (ID {row.id})": int(row.id)
                                for row in barcode_df.itertuples()
                            }
                            product_to_delete = st.selectbox(
                                "Supprimer un produit sans code-barres",
                                list(delete_options.keys()),
                                key="quality_missing_barcode_delete",
                            ) if delete_options else None

                            if product_to_delete and st.button(
                                "Supprimer le produit sélectionné",
                                key="confirm_delete_missing_barcode",
                                type="secondary",
                            ):
                                product_id = delete_options.get(product_to_delete)
                                try:
                                    with get_engine().begin() as conn:
                                        conn.execute(
                                            text("DELETE FROM produits WHERE id = :pid"),
                                            {"pid": int(product_id)},
                                        )
                                except Exception as exc:
                                    st.error(f"Erreur lors de la suppression du produit: {exc}")
                                else:
                                    st.toast(f"🗑️ Produit ID {product_id} supprimé.", icon='🗑️')
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
                                    st.rerun()
                        else:
                            st.dataframe(barcode_df, use_container_width=True, hide_index=True)

                # --- Marge négative ---
                with tabs[3]:
                    st.subheader("Produits vendus à marge négative", divider="rainbow")
                    alert_display = margin_alert_df[[
                        "id",
                        "nom",
                        "categorie",
                        "prix_achat",
                        "prix_vente",
                        "stock_actuel",
                        "ean",
                    ]].reset_index(drop=True) if not margin_alert_df.empty else pd.DataFrame()

                    if alert_display.empty:
                        st.success("Aucun produit n'est vendu sous son prix d'achat.")
                    else:
                        st.dataframe(alert_display, hide_index=True, use_container_width=True)

                    if st.session_state.get("user_role") == "admin" and not alert_display.empty:
                        st.subheader("Campagne de correction rapide")
                        correction_df = alert_display.copy()

                        correction_editor = st.data_editor(
                            correction_df,
                            key="quality_campaign_editor",
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "id": st.column_config.NumberColumn("ID", disabled=True),
                                "nom": st.column_config.TextColumn("Produit", disabled=True),
                                "categorie": st.column_config.TextColumn("Catégorie", disabled=True),
                                "prix_achat": st.column_config.NumberColumn("Prix achat (€)", format="%.2f", disabled=True),
                                "prix_vente": st.column_config.NumberColumn("Prix vente (€)", format="%.2f"),
                                "stock_actuel": st.column_config.NumberColumn("Stock", format="%.2f", disabled=True),
                                "ean": st.column_config.TextColumn("EAN", disabled=True),
                            },
                        )

                        if st.button("Appliquer les corrections ciblées", key="apply_quality_campaign", type="primary"):
                            editor_state = st.session_state.get("quality_campaign_editor", {})
                            changes = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
                            if not changes:
                                st.info("Aucune modification détectée sur les produits ciblés.")
                            else:
                                applied = 0
                                for index, row_changes in changes.items():
                                    try:
                                        base_row = correction_df.iloc[int(index)]
                                    except (IndexError, ValueError):
                                        continue
                                    payload = {k: v for k, v in row_changes.items() if k in {"prix_vente"}}
                                    if not payload:
                                        continue
                                    try:
                                        update_catalog_entry(int(base_row["id"]), payload, None)
                                        applied += len(payload)
                                    except Exception as exc:
                                        st.error(f"Erreur lors de la mise à jour de {base_row['nom']}: {exc}")
                                if applied:
                                    st.success(f"{applied} champ(s) mis à jour.")
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
                                    st.rerun()
                                else:
                                    st.info("Aucune correction n'a été appliquée.")

                # --- Doublons de codes-barres ---
                with tabs[4]:
                    st.subheader("Doublons de codes-barres détectés", divider="rainbow")
                    if duplicates_df.empty:
                        st.success("Aucun doublon de code-barres détecté.")
                    else:
                        st.dataframe(duplicates_df, hide_index=True, use_container_width=True)
                        st.download_button(
                            "Exporter les doublons",
                            data=duplicates_df.to_csv(index=False).encode("utf-8"),
                            file_name="doublons_codes_barres.csv",
                            mime="text/csv",
                        )

            if st.session_state.get("user_role") == "admin":
                with workspace_panel(
                    "Ajout rapide de produit",
                    "Créez une nouvelle référence et attribuez-lui éventuellement des codes-barres.",
                    icon="✨",
                    accent="lagoon",
                ):
                    with st.form("add_product_form", clear_on_submit=True):
                        colA, colB = st.columns(2)
                        with colA:
                            new_nom = st.text_input("Nom du Produit", max_chars=100)
                            new_prix = st.number_input("Prix de Vente (€)", min_value=0.01, format="%.2f", value=1.0)
                        with colB:
                            new_tva = st.number_input("TVA (%)", min_value=0.0, max_value=100.0, value=20.0, format="%.2f")
                            new_codes = st.text_input("Codes-barres (séparés par ;) [Optionnel]", max_chars=255)

                        if st.form_submit_button("Ajouter le Produit au Catalogue"):
                            if new_nom and new_prix > 0:
                                try:
                                    sql_prod = text("INSERT INTO produits (nom, prix_vente, tva) VALUES (:nom, :prix, :tva) RETURNING id")
                                    product_id = exec_sql_return_id(sql_prod.bindparams(nom=new_nom, prix=new_prix, tva=new_tva))

                                    if new_codes:
                                        codes_list = parse_barcode_input(new_codes)
                                        barcode_outcome = {"added": 0, "conflicts": 0, "skipped": 0}
                                        engine = get_engine()
                                        with engine.begin() as conn:
                                            for code in codes_list:
                                                status = products_loader.insert_or_update_barcode(conn, product_id, code)
                                                if status == "added":
                                                    barcode_outcome["added"] += 1
                                                elif status == "conflict":
                                                    barcode_outcome["conflicts"] += 1
                                                else:
                                                    barcode_outcome["skipped"] += 1

                                    st.success(f"Produit '{new_nom}' ajouté avec succès!")
                                    invalidate_data_caches(
                                        "products_list",
                                        "catalog",
                                        "trending",
                                        "product_options",
                                        "table_preview",
                                        "recent_movements",
                                        "table_counts",
                                    )

                                    if new_codes:
                                        st.caption(
                                            "Codes-barres — "
                                            f"ajouts: {barcode_outcome['added']}, "
                                            f"conflits: {barcode_outcome['conflicts']}, "
                                            f"ignorés: {barcode_outcome['skipped']}"
                                        )
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur lors de l'ajout: {e}")
                            else:
                                st.warning("Veuillez entrer un nom et un prix de produit valide (> 0).")

        # ---------------- Stock & Mvt ----------------

        with mvt_tab:
            if df_products.empty:
                st.info("Veuillez ajouter des produits au catalogue d'abord.")
                st.stop()

        # ---------------- Catalogue ----------------

            hero_placeholder = st.container()

            try:
                product_options = cached_product_options()
            except Exception as exc:
                st.error(
                    "Impossible de charger la liste des produits pour le filtre des mouvements. "
                    f"Détail: {exc}"
                )
                product_options = {}

            filter_products = ["Catalogue complet"] + list(product_options.keys())

            with workspace_panel(
                "Paramètres d'analyse",
                "Sélectionnez le périmètre de suivi pour explorer les mouvements.",
                icon="🎯",
                accent="marine",
            ):
                col_filter_product, col_filter_window, col_filter_limit = st.columns([3, 1, 1])
                selected_product_name = col_filter_product.selectbox(
                    "Produit suivi",
                    filter_products,
                    key="movement_filter_product",
                )
                selected_product_id = (
                    product_options.get(selected_product_name)
                    if selected_product_name in product_options
                    else None
                )

                window_days = col_filter_window.selectbox(
                    "Période",
                    options=[7, 30, 90, 180],
                    format_func=lambda d: f"{d} jours",
                    index=1,
                    key="movement_filter_window",
                )

                recent_limit = col_filter_limit.selectbox(
                    "Lignes",
                    options=[25, 50, 100, 200],
                    index=2,
                    key="movement_filter_limit",
                )

            movement_ts = load_movement_timeseries(window_days=window_days, product_id=selected_product_id)
            recent_movements = load_recent_movements(limit=recent_limit, product_id=selected_product_id)

            total_entries = float(movement_ts.loc[movement_ts['type'] == 'ENTREE', 'quantite'].sum()) if not movement_ts.empty else 0.0
            total_outputs = float(movement_ts.loc[movement_ts['type'] == 'SORTIE', 'quantite'].sum()) if not movement_ts.empty else 0.0
            net_balance = total_entries - total_outputs

            selection_label = "Catalogue complet" if not selected_product_id else selected_product_name

            with hero_placeholder:
                render_workspace_hero(
                    eyebrow="Mouvements de stock",
                    title=f"Analyse des flux — {selection_label}",
                    description="Visualisez l'équilibre des entrées/sorties et anticipez les ruptures.",
                    badges=["Pilotage quotidien", f"Fenêtre {window_days} j"],
                    metrics=[
                        {"label": "Entrées", "value": f"+{_format_human_number(total_entries, 2)}", "hint": "Quantités"},
                        {"label": "Sorties", "value": f"-{_format_human_number(total_outputs, 2)}", "hint": "Déstockage"},
                        {"label": "Variation nette", "value": f"{_format_human_number(net_balance, 2)}", "hint": "Entrées - sorties"},
                    ],
                    tone="marine",
                )

            with workspace_panel(
                "Visualisations des mouvements",
                "Comparez les volumes quotidiens et la tendance cumulative.",
                icon="📈",
                accent="marine",
            ):
                if movement_ts.empty:
                    st.info("Aucun mouvement enregistré pour la période sélectionnée.")
                else:
                    chart_col_1, chart_col_2 = st.columns(2)
                    with chart_col_1:
                        chart_df = movement_ts.copy()
                        chart_df.sort_values(["jour", "type"], inplace=True)
                        st.plotly_chart(
                            px.bar(
                                chart_df,
                                x="jour",
                                y="quantite",
                                color="type",
                                barmode="group",
                                title="Mouvements par type",
                                labels={"jour": "Jour", "quantite": "Quantité", "type": "Type"},
                            ),
                            use_container_width=True,
                        )

                    with chart_col_2:
                        net_daily = movement_ts.copy()
                        net_daily["delta"] = net_daily.apply(
                            lambda row: -row["quantite"] if row["type"] == "SORTIE" else row["quantite"],
                            axis=1,
                        )
                        net_daily = (
                            net_daily.groupby("jour")["delta"]
                            .sum()
                            .reset_index(name="variation")
                            .sort_values("jour")
                        )
                        net_daily["cumul"] = net_daily["variation"].cumsum()
                        line_fig = px.line(
                            net_daily,
                            x="jour",
                            y="cumul",
                            markers=True,
                            title="Variation cumulée",
                            labels={"jour": "Jour", "cumul": "Δ cumulée"},
                        )
                        line_fig.add_hline(y=0, line_dash="dot", line_color="#999999")
                        st.plotly_chart(line_fig, use_container_width=True)

            with workspace_panel(
                "Mouvements récents",
                "Consultez le détail des derniers mouvements enregistrés.",
                icon="🗂️",
                accent="marine",
            ):
                if recent_movements.empty:
                    st.info("Aucun mouvement à afficher pour le filtre en cours.")
                else:
                    recent_display = recent_movements.copy()
                    recent_display["date_mvt"] = pd.to_datetime(recent_display["date_mvt"]).dt.strftime("%Y-%m-%d %H:%M")
                    st.dataframe(recent_display, use_container_width=True, hide_index=True)

            if st.session_state.get("user_role") == "admin":
                with workspace_panel(
                    "Ajustement / Inventaire",
                    "Corrigez une quantité de stock en enregistrant un mouvement dédié.",
                    icon="🛠️",
                    accent="marine",
                ):
                    with st.form("stock_adjustment_form", clear_on_submit=True):
                        col_prod, col_qty = st.columns(2)
                        selected_product_name = col_prod.selectbox("Produit à ajuster", product_names, key='adj_product',)
                        selected_product_id = product_options.get(selected_product_name)
                        product_details = (
                            get_product_details(selected_product_id) if selected_product_id else None
                        )

                        current_stock = 0.0
                        if product_details:
                            current_stock = float(product_details.get('quantite_stock') or 0)
                            st.info(f"Produit trouvé: **{product_details['nom']}**")
                            st.warning(f"Stock actuel: **{current_stock:.2f}**")
                        elif selected_product_name:
                            st.error("Produit non trouvé.")
                        else:
                            st.info("Sélectionnez un produit pour afficher le stock actuel.")

                        target_stock = col_qty.number_input(
                            "Nouvelle Quantité Totale (Inventaire)",
                            min_value=0.00,
                            value=current_stock,
                            step=0.01,
                            format="%.2f",
                            key='adj_target_qty'
                        )

                        if st.form_submit_button("Enregistrer l'Ajustement", type="primary"):
                            if not selected_product_id:
                                st.error("Erreur: Le produit n'a pas été trouvé ou sélectionné. Veuillez réessayer.")
                            else:
                                quantite_mvt = target_stock - current_stock

                                if abs(quantite_mvt) < 0.001:
                                    st.warning(
                                        f"Le stock de **{selected_product_name}** n'a pas changé. ({current_stock:.2f} -> {target_stock:.2f})"
                                    )
                                else:
                                    mouvement_type = 'ENTREE' if quantite_mvt > 0 else 'SORTIE'
                                    mouvement_params = {
                                        'pid': selected_product_id,
                                        'type': mouvement_type,
                                        'quantite': abs(quantite_mvt),
                                        'source': f"Inventaire par {st.session_state.get('username', 'inconnu')}"
                                    }

                                    sql_mvt = text(
                                        "INSERT INTO mouvements_stock (produit_id, type, quantite, source) VALUES (:pid, :type, :quantite, :source)"
                                    )

                                    try:
                                        exec_sql(sql_mvt, mouvement_params)
                                        st.success(
                                            f"Ajustement réussi. Le stock de {selected_product_name} est maintenant à {target_stock:.2f} unités."
                                        )
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
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erreur lors de l'enregistrement de l'ajustement: {e}")

        # ---------------- Audit & écarts ----------------

        with audit_tab:
            st.header("Audit & résolution d'écarts")

            diag_df = load_stock_diagnostics()
            assignments: dict[int, dict[str, Any]] = st.session_state.setdefault("audit_assignments", {})
            resolution_log: list[dict[str, Any]] = st.session_state.setdefault("audit_resolution_log", [])
            count_tasks: dict[int, dict[str, Any]] = st.session_state.setdefault("audit_count_tasks", {})

            if diag_df is None or diag_df.empty:
                st.success("Aucun écart détecté, les stocks théoriques et mouvements sont alignés ✅")
            else:
                catalog_snapshot = load_customer_catalog()[["id", "categorie", "prix_achat", "prix_vente"]]
                audit_df = diag_df.merge(catalog_snapshot, on="id", how="left")
                audit_df["ecart_abs"] = audit_df["ecart"].abs()
                severity_levels = np.select(
                    [
                        audit_df["ecart_abs"] >= 10,
                        audit_df["ecart_abs"] >= 3,
                    ],
                    ["Critique", "Modéré"],
                    default="Mineur",
                )
                audit_df["niveau_ecart"] = severity_levels
                audit_df["responsable"] = audit_df["id"].map(
                    lambda pid: assignments.get(int(pid), {}).get("responsable")
                )
                audit_df["tache_statut"] = audit_df["id"].map(
                    lambda pid: count_tasks.get(int(pid), {}).get("status", "À investiguer")
                )

                filter_cols = st.columns([1.6, 1.3, 1.5])
                categories = sorted(audit_df["categorie"].dropna().unique().tolist())
                selected_categories = filter_cols[0].multiselect(
                    "Catégories concernées",
                    options=categories,
                    default=categories,
                    key="audit_category_filter",
                )
                levels = ["Critique", "Modéré", "Mineur"]
                selected_levels = filter_cols[1].multiselect(
                    "Niveau d'écart",
                    options=levels,
                    default=levels,
                    key="audit_severity_filter",
                )
                max_ecart = float(np.ceil(audit_df["ecart_abs"].max())) if not audit_df.empty else 1.0
                ecart_range = filter_cols[2].slider(
                    "Amplitude d'écart (abs)",
                    min_value=0.0,
                    max_value=max(1.0, max_ecart),
                    value=(0.0, max(1.0, max_ecart)),
                    key="audit_ecart_range",
                )

                filtered_audit = audit_df.copy()
                if selected_categories:
                    filtered_audit = filtered_audit[filtered_audit["categorie"].isin(selected_categories)]
                if selected_levels:
                    filtered_audit = filtered_audit[filtered_audit["niveau_ecart"].isin(selected_levels)]
                filtered_audit = filtered_audit[
                    (filtered_audit["ecart_abs"] >= ecart_range[0])
                    & (filtered_audit["ecart_abs"] <= ecart_range[1])
                ]

                metrics = st.columns(4)
                metrics[0].metric("Anomalies ouvertes", f"{len(filtered_audit):,}".replace(",", " "))
                metrics[1].metric(
                    "Écart cumulé",
                    f"{filtered_audit['ecart'].sum():+.2f}",
                )
                metrics[2].metric(
                    "Assignées",
                    f"{sum(1 for pid in filtered_audit['id'] if pid in assignments):,}".replace(",", " "),
                )
                metrics[3].metric(
                    "Tâches à compter",
                    f"{sum(1 for data in count_tasks.values() if data.get('status') != 'Clôturé'):,}".replace(",", " "),
                )

                if filtered_audit.empty:
                    st.info("Aucune anomalie ne correspond aux filtres sélectionnés.")
                else:
                    display_cols = [
                        "nom",
                        "categorie",
                        "stock_actuel",
                        "stock_calcule",
                        "ecart",
                        "ecart_abs",
                        "niveau_ecart",
                        "responsable",
                        "tache_statut",
                    ]
                    st.dataframe(
                        filtered_audit[display_cols],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "nom": "Produit",
                            "categorie": "Catégorie",
                            "stock_actuel": st.column_config.NumberColumn("Stock système", format="%.2f"),
                            "stock_calcule": st.column_config.NumberColumn("Stock calculé", format="%.2f"),
                            "ecart": st.column_config.NumberColumn("Écart", format="%+.2f"),
                            "ecart_abs": st.column_config.NumberColumn("Écart abs.", format="%.2f"),
                            "niveau_ecart": st.column_config.TextColumn("Niveau"),
                            "responsable": st.column_config.TextColumn("Responsable"),
                            "tache_statut": st.column_config.TextColumn("Statut tâche"),
                        },
                    )

                actions_col, resolve_col = st.columns(2)

                with actions_col:
                    st.subheader("Assigner un audit")
                    if audit_df.empty:
                        st.caption("Aucune ligne disponible")
                    else:
                        assign_options = {
                            f"{row.nom} ({row.ecart:+.2f})": int(row.id)
                            for row in audit_df.itertuples()
                        }
                        with st.form("audit_assignment_form"):
                            selected_label = st.selectbox(
                                "Produit concerné",
                                list(assign_options.keys()),
                                key="audit_assign_product",
                            )
                            responsable = st.text_input("Responsable", key="audit_assign_owner")
                            due_date = st.date_input("Date de comptage prévue", key="audit_assign_date")
                            note = st.text_area("Notes", key="audit_assign_note")
                            create_task = st.checkbox(
                                "Générer une tâche de comptage correctif",
                                value=True,
                                key="audit_assign_create_task",
                            )
                            submitted = st.form_submit_button("Enregistrer l'assignation", use_container_width=True)

                        if submitted:
                            product_id = assign_options.get(selected_label)
                            if not responsable:
                                st.warning("Veuillez renseigner un responsable pour suivre l'écart.")
                            elif product_id is None:
                                st.error("Produit sélectionné invalide.")
                            else:
                                assignments[int(product_id)] = {
                                    "responsable": responsable,
                                    "note": note,
                                    "assigned_at": datetime.now(),
                                }
                                if create_task:
                                    count_tasks[int(product_id)] = {
                                        "responsable": responsable,
                                        "note": note,
                                        "created_at": datetime.now(),
                                        "status": "À compter",
                                        "due_date": datetime.combine(due_date, datetime.min.time()),
                                    }
                                st.session_state["audit_assignments"] = assignments
                                st.session_state["audit_count_tasks"] = count_tasks
                                st.success("Assignation enregistrée.")

                with resolve_col:
                    st.subheader("Clôturer / journaliser")
                    if not assignments:
                        st.caption("Aucun audit assigné pour l'instant.")
                    else:
                        task_options = {
                            f"{audit_df.loc[audit_df['id'] == pid, 'nom'].iloc[0]}": int(pid)
                            for pid in assignments
                            if pid in audit_df["id"].values
                        }
                        with st.form("audit_resolution_form"):
                            if not task_options:
                                st.caption("Aucune ligne correspondante aux données chargées.")
                                selected_task = None
                            else:
                                selected_task_label = st.selectbox(
                                    "Produit", list(task_options.keys()), key="audit_resolve_product"
                                )
                                selected_task = task_options.get(selected_task_label)
                            resolution_status = st.selectbox(
                                "Statut", ["En cours", "Résolu"], key="audit_resolve_status"
                            )
                            resolution_note = st.text_area("Commentaire / actions réalisées", key="audit_resolve_note")
                            submit_resolution = st.form_submit_button(
                                "Mettre à jour", use_container_width=True
                            )

                        if submit_resolution and selected_task is not None:
                            entry = {
                                "produit_id": selected_task,
                                "produit": audit_df.loc[audit_df["id"] == selected_task, "nom"].iloc[0],
                                "responsable": assignments.get(selected_task, {}).get("responsable"),
                                "statut": resolution_status,
                                "note": resolution_note,
                                "timestamp": datetime.now(),
                            }
                            resolution_log.append(entry)
                            if resolution_status == "Résolu":
                                count_tasks.setdefault(selected_task, {})["status"] = "Clôturé"
                            else:
                                count_tasks.setdefault(selected_task, {})["status"] = "En cours"
                            st.session_state["audit_resolution_log"] = resolution_log
                            st.session_state["audit_count_tasks"] = count_tasks
                            st.success("Journal mis à jour.")

                with st.expander("Tâches de comptage en cours", expanded=False):
                    if not count_tasks:
                        st.caption("Aucune tâche planifiée.")
                    else:
                        tasks_df = pd.DataFrame(
                            [
                                {
                                    "produit": audit_df.loc[audit_df["id"] == pid, "nom"].iloc[0]
                                    if pid in audit_df["id"].values
                                    else f"Produit {pid}",
                                    "responsable": data.get("responsable"),
                                    "statut": data.get("status"),
                                    "due_date": data.get("due_date"),
                                    "note": data.get("note"),
                                }
                                for pid, data in count_tasks.items()
                            ]
                        )
                        st.dataframe(tasks_df, hide_index=True, use_container_width=True)

                with st.expander("Historique des résolutions", expanded=False):
                    if not resolution_log:
                        st.caption("Le journal est vide pour le moment.")
                    else:
                        log_df = pd.DataFrame(resolution_log)
                        log_df["timestamp"] = pd.to_datetime(log_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
                        st.dataframe(log_df, hide_index=True, use_container_width=True)

                with st.expander("Exporter l'audit", expanded=False):
                    if filtered_audit.empty:
                        st.caption("Aucune donnée à exporter.")
                    else:
                        export_df = filtered_audit.assign(
                            Responsable=filtered_audit["responsable"],
                            Statut=filtered_audit["tache_statut"],
                        )[
                            [
                                "id",
                                "nom",
                                "categorie",
                                "stock_actuel",
                                "stock_calcule",
                                "ecart",
                                "ecart_abs",
                                "niveau_ecart",
                                "Responsable",
                                "Statut",
                            ]
                        ]
                        st.download_button(
                            "Télécharger le rapport CSV",
                            data=export_df.to_csv(index=False).encode("utf-8"),
                            file_name="audit_ecarts.csv",
                            mime="text/csv",
                        )

        # ---------------- Dashboard ----------------

        with dash_tab:
            try:
                df_kpis = load_stock_kpis()
                df_top_stock_value = load_top_stock_value()
                df_top_sales = load_top_sales()
                df_status_count = df_products.groupby("statut_stock").size().reset_index(name="Nombre")
            except Exception as e:
                st.error(f"Erreur lors du chargement des données du tableau de bord: {e}")
                df_kpis = pd.DataFrame({
                    "total_produits": [0],
                    "valeur_stock_ht": [0.0],
                    "quantite_stock_total": [0.0],
                    "alerte_stock_bas": [0],
                    "stock_epuise": [0],
                })
                df_top_stock_value = pd.DataFrame({"nom": [], "valeur_stock": []})
                df_top_sales = pd.DataFrame({"nom": [], "quantite_vendue": []})
                df_status_count = pd.DataFrame({
                    "statut_stock": ["Stock OK", "Alerte Basse", "Épuisé"],
                    "Nombre": [0, 0, 0],
                })

            kpis = df_kpis.iloc[0]
            stock_value = float(kpis.get('valeur_stock_ht') or 0.0)
            stock_units = float(kpis.get('quantite_stock_total') or 0.0)
            alert_count = int(kpis.get('alerte_stock_bas') or 0)
            exhausted_count = int(kpis.get('stock_epuise') or 0)

            render_workspace_hero(
                eyebrow="Tableau de bord",
                title="Pilotez l'inventaire en un clin d'œil",
                description="Suivez la valeur du stock, détectez les alertes et identifiez vos best-sellers en continu.",
                badges=["Vue globale", "Décision rapide"],
                metrics=[
                    {"label": "Références", "value": str(int(kpis.get('total_produits', 0)))},
                    {"label": "Valeur HT", "value": f"{_format_human_number(stock_value, 2)} €", "hint": f"{_format_human_number(stock_units, 0)} unités"},
                    {"label": "Alertes", "value": str(alert_count), "hint": f"{exhausted_count} rupture(s)"},
                ],
                tone="violet",
            )

            with workspace_panel(
                "Indicateurs clés",
                "Vue synthétique des métriques d'inventaire.",
                icon="📊",
                accent="violet",
            ):
                metric_cols = st.columns(4)
                metric_cols[0].metric("Valeur stock HT", f"{_format_human_number(stock_value, 2)} €")
                metric_cols[1].metric("Quantité totale", _format_human_number(stock_units, 0))
                metric_cols[2].metric("Alertes stock", f"{alert_count}", delta=alert_count, delta_color="inverse")
                metric_cols[3].metric("Ruptures", f"{exhausted_count}", delta=exhausted_count, delta_color="inverse")

            with workspace_panel(
                "Focus stock et ventes",
                "Identifiez les produits à forte valeur et les meilleures ventes.",
                icon="📦",
                accent="violet",
            ):
                col_chart_1, col_chart_2, col_chart_3 = st.columns(3)

                with col_chart_1:
                    st.caption("Top 5 Stock (valeur HT)")
                    if not df_top_stock_value.empty:
                        st.bar_chart(df_top_stock_value, x='nom', y='valeur_stock', height=280)
                    else:
                        st.info("Aucune donnée de stock à afficher.")

                with col_chart_2:
                    st.caption("Top 5 ventes (quantité)")
                    if not df_top_sales.empty:
                        st.bar_chart(df_top_sales, x='nom', y='quantite_vendue', height=280, color="#f97316")
                    else:
                        st.info("Aucune donnée de vente à afficher.")

                with col_chart_3:
                    st.caption("Répartition des statuts")
                    if not df_status_count.empty:
                        st.plotly_chart(
                            px.pie(df_status_count, values='Nombre', names='statut_stock', title=None),
                            use_container_width=True,
                            config={"displayModeBar": False},
                        )
                    else:
                        st.info("Aucune donnée de statut à afficher.")

        # ---------------- Scanner ----------------

        with scanner_tab:
            last_barcode = st.session_state.get("last_barcode")

            render_workspace_hero(
                eyebrow="Scanner",
                title="Capturez vos codes-barres en direct",
                description="Utilisez la webcam pour alimenter rapidement le terminal de vente ou enrichir vos fiches produits.",
                badges=["Webcam", "Détection instantanée"],
                metrics=[
                    {"label": "Dernier code", "value": last_barcode or "—"},
                    {"label": "Connexion", "value": "Actif" if last_barcode else "En attente"},
                ],
                tone="emerald",
            )

            with workspace_panel(
                "Informations de lecture",
                "Historique du dernier code détecté et résultat de la recherche produit.",
                icon="🔍",
                accent="emerald",
            ):
                if last_barcode:
                    st.success(f"Code-barres détecté : **{last_barcode}**")
                    try:
                        product_name = lookup_product_name(last_barcode)
                    except Exception:
                        product_name = None

                    if product_name:
                        st.caption(f"Produit correspondant : **{product_name}**")
                    else:
                        st.caption("Aucun produit associé à ce code-barres.")
                else:
                    st.info("Lancez la capture vidéo pour commencer la détection.")

            with workspace_panel(
                "Capture vidéo",
                "Activez la caméra pour analyser les codes-barres.",
                icon="📷",
                accent="emerald",
            ):
                webrtc_streamer(
                    key="barcode_scanner_webrtc",
                    mode=WebRtcMode.SENDRECV,
                    rtc_configuration=RTCConfiguration(
                        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
                    ),
                    video_processor_factory=BarcodeDetector,
                    async_processing=True,
                )

        # ---------------- Extraction Facture ----------------

        with extract_tab:
            extracted_df = st.session_state.get("invoice_products_df")
            summary = st.session_state.get("invoice_import_summary")
            detected_count = int(len(extracted_df)) if isinstance(extracted_df, pd.DataFrame) else 0

            render_workspace_hero(
                eyebrow="Extraction facture",
                title="Transformez vos factures en produits structurés",
                description="Téléversez une facture Metro, corrigez les lignes détectées et importez-les directement dans le catalogue.",
                badges=["PDF / DOCX / TXT", "Analyse automatique"],
                metrics=[
                    {"label": "Lignes détectées", "value": str(detected_count)},
                    {"label": "Résumé import", "value": "Disponible" if summary else "En attente"},
                ],
                tone="amber",
            )

            with workspace_panel(
                "Téléversement",
                "Ajoutez une facture et choisissez la capture à analyser.",
                icon="📂",
                accent="amber",
            ):
                uploaded_invoice_files = st.file_uploader(
                    "Déposer une facture Metro",
                    type=["pdf", "docx", "txt"],
                    key="extract_invoice_file_uploader",
                    help="Les formats PDF, DOCX et TXT sont pris en charge.",
                    accept_multiple_files=True,
                )

                _process_uploaded_invoices(uploaded_invoice_files, "Extraction")
                _render_invoice_selector("Facture chargée", "extract_invoice_selector")

            with workspace_panel(
                "Texte de la facture",
                "Collez ou ajustez le contenu avant l'analyse.",
                icon="📝",
                accent="amber",
            ):
                extract_invoice_text = st.text_area(
                    "Texte à analyser",
                    value=st.session_state.get("invoice_text_input", ""),
                    key="extract_invoice_text_input",
                    height=260,
                    placeholder="Collez ici la section produits de la facture si nécessaire...",
                )
                if extract_invoice_text != st.session_state.get("invoice_text_input"):
                    st.session_state["invoice_text_input"] = extract_invoice_text
                    st.session_state["import_invoice_text_input"] = extract_invoice_text

                col_extract_btn, col_reset_btn = st.columns(2)
                with col_extract_btn:
                    if st.button("Analyser le texte", key="extract_invoice_extract_button", type="primary"):
                        text_to_parse = st.session_state.get("invoice_text_input", "")
                        if not text_to_parse.strip():
                            st.warning("Aucun texte à analyser. Téléversez une facture ou collez du texte.")
                        else:
                            df_extracted = invoice_extractor.extract_products_from_metro_invoice(text_to_parse)
                            st.session_state["invoice_products_df"] = df_extracted
                            st.session_state["invoice_import_summary"] = None
                            if df_extracted.empty:
                                st.warning("Aucune ligne produit détectée. Ajustez le texte et réessayez.")
                            else:
                                st.success(f"{len(df_extracted)} ligne(s) produit détectée(s). Vérifiez et corrigez-les ci-dessous.")
                with col_reset_btn:
                    if st.button("Réinitialiser l'extraction", key="extract_invoice_reset_button"):
                        _reset_invoice_session_state()
                        st.session_state["invoice_reset_notice_origin"] = "extract"
                        st.rerun()

                if st.session_state.get("invoice_reset_notice_origin") == "extract":
                    st.info("Extraction réinitialisée.")
                    st.session_state.pop("invoice_reset_notice_origin", None)

                if st.session_state.get("invoice_raw_text"):
                    st.download_button(
                        "Télécharger le texte brut",
                        data=st.session_state["invoice_raw_text"].encode("utf-8"),
                        file_name=st.session_state.get("invoice_uploaded_name", "facture.txt"),
                        mime="text/plain",
                        key="extract_invoice_raw_text_download",
                    )

            if isinstance(extracted_df, pd.DataFrame) and not extracted_df.empty:
                with workspace_panel(
                    "Produits détectés",
                    "Corrigez les informations extraites avant import.",
                    icon="🧾",
                    accent="amber",
                ):
                    st.caption(
                        "Vérifiez les informations extraites. Vous pouvez ajuster les noms, les prix, la TVA ou les codes-barres avant l'importation."
                    )

                    working_df = extracted_df.copy()
                    if "quantite_recue" not in working_df.columns and "qte_init" in working_df.columns:
                        working_df["quantite_recue"] = working_df["qte_init"]
                    if "codes" in working_df.columns:
                        working_df["_code_lower"] = (
                            working_df["codes"].fillna("").astype(str).str.lower().str.strip()
                        )
                        matches_df = match_invoice_products(working_df)
                        if not matches_df.empty:
                            matches_df = matches_df.rename(
                                columns={
                                    "code": "_code_lower",
                                    "produit_id": "catalogue_id",
                                    "produit_nom": "catalogue_nom",
                                    "categorie": "catalogue_categorie",
                                }
                            )
                            working_df = working_df.merge(matches_df, on="_code_lower", how="left")
                            if "produit_id" not in working_df.columns:
                                working_df["produit_id"] = working_df["catalogue_id"]
                            else:
                                working_df["produit_id"] = working_df["produit_id"].fillna(
                                    working_df["catalogue_id"]
                                )
                        working_df.drop(columns=["_code_lower"], inplace=True, errors="ignore")

                    editable_df = st.data_editor(
                        working_df,
                        key="extract_invoice_products_editor",
                        hide_index=True,
                        num_rows="dynamic",
                        use_container_width=True,
                        column_config={
                            "nom": st.column_config.TextColumn("Nom du produit"),
                            "prix_vente": st.column_config.NumberColumn("Prix de vente (€)", format="%.2f"),
                            "tva": st.column_config.NumberColumn("TVA (%)", format="%.2f"),
                            "qte_init": st.column_config.NumberColumn("Quantité", step=1, format="%.0f"),
                            "quantite_recue": st.column_config.NumberColumn(
                                "Quantité reçue", step=1, format="%.0f"
                            ),
                            "codes": st.column_config.TextColumn("Codes-barres"),
                            "produit_id": st.column_config.NumberColumn(
                                "Produit ID", help="Identifiant catalogue cible si déjà existant"
                            ),
                            "catalogue_id": st.column_config.NumberColumn(
                                "ID catalogue suggéré", disabled=True
                            ),
                            "catalogue_nom": st.column_config.TextColumn(
                                "Produit catalogue", disabled=True
                            ),
                            "catalogue_categorie": st.column_config.TextColumn(
                                "Catégorie catalogue", disabled=True
                            ),
                            "prix_achat_catalogue": st.column_config.NumberColumn(
                                "Prix achat catalogue (€)", format="%.2f", disabled=True
                            ),
                            "prix_vente_catalogue": st.column_config.NumberColumn(
                                "Prix vente catalogue (€)", format="%.2f", disabled=True
                            ),
                        },
                    )
                    editable_df = pd.DataFrame(editable_df)
                    for col in ("nom", "codes"):
                        if col in editable_df.columns:
                            editable_df[col] = editable_df[col].fillna("")
                    st.session_state["invoice_products_df"] = editable_df

                    col_download, col_import = st.columns(2)
                    with col_download:
                        csv_data = editable_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Télécharger le CSV extrait",
                            data=csv_data,
                            file_name=st.session_state.get("invoice_uploaded_name", "facture.txt").replace(".txt", ".csv"),
                            mime="text/csv",
                            key="extract_invoice_csv_download",
                        )
                    with col_import:
                        if st.button("Importer ces produits", key="extract_invoice_import_button", type="primary"):
                            with st.spinner("Import des produits en cours..."):
                                summary_result = products_loader.load_products_from_df(editable_df)
                            st.session_state["invoice_import_summary"] = summary_result
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
                            st.success("Importation terminée. Consultez le résumé ci-dessous.")
                            summary = summary_result

                with workspace_panel(
                    "Rapprochement facture → commande",
                    "Préparez les bons de réception et les mouvements de stock à partir de la facture importée.",
                    icon="🔄",
                    accent="teal",
                ):
                    reconciliation_df = st.session_state.get("invoice_products_df")
                    if not isinstance(reconciliation_df, pd.DataFrame) or reconciliation_df.empty:
                        st.info("Chargez une facture et identifiez les produits pour accéder au rapprochement.")
                    else:
                        working_df = reconciliation_df.copy()
                        working_df["quantite_recue"] = pd.to_numeric(
                            working_df.get("quantite_recue", working_df.get("qte_init", 0)), errors="coerce"
                        ).fillna(0)
                        working_df["prix_achat_facture"] = pd.to_numeric(
                            working_df.get("prix_achat", working_df.get("prix_vente", 0)), errors="coerce"
                        ).fillna(0)
                        working_df["prix_achat_catalogue"] = pd.to_numeric(
                            working_df.get("prix_achat_catalogue", 0), errors="coerce"
                        ).fillna(0)
                        working_df["valeur_facturee"] = working_df["quantite_recue"] * working_df["prix_achat_facture"]
                        working_df["valeur_catalogue"] = working_df["quantite_recue"] * working_df["prix_achat_catalogue"]
                        working_df["ecart_prix_unitaire"] = (
                            working_df["prix_achat_facture"] - working_df["prix_achat_catalogue"]
                        )

                        metrics_cols = st.columns(3)
                        metrics_cols[0].metric("Lignes rapprochées", f"{len(working_df):,}".replace(",", " "))
                        metrics_cols[1].metric(
                            "Produits identifiés",
                            f"{int(working_df['produit_id'].notna().sum()):,}".replace(",", " "),
                        )
                        delta_total = working_df["valeur_facturee"].sum() - working_df["valeur_catalogue"].sum()
                        metrics_cols[2].metric(
                            "Écart vs catalogue",
                            f"{delta_total:,.2f} €".replace(",", " "),
                            delta=f"{delta_total:,.2f} €".replace(",", " "),
                            delta_color="inverse" if delta_total > 0 else "normal",
                        )

                        display_cols = [
                            "nom",
                            "produit_id",
                            "quantite_recue",
                            "prix_achat_facture",
                            "prix_achat_catalogue",
                            "ecart_prix_unitaire",
                            "valeur_facturee",
                            "valeur_catalogue",
                            "catalogue_nom",
                            "catalogue_categorie",
                            "codes",
                        ]
                        available_cols = [col for col in display_cols if col in working_df.columns]
                        st.dataframe(
                            working_df[available_cols],
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "nom": "Désignation facture",
                                "produit_id": st.column_config.NumberColumn("Produit ID", format="%d"),
                                "quantite_recue": st.column_config.NumberColumn("Quantité reçue", format="%.0f"),
                                "prix_achat_facture": st.column_config.NumberColumn("Prix facture (€)", format="%.2f €"),
                                "prix_achat_catalogue": st.column_config.NumberColumn(
                                    "Prix catalogue (€)", format="%.2f €"
                                ),
                                "ecart_prix_unitaire": st.column_config.NumberColumn(
                                    "Écart unitaire (€)", format="%+.2f €"
                                ),
                                "valeur_facturee": st.column_config.NumberColumn("Montant facture (€)", format="%.2f €"),
                                "valeur_catalogue": st.column_config.NumberColumn(
                                    "Montant catalogue (€)", format="%.2f €"
                                ),
                                "catalogue_nom": st.column_config.TextColumn("Produit catalogue"),
                                "catalogue_categorie": st.column_config.TextColumn("Catégorie"),
                                "codes": st.column_config.TextColumn("Codes-barres"),
                            },
                        )

                        form_cols = st.columns([1.6, 1, 1])
                        supplier_name = form_cols[0].text_input(
                            "Fournisseur / source", value=st.session_state.get("invoice_supplier_hint", "")
                        )
                        action_mode = form_cols[1].selectbox(
                            "Mode", ["Créer mouvements d'entrée", "Préparer bon de commande"],
                            key="invoice_pipeline_mode",
                        )
                        reception_date = form_cols[2].date_input(
                            "Date de réception",
                            value=st.session_state.get("invoice_pipeline_date")
                            or datetime.now().date(),
                            key="invoice_pipeline_date",
                        )

                        movements_df = working_df[working_df["produit_id"].notna()].copy()
                        movements_df["quantite_recue"] = pd.to_numeric(
                            movements_df["quantite_recue"], errors="coerce"
                        ).fillna(0)
                        movements_df = movements_df[movements_df["quantite_recue"] > 0]

                        action_cols = st.columns(2)
                        with action_cols[0]:
                            if st.button(
                                "Créer les mouvements", type="primary", key="invoice_pipeline_movements"
                            ):
                                if action_mode != "Créer mouvements d'entrée":
                                    st.info("Basculer en mode 'Créer mouvements d'entrée' pour enregistrer les mouvements.")
                                elif movements_df.empty:
                                    st.warning("Aucun produit identifié avec quantité reçue positive.")
                                else:
                                    reception_dt = datetime.combine(reception_date, datetime.min.time())
                                    result = register_invoice_reception(
                                        movements_df,
                                        username=st.session_state.get("username", ""),
                                        supplier=supplier_name,
                                        movement_type="ENTREE",
                                        reception_date=reception_dt,
                                    )
                                    if result.get("movements_created"):
                                        st.success(
                                            f"{result['movements_created']} mouvement(s) créé(s) pour {result['quantity_total']:.2f} unité(s)."
                                        )
                                        invalidate_data_caches(
                                            "products_list",
                                            "catalog",
                                            "movement_timeseries",
                                            "recent_movements",
                                        )
                                    else:
                                        st.warning("Aucun mouvement n'a été généré. Vérifiez les données sélectionnées.")

                        with action_cols[1]:
                            order_export = working_df[available_cols].to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "Télécharger le bon de commande",
                                data=order_export,
                                file_name="commande_reappro.csv",
                                mime="text/csv",
                                disabled=working_df.empty,
                            )

            with workspace_panel(
                "Mise à jour automatique des tarifs",
                "Comparez les prix facturés et alignez le catalogue tout en conservant la marge cible.",
                icon="💶",
                accent="amber",
            ):
                invoice_df = st.session_state.get("invoice_products_df")
                notice_message = st.session_state.get("invoice_price_update_notice")
                if notice_message:
                    st.success(notice_message)
                    st.session_state.pop("invoice_price_update_notice", None)

                if not isinstance(invoice_df, pd.DataFrame) or invoice_df.empty:
                    st.info("Chargez une facture et identifiez les produits pour accéder à la mise à jour des tarifs.")
                else:
                    control_cols = st.columns(3)
                    margin_pct = control_cols[0].slider(
                        "Marge minimale (%)",
                        min_value=10,
                        max_value=100,
                        value=int(st.session_state.get("invoice_price_margin", 40)),
                        step=5,
                        key="invoice_price_margin",
                    )
                    threshold_pct = control_cols[1].slider(
                        "Seuil d'ajustement (%)",
                        min_value=1,
                        max_value=50,
                        value=int(st.session_state.get("invoice_price_threshold", 10)),
                        step=1,
                        key="invoice_price_threshold",
                    )
                    control_cols[2].metric("Coefficient appliqué", f"× {(1 + margin_pct / 100):.2f}")

                    margin_ratio = max(float(margin_pct) / 100.0, 0.0)
                    threshold_ratio = max(float(threshold_pct) / 100.0, 0.0)

                    plan = prepare_invoice_price_updates(
                        invoice_df,
                        min_margin=margin_ratio,
                        delta_threshold=threshold_ratio,
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
                        st.success("Aucun ajustement de prix n'est nécessaire avec les paramètres actuels.")
                    else:
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
                                "delta_percent": st.column_config.NumberColumn(
                                    "Delta (%)", format="%.1f"
                                ),
                            },
                        )

                        if st.button(
                            "Appliquer les nouveaux tarifs",
                            key="apply_invoice_price_updates_button",
                            type="primary",
                        ):
                            with st.spinner("Mise à jour des prix en cours..."):
                                result = apply_invoice_price_updates(
                                    invoice_df,
                                    min_margin=margin_ratio,
                                    delta_threshold=threshold_ratio,
                                )

                            applied = int(result.get("applied_updates", 0))
                            errors = result.get("errors", [])
                            if applied:
                                st.session_state["invoice_price_update_notice"] = (
                                    f"{applied} produit(s) mis à jour selon la facture."
                                )
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
                                st.rerun()
                            elif errors:
                                for error_message in errors:
                                    st.error(error_message)
                            else:
                                st.info("Aucun produit n'a nécessité de mise à jour.")

                    skipped_rows = plan.get("skipped", [])
                    if skipped_rows:
                        with st.expander("Produits conservés (delta trop faible)"):
                            skipped_df = pd.DataFrame(skipped_rows)
                            st.dataframe(
                                skipped_df[
                                    [
                                        col
                                        for col in [
                                            "product_name",
                                            "ean",
                                            "current_sale_price",
                                            "proposed_sale_price",
                                            "delta_percent",
                                            "reason",
                                        ]
                                        if col in skipped_df.columns
                                    ]
                                ],
                                hide_index=True,
                                use_container_width=True,
                            )

            if isinstance(summary, dict):
                with workspace_panel(
                    "Résumé de l'import",
                    "Synthèse des lignes traitées et des actions réalisées.",
                    icon="✅",
                    accent="amber",
                ):
                    metric_cols = st.columns(4)
                    metric_cols[0].metric("Lignes reçues", summary.get("rows_received", 0))
                    metric_cols[1].metric("Traitées", summary.get("rows_processed", 0))
                    metric_cols[2].metric("Créées", summary.get("created", 0))
                    metric_cols[3].metric("Mises à jour", summary.get("updated", 0))

                    extra_cols = st.columns(3)
                    extra_cols[0].metric("Stocks initiaux", summary.get("stock_initialized", 0))
                    barcode_stats = summary.get("barcode", {})
                    extra_cols[1].metric("Codes ajoutés", barcode_stats.get("added", 0))
                    extra_cols[2].metric("Codes en conflit", barcode_stats.get("conflicts", 0))

                    if summary.get("errors"):
                        st.warning(f"{len(summary['errors'])} ligne(s) n'ont pas pu être importées.")
                        errors_df = pd.DataFrame(summary["errors"])
                        st.dataframe(errors_df, hide_index=True, use_container_width=True)
                    else:
                        st.success("Toutes les lignes valides ont été importées avec succès.")

        # ---------------- Importation ----------------

        with import_tab:
            imported_df = st.session_state.get("invoice_products_df")
            summary = st.session_state.get("invoice_import_summary")
            pending_count = int(len(imported_df)) if isinstance(imported_df, pd.DataFrame) else 0

            render_workspace_hero(
                eyebrow="Importation",
                title="Injectez rapidement des produits depuis vos fichiers",
                description="Chargez un texte de facture, ajustez les lignes, puis importez-les directement dans l'inventaire.",
                badges=["CSV prêt", "Vérification manuelle"],
                metrics=[
                    {"label": "Lignes prêtes", "value": str(pending_count)},
                    {"label": "Dernier import", "value": "OK" if summary else "À planifier"},
                ],
                tone="teal",
            )

            with workspace_panel(
                "Téléversement",
                "Ajoutez la facture à importer et sélectionnez la source.",
                icon="📂",
                accent="teal",
            ):
                uploaded_invoice_files = st.file_uploader(
                    "Déposer une facture Metro",
                    type=["pdf", "docx", "txt"],
                    key="import_invoice_file_uploader",
                    help="Les formats PDF, DOCX et TXT sont pris en charge.",
                    accept_multiple_files=True,
                )

                _process_uploaded_invoices(uploaded_invoice_files, "Import")
                _render_invoice_selector("Facture chargée", "import_invoice_selector")

            with workspace_panel(
                "Texte de la facture",
                "Collez ou corrigez le contenu avant l'analyse.",
                icon="📝",
                accent="teal",
            ):
                import_invoice_text = st.text_area(
                    "Texte à analyser",
                    value=st.session_state.get("invoice_text_input", ""),
                    key="import_invoice_text_input",
                    height=260,
                    placeholder="Collez ici la section produits de la facture si nécessaire...",
                )
                if import_invoice_text != st.session_state.get("invoice_text_input"):
                    st.session_state["invoice_text_input"] = import_invoice_text
                    st.session_state["extract_invoice_text_input"] = import_invoice_text

                col_extract_btn, col_reset_btn = st.columns(2)
                with col_extract_btn:
                    if st.button("Analyser le texte", key="import_invoice_extract_button", type="primary"):
                        text_to_parse = st.session_state.get("invoice_text_input", "")
                        if not text_to_parse.strip():
                            st.warning("Aucun texte à analyser. Téléversez une facture ou collez du texte.")
                        else:
                            df_extracted = invoice_extractor.extract_products_from_metro_invoice(text_to_parse)
                            st.session_state["invoice_products_df"] = df_extracted
                            st.session_state["invoice_import_summary"] = None
                            if df_extracted.empty:
                                st.warning("Aucune ligne produit détectée. Ajustez le texte et réessayez.")
                            else:
                                st.success(f"{len(df_extracted)} ligne(s) produit détectée(s). Vérifiez et corrigez-les ci-dessous.")
                with col_reset_btn:
                    if st.button("Réinitialiser l'extraction", key="import_invoice_reset_button"):
                        _reset_invoice_session_state()
                        st.session_state["invoice_reset_notice_origin"] = "import"
                        st.rerun()

                if st.session_state.get("invoice_reset_notice_origin") == "import":
                    st.info("Extraction réinitialisée.")
                    st.session_state.pop("invoice_reset_notice_origin", None)

                if st.session_state.get("invoice_raw_text"):
                    st.download_button(
                        "Télécharger le texte brut",
                        data=st.session_state["invoice_raw_text"].encode("utf-8"),
                        file_name=st.session_state.get("invoice_uploaded_name", "facture.txt"),
                        mime="text/plain",
                        key="import_invoice_raw_text_download",
                    )

            if isinstance(imported_df, pd.DataFrame) and not imported_df.empty:
                with workspace_panel(
                    "Produits détectés",
                    "Finalisez les informations avant import.",
                    icon="🧾",
                    accent="teal",
                ):
                    st.caption("Vérifiez et complétez les champs avant de valider l'importation.")

                    working_df = imported_df.copy()
                    if "quantite_recue" not in working_df.columns and "qte_init" in working_df.columns:
                        working_df["quantite_recue"] = working_df["qte_init"]
                    if "codes" in working_df.columns:
                        working_df["_code_lower"] = (
                            working_df["codes"].fillna("").astype(str).str.lower().str.strip()
                        )
                        matches_df = match_invoice_products(working_df)
                        if not matches_df.empty:
                            matches_df = matches_df.rename(
                                columns={
                                    "code": "_code_lower",
                                    "produit_id": "catalogue_id",
                                    "produit_nom": "catalogue_nom",
                                    "categorie": "catalogue_categorie",
                                }
                            )
                            working_df = working_df.merge(matches_df, on="_code_lower", how="left")
                            if "produit_id" not in working_df.columns:
                                working_df["produit_id"] = working_df["catalogue_id"]
                            else:
                                working_df["produit_id"] = working_df["produit_id"].fillna(
                                    working_df["catalogue_id"]
                                )
                        working_df.drop(columns=["_code_lower"], inplace=True, errors="ignore")

                    editable_df = st.data_editor(
                        working_df,
                        key="import_invoice_products_editor",
                        hide_index=True,
                        num_rows="dynamic",
                        use_container_width=True,
                        column_config={
                            "nom": st.column_config.TextColumn("Nom du produit"),
                            "prix_vente": st.column_config.NumberColumn("Prix de vente (€)", format="%.2f"),
                            "tva": st.column_config.NumberColumn("TVA (%)", format="%.2f"),
                            "qte_init": st.column_config.NumberColumn("Quantité", step=1, format="%.0f"),
                            "quantite_recue": st.column_config.NumberColumn(
                                "Quantité reçue", step=1, format="%.0f"
                            ),
                            "codes": st.column_config.TextColumn("Codes-barres"),
                            "produit_id": st.column_config.NumberColumn(
                                "Produit ID", help="Identifiant catalogue cible si le produit existe"
                            ),
                            "catalogue_id": st.column_config.NumberColumn(
                                "ID catalogue suggéré", disabled=True
                            ),
                            "catalogue_nom": st.column_config.TextColumn(
                                "Produit catalogue", disabled=True
                            ),
                            "catalogue_categorie": st.column_config.TextColumn(
                                "Catégorie catalogue", disabled=True
                            ),
                            "prix_achat_catalogue": st.column_config.NumberColumn(
                                "Prix achat catalogue (€)", format="%.2f", disabled=True
                            ),
                            "prix_vente_catalogue": st.column_config.NumberColumn(
                                "Prix vente catalogue (€)", format="%.2f", disabled=True
                            ),
                        },
                    )
                    editable_df = pd.DataFrame(editable_df)
                    for col in ("nom", "codes"):
                        if col in editable_df.columns:
                            editable_df[col] = editable_df[col].fillna("")
                    st.session_state["invoice_products_df"] = editable_df

                    col_download, col_import = st.columns(2)
                    with col_download:
                        csv_data = editable_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Télécharger le CSV extrait",
                            data=csv_data,
                            file_name=st.session_state.get("invoice_uploaded_name", "facture.txt").replace(".txt", ".csv"),
                            mime="text/csv",
                            key="import_invoice_csv_download",
                        )
                    with col_import:
                        if st.button("Importer ces produits", key="import_invoice_import_button", type="primary"):
                            with st.spinner("Import des produits en cours..."):
                                summary_result = products_loader.load_products_from_df(editable_df)
                            st.session_state["invoice_import_summary"] = summary_result
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
                            st.success("Importation terminée. Consultez le résumé ci-dessous.")
                            summary = summary_result

            with workspace_panel(
                "Rapprochement facture → commande",
                "Préparez les bons de réception et les mouvements de stock à partir de la facture importée.",
                icon="🔄",
                accent="teal",
            ):
                reconciliation_df = st.session_state.get("invoice_products_df")
                if not isinstance(reconciliation_df, pd.DataFrame) or reconciliation_df.empty:
                    st.info("Chargez une facture et identifiez les produits pour accéder au rapprochement.")
                else:
                    working_df = reconciliation_df.copy()
                    working_df["quantite_recue"] = pd.to_numeric(
                        working_df.get("quantite_recue", working_df.get("qte_init", 0)), errors="coerce"
                    ).fillna(0)
                    working_df["prix_achat_facture"] = pd.to_numeric(
                        working_df.get("prix_achat", working_df.get("prix_vente", 0)), errors="coerce"
                    ).fillna(0)
                    working_df["prix_achat_catalogue"] = pd.to_numeric(
                        working_df.get("prix_achat_catalogue", 0), errors="coerce"
                    ).fillna(0)
                    working_df["valeur_facturee"] = working_df["quantite_recue"] * working_df["prix_achat_facture"]
                    working_df["valeur_catalogue"] = working_df["quantite_recue"] * working_df["prix_achat_catalogue"]
                    working_df["ecart_prix_unitaire"] = (
                        working_df["prix_achat_facture"] - working_df["prix_achat_catalogue"]
                    )

                    metrics_cols = st.columns(3)
                    metrics_cols[0].metric("Lignes rapprochées", f"{len(working_df):,}".replace(",", " "))
                    metrics_cols[1].metric(
                        "Produits identifiés",
                        f"{int(working_df['produit_id'].notna().sum()):,}".replace(",", " "),
                    )
                    delta_total = working_df["valeur_facturee"].sum() - working_df["valeur_catalogue"].sum()
                    metrics_cols[2].metric(
                        "Écart vs catalogue",
                        f"{delta_total:,.2f} €".replace(",", " "),
                        delta=f"{delta_total:,.2f} €".replace(",", " "),
                        delta_color="inverse" if delta_total > 0 else "normal",
                    )

                    display_cols = [
                        "nom",
                        "produit_id",
                        "quantite_recue",
                        "prix_achat_facture",
                        "prix_achat_catalogue",
                        "ecart_prix_unitaire",
                        "valeur_facturee",
                        "valeur_catalogue",
                        "catalogue_nom",
                        "catalogue_categorie",
                        "codes",
                    ]
                    available_cols = [col for col in display_cols if col in working_df.columns]
                    st.dataframe(
                        working_df[available_cols],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "nom": "Désignation facture",
                            "produit_id": st.column_config.NumberColumn("Produit ID", format="%d"),
                            "quantite_recue": st.column_config.NumberColumn("Quantité reçue", format="%.0f"),
                            "prix_achat_facture": st.column_config.NumberColumn("Prix facture (€)", format="%.2f €"),
                            "prix_achat_catalogue": st.column_config.NumberColumn(
                                "Prix catalogue (€)", format="%.2f €"
                            ),
                            "ecart_prix_unitaire": st.column_config.NumberColumn(
                                "Écart unitaire (€)", format="%+.2f €"
                            ),
                            "valeur_facturee": st.column_config.NumberColumn("Montant facture (€)", format="%.2f €"),
                            "valeur_catalogue": st.column_config.NumberColumn(
                                "Montant catalogue (€)", format="%.2f €"
                            ),
                            "catalogue_nom": st.column_config.TextColumn("Produit catalogue"),
                            "catalogue_categorie": st.column_config.TextColumn("Catégorie"),
                            "codes": st.column_config.TextColumn("Codes-barres"),
                        },
                    )

                    form_cols = st.columns([1.6, 1, 1])
                    supplier_name = form_cols[0].text_input(
                        "Fournisseur / source", value=st.session_state.get("invoice_supplier_hint", "")
                    )
                    action_mode = form_cols[1].selectbox(
                        "Mode", ["Créer mouvements d'entrée", "Préparer bon de commande"],
                        key="invoice_pipeline_mode",
                    )
                    reception_date = form_cols[2].date_input(
                        "Date de réception",
                        value=st.session_state.get("invoice_pipeline_date")
                        or datetime.now().date(),
                        key="invoice_pipeline_date",
                    )

                    movements_df = working_df[working_df["produit_id"].notna()].copy()
                    movements_df["quantite_recue"] = pd.to_numeric(
                        movements_df["quantite_recue"], errors="coerce"
                    ).fillna(0)
                    movements_df = movements_df[movements_df["quantite_recue"] > 0]

                    action_cols = st.columns(2)
                    with action_cols[0]:
                        if st.button(
                            "Créer les mouvements", type="primary", key="invoice_pipeline_movements"
                        ):
                            if action_mode != "Créer mouvements d'entrée":
                                st.info("Basculer en mode 'Créer mouvements d'entrée' pour enregistrer les mouvements.")
                            elif movements_df.empty:
                                st.warning("Aucun produit identifié avec quantité reçue positive.")
                            else:
                                reception_dt = datetime.combine(reception_date, datetime.min.time())
                                result = register_invoice_reception(
                                    movements_df,
                                    username=st.session_state.get("username", ""),
                                    supplier=supplier_name,
                                    movement_type="ENTREE",
                                    reception_date=reception_dt,
                                )
                                if result.get("movements_created"):
                                    st.success(
                                        f"{result['movements_created']} mouvement(s) créé(s) pour {result['quantity_total']:.2f} unité(s)."
                                    )
                                    invalidate_data_caches(
                                        "products_list",
                                        "catalog",
                                        "movement_timeseries",
                                        "recent_movements",
                                    )
                                else:
                                    st.warning("Aucun mouvement n'a été généré. Vérifiez les données sélectionnées.")

                    with action_cols[1]:
                        order_export = working_df[available_cols].to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Télécharger le bon de commande",
                            data=order_export,
                            file_name="commande_reappro.csv",
                            mime="text/csv",
                            disabled=working_df.empty,
                        )

            if isinstance(summary, dict):
                with workspace_panel(
                    "Résumé de l'import",
                    "Synthèse des lignes traitées et des actions réalisées.",
                    icon="✅",
                    accent="teal",
                ):
                    metric_cols = st.columns(4)
                    metric_cols[0].metric("Lignes reçues", summary.get("rows_received", 0))
                    metric_cols[1].metric("Traitées", summary.get("rows_processed", 0))
                    metric_cols[2].metric("Créées", summary.get("created", 0))
                    metric_cols[3].metric("Mises à jour", summary.get("updated", 0))

                    extra_cols = st.columns(3)
                    extra_cols[0].metric("Stocks initiaux", summary.get("stock_initialized", 0))
                    barcode_stats = summary.get("barcode", {})
                    extra_cols[1].metric("Codes ajoutés", barcode_stats.get("added", 0))
                    extra_cols[2].metric("Codes en conflit", barcode_stats.get("conflicts", 0))

                    if summary.get("errors"):
                        st.warning(f"{len(summary['errors'])} ligne(s) n'ont pas pu être importées.")
                        errors_df = pd.DataFrame(summary["errors"])
                        st.dataframe(errors_df, hide_index=True, use_container_width=True)
                    else:
                        st.success("Toutes les lignes valides ont été importées avec succès.")

        # ---------------- Maintenance (Admin) ----------------

        with admin_tab:
            if st.session_state["user_role"] != "admin":
                st.error("Accès refusé. Seuls les administrateurs peuvent accéder à l'onglet Maintenance (Admin).")
            else:
                tool_statuses = check_backup_tools()
                missing_tools = [status for status in tool_statuses if not status.available]
                backups = list_backups()
                backup_count = len(backups)

                render_workspace_hero(
                    eyebrow="Maintenance",
                    title="Administrez la plateforme en toute confiance",
                    description="Supervisez les sauvegardes, vérifiez l'intégrité des données et pilotez les diagnostics avancés.",
                    badges=["Rôle admin", "Contrôle avancé"],
                    metrics=[
                        {"label": "Sauvegardes", "value": str(backup_count)},
                        {"label": "Outils PostgreSQL", "value": "OK" if not missing_tools else "À compléter"},
                    ],
                    tone="slate",
                )

                with workspace_panel(
                    "Pré-requis système",
                    "Statut des utilitaires nécessaires aux sauvegardes.",
                    icon="🛡️",
                    accent="slate",
                ):
                    st.markdown(
                        "ℹ️ **Pré-requis système** : l'utilisateur exécutant Streamlit doit disposer "
                        "du client PostgreSQL (`pg_dump` et `psql`). Sur Debian/Ubuntu, installez-le "
                        "via `apt install postgresql-client` ou fournissez les chemins via les "
                        "variables `PG_DUMP_PATH`/`PSQL_PATH`."
                    )

                    status_lines = []
                    for status in tool_statuses:
                        if status.available:
                            status_lines.append(
                                f"- ✅ `{status.name}` disponible : `{status.resolved}` (détecté via {status.source})."
                            )
                        else:
                            status_lines.append(
                                f"- ❌ `{status.name}` introuvable avec la configuration actuelle (`{status.configured}` depuis {status.source})."
                            )
                    st.markdown("\n".join(status_lines))

                    if missing_tools:
                        st.error(
                            "Installez le client PostgreSQL ou ajustez les variables d'environnement pour activer la sauvegarde et la restauration."
                        )
                    else:
                        st.success("Les utilitaires PostgreSQL requis sont disponibles.")

                with workspace_panel(
                    "Sauvegardes base de données",
                    "Créez, planifiez et contrôlez vos sauvegardes PostgreSQL.",
                    icon="💾",
                    accent="slate",
                ):
                    def _trigger_rerun():
                        try:
                            st.rerun()
                        except AttributeError:
                            st.experimental_rerun()

                    backup_directory = get_backup_directory()
                    backup_settings = load_backup_settings()
                    st.caption(
                        "Les fichiers générés sont conservés dans le dossier suivant : "
                        f"`{backup_directory.resolve()}`"
                    )

                    next_run = plan_next_backup(backup_settings, last_backup=backups[0] if backups else None)
                    if next_run:
                        st.info(
                            f"Prochaine sauvegarde planifiée le {next_run.strftime('%d/%m/%Y %H:%M')} (heure locale)."
                        )

                    feedback = st.session_state.pop("admin_backup_feedback", None)
                    if feedback:
                        level, message = feedback
                        display = getattr(st, level, st.info)
                        display(message)

                    schedule_cols = st.columns(3)
                    frequency = schedule_cols[0].selectbox(
                        "Fréquence",
                        options=["manual", "daily", "weekly"],
                        format_func=lambda value: {
                            "manual": "Manuel",
                            "daily": "Quotidienne",
                            "weekly": "Hebdomadaire",
                        }[value],
                        index=["manual", "daily", "weekly"].index(str(backup_settings.get("frequency", "manual"))),
                        key="backup_frequency",
                    )

                    try:
                        default_time = datetime.strptime(str(backup_settings.get("time", "02:00")), "%H:%M").time()
                    except ValueError:
                        default_time = datetime.strptime("02:00", "%H:%M").time()
                    scheduled_time = schedule_cols[1].time_input(
                        "Heure d'exécution",
                        value=default_time,
                        key="backup_schedule_time",
                    )

                    weekday_selection = backup_settings.get("weekday", 0)
                    if frequency == "weekly":
                        weekday = schedule_cols[2].selectbox(
                            "Jour",
                            options=list(range(7)),
                            format_func=lambda idx: [
                                "Lundi",
                                "Mardi",
                                "Mercredi",
                                "Jeudi",
                                "Vendredi",
                                "Samedi",
                                "Dimanche",
                            ][idx],
                            index=int(weekday_selection) % 7,
                            key="backup_schedule_weekday",
                        )
                    else:
                        schedule_cols[2].markdown("<small>Le jour est utilisé uniquement en mode hebdomadaire.</small>", unsafe_allow_html=True)
                        weekday = weekday_selection

                    retention_cols = st.columns(2)
                    retention_days = int(
                        retention_cols[0].number_input(
                            "Rétention (jours)",
                            min_value=1,
                            max_value=365,
                            value=int(backup_settings.get("retention_days", 30)),
                            key="backup_retention_days",
                        )
                    )
                    max_backups = int(
                        retention_cols[1].number_input(
                            "Nombre maximum de sauvegardes",
                            min_value=1,
                            max_value=200,
                            value=int(backup_settings.get("max_backups", 20)),
                            key="backup_retention_count",
                        )
                    )

                    notification_choices = ["Email", "Slack", "Webhook"]
                    notifications = st.multiselect(
                        "Notifications",
                        options=notification_choices,
                        default=[n for n in backup_settings.get("notifications", []) if n in notification_choices],
                        help="Choisissez les canaux à informer lors des sauvegardes.",
                        key="backup_notifications",
                    )
                    integrity_toggle = st.checkbox(
                        "Vérifier automatiquement l'intégrité après chaque sauvegarde",
                        value=bool(backup_settings.get("integrity_checks", True)),
                        key="backup_integrity_toggle",
                    )

                    if st.button("Enregistrer la planification", key="backup_schedule_save"):
                        save_backup_settings(
                            {
                                "frequency": frequency,
                                "time": scheduled_time.strftime("%H:%M"),
                                "weekday": int(weekday),
                                "retention_days": retention_days,
                                "max_backups": max_backups,
                                "notifications": notifications,
                                "integrity_checks": integrity_toggle,
                            }
                        )
                        st.session_state["admin_backup_feedback"] = (
                            "success",
                            "Planification mise à jour.",
                        )
                        _trigger_rerun()

                    stats = compute_backup_statistics(backups)
                    stats_cols = st.columns(3)
                    stats_cols[0].metric("Sauvegardes", str(len(backups)))
                    stats_cols[1].metric("Volume cumulé", f"{stats['total_size_mb']:.2f} Mo")
                    stats_cols[2].metric("Taille moyenne", f"{stats['average_size_mb']:.2f} Mo")

                    timeline_data = build_backup_timeline(backups)
                    if timeline_data:
                        timeline_df = pd.DataFrame(timeline_data)
                        timeline_df["created_at"] = pd.to_datetime(timeline_df["created_at"]).dt.tz_localize(None)
                        st.area_chart(timeline_df.set_index("created_at")["size_mb"], height=180)

                    prune_candidates = suggest_retention_cleanup(
                        backups,
                        retention_days=retention_days,
                        max_backups=max_backups,
                    )
                    if prune_candidates:
                        names = ", ".join(meta.name for meta in prune_candidates)
                        st.warning(
                            f"{len(prune_candidates)} sauvegarde(s) dépassent la politique de rétention : {names}.",
                            icon="🗑️",
                        )

                    st.text_input(
                        "Étiquette optionnelle pour la prochaine sauvegarde",
                        key="admin_backup_label",
                        placeholder="ex: apres_inventaire",
                        help="L'étiquette est ajoutée au nom du fichier pour faciliter l'identification.",
                    )

                    if st.button("Créer une sauvegarde maintenant", key="admin_backup_create", type="primary"):
                        label = st.session_state.get("admin_backup_label", "").strip()
                        with st.spinner("Création de la sauvegarde en cours..."):
                            try:
                                metadata = create_backup(label=label or None, database_url=DATABASE_URL)
                            except BackupError as exc:
                                st.error(f"Échec de la sauvegarde : {exc}")
                            else:
                                st.session_state["admin_backup_label"] = ""
                                st.session_state["admin_backup_feedback"] = (
                                    "success",
                                    f"Sauvegarde créée : {metadata.name} — {metadata.size_mb:.2f} Mo",
                                )
                                st.toast("Sauvegarde terminée", icon="💾")
                                _trigger_rerun()

                    if backups and st.button("Restaurer la dernière sauvegarde", key="backup_restore_latest"):
                        latest = backups[0]
                        with st.spinner("Restauration de la dernière sauvegarde..."):
                            try:
                                restore_backup(latest.name, database_url=DATABASE_URL)
                            except BackupError as exc:
                                st.error(f"Échec de la restauration : {exc}")
                            else:
                                st.session_state["admin_backup_feedback"] = (
                                    "success",
                                    f"Base restaurée depuis {latest.name}.",
                                )
                                st.toast("Restauration effectuée", icon="✅")
                                _trigger_rerun()

                    if st.button("Vérifier l'intégrité des sauvegardes", key="backup_integrity_check"):
                        report = integrity_report(backups)
                        if not report:
                            st.info("Aucune sauvegarde à analyser pour le moment.")
                        else:
                            report_df = pd.DataFrame(report)
                            report_df["created_at"] = pd.to_datetime(report_df["created_at"]).dt.strftime("%d/%m/%Y %H:%M")
                            st.dataframe(report_df, hide_index=True, use_container_width=True)

                    if not backups:
                        st.info("Aucune sauvegarde trouvée pour le moment.")
                    else:
                        st.warning(
                            "La restauration réinitialise la base avec le contenu du fichier sélectionné.",
                            icon="⚠️",
                        )
                        for index, backup in enumerate(backups):
                            with st.container():
                                cols = st.columns([3.2, 1.6, 1.2, 1.5, 1.3, 1.1])
                                cols[0].write(f"**{backup.name}**")
                                cols[1].write(backup.created_at.astimezone().strftime("%d/%m/%Y %H:%M"))
                                cols[2].write(f"{backup.size_mb:.2f} Mo")
                                mime = "application/gzip" if backup.path.suffix == ".gz" else "application/sql"
                                cols[3].download_button(
                                    "Télécharger",
                                    data=backup.path.read_bytes(),
                                    file_name=backup.name,
                                    mime=mime,
                                    key=f"backup_download_{index}",
                                    use_container_width=True,
                                )
                                if cols[4].button(
                                    "Restaurer",
                                    key=f"backup_restore_{index}",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Restauration de la base en cours..."):
                                        try:
                                            restore_backup(backup.name, database_url=DATABASE_URL)
                                        except BackupError as exc:
                                            st.error(f"Échec de la restauration : {exc}")
                                        else:
                                            st.session_state["admin_backup_feedback"] = (
                                                "success",
                                                f"Base restaurée depuis {backup.name}.",
                                            )
                                            st.toast("Restauration effectuée", icon="✅")
                                            _trigger_rerun()
                                if cols[5].button(
                                    "Supprimer",
                                    key=f"backup_delete_{index}",
                                    use_container_width=True,
                                ):
                                    try:
                                        delete_backup(backup.name)
                                    except BackupError as exc:
                                        st.error(f"Suppression impossible : {exc}")
                                    else:
                                        st.session_state["admin_backup_feedback"] = (
                                            "success",
                                            f"Sauvegarde supprimée : {backup.name}",
                                        )
                                        st.toast("Fichier supprimé", icon="🗑️")
                                        _trigger_rerun()

                with workspace_panel(
                    "Diagnostics et tables",
                    "Consultez les aperçus de tables et vérifiez la cohérence des mouvements.",
                    icon="🧮",
                    accent="slate",
                ):
                    tables_tab, diagnostics_tab = st.tabs(["Tables principales", "Diagnostic mouvements"])

                    with tables_tab:
                        counts_df = load_table_counts()
                        if counts_df.empty:
                            st.info("Impossible d'afficher les statistiques de tables pour le moment.")
                        else:
                            cols = st.columns(len(counts_df))
                            for col, (_, row) in zip(cols, counts_df.iterrows()):
                                col.metric(f"{row['table']}", f"{int(row['lignes'])} enregistrements")

                        for table_name in ["produits", "produits_barcodes", "mouvements_stock"]:
                            preview = load_table_preview(table_name)
                            if preview.empty:
                                st.warning(f"La table {table_name} ne contient aucune ligne (ou est inaccessible).")
                            else:
                                st.expander(
                                    f"Table '{table_name}' — aperçu des {len(preview)} dernières lignes",
                                    expanded=False,
                                ).dataframe(preview, use_container_width=True, hide_index=True)

                    with diagnostics_tab:
                        st.caption("Comparaison entre le stock calculé via les mouvements et le stock_actuel matérialisé.")
                        diag_df = load_stock_diagnostics()
                        if diag_df.empty:
                            st.success("Aucun écart détecté entre les mouvements et le stock matérialisé.")
                        else:
                            st.warning("Des écarts nécessitent une vérification manuelle.")
                            display_df = diag_df.copy()
                            display_df.columns = ["ID", "Produit", "Stock actuel", "Stock calculé", "Écart"]
                            st.dataframe(display_df, use_container_width=True, hide_index=True)

                        st.divider()
                        st.caption("20 derniers mouvements toutes sources confondues.")
                        diag_movements = load_recent_movements(limit=20, product_id=None)
                        if diag_movements.empty:
                            st.info("Aucun mouvement enregistré.")
                        else:
                            diag_movements = diag_movements.copy()
                            diag_movements["date_mvt"] = pd.to_datetime(diag_movements["date_mvt"]).dt.strftime("%Y-%m-%d %H:%M")
                            st.dataframe(diag_movements, use_container_width=True, hide_index=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ==============================================================================
    # --- FIN DU FLUX PRINCIPAL (Contrôle d'accès) ---
    # ==============================================================================

    elif authentication_status is False:
        st.error('Nom d\'utilisateur/mot de passe incorrect.')
    elif authentication_status is None:
        st.warning('Veuillez entrer votre nom d\'utilisateur et votre mot de passe.')

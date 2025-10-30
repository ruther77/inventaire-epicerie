# app.py

import os
import io
import math
import re
import json
from html import escape
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from functools import lru_cache
import streamlit_authenticator as stauth
import plotly.express as px
import invoice_extractor
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from backup_manager import (
    BackupError,
    BinaryStatus,
    check_backup_tools,
    create_backup,
    delete_backup,
    get_backup_directory,
    list_backups,
    restore_backup,
)

# Imports pour le Scanner et la Vidéo
import cv2 
from pyzbar.pyzbar import decode
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode, RTCConfiguration

# Importation des fonctions de gestion de la BDD et du chargeur 
from data_repository import (
    DATABASE_URL,
    query_df,
    exec_sql,
    exec_sql_return_id,
    get_engine,
    get_product_details,
    get_product_options,
)
from inventory_service import *
import products_loader
import invoice_extractor

# --- FONCTION POUR CHARGER LE CSS EXTERNE (style.css) ---
def local_css(file_name):
    """Charge un fichier CSS externe et l'injecte dans l'application Streamlit."""
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    
    try:
        with open(file_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        current_dir = os.getcwd()
        st.error(f"Erreur: Le fichier de style '{file_name}' est introuvable. Chemin relatif tenté (CWD): {current_dir}/{file_name}. Le fichier n'est PAS dans le conteneur ou le CWD est incorrect.")
        
        
# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Inventaire Épicerie", layout="wide", page_icon="📦")

# --- CHARGEMENT DU STYLE CSS PERSONNALISÉ ---
local_css("style.css")

# --- Initialisation des Variables de Session ---
if "last_barcode" not in st.session_state:
    st.session_state["last_barcode"] = None
if "current_frame_count" not in st.session_state:
    st.session_state["current_frame_count"] = 0
if "cart" not in st.session_state:
    st.session_state["cart"] = []
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

MAX_INVOICE_UPLOADS = 20
INVOICE_SELECTOR_KEYS = ("extract_invoice_selector", "import_invoice_selector")
INVOICE_FILE_UPLOADER_KEYS = (
    "extract_invoice_file_uploader",
    "import_invoice_file_uploader",
)


def _ensure_cart_state() -> List[Dict[str, Any]]:
    """Retourne la liste du panier depuis l'état de session en garantissant son existence."""

    return st.session_state.setdefault("cart", [])


def _clear_cart() -> None:
    """Vide complètement le panier et force le rafraîchissement de la session."""

    st.session_state["cart"] = []




@st.cache_data(ttl=180)
def load_customer_catalog() -> pd.DataFrame:
    """Charge un catalogue orienté client avec informations agrégées."""

    sql_query = """
        SELECT
            p.id,
            p.nom,
            p.categorie,
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

    try:
        df = query_df(sql_query)
    except Exception as exc:
        st.error(
            "Impossible de charger le catalogue client. Vérifiez que les vues SQL sont déployées (v_top_ventes_30j).\n"
            f"Détail: {exc}"
        )
        return pd.DataFrame(columns=["id", "nom", "categorie", "prix_vente", "stock_actuel", "ventes_30j"])

    if df.empty:
        return df.assign(
            categorie=[], prix_vente=[], stock_actuel=[], ventes_30j=[]
        )

    expected_cols = {"categorie", "prix_vente", "stock_actuel", "ventes_30j"}
    for col in expected_cols:
        if col not in df.columns:
            df[col] = 0

    numeric_cols = ["prix_vente", "stock_actuel", "ventes_30j"]
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

    return df


@st.cache_data(ttl=120)
def load_trending_products(limit: int = 6) -> pd.DataFrame:
    """Retourne les produits les plus vendus récemment."""

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


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_product_image_url(ean: str | None) -> str | None:
    """Retourne une URL d'image OpenFoodFacts pour un code-barres donné."""

    if not ean:
        return None

    sanitized = re.sub(r"\D", "", str(ean)).strip()
    if len(sanitized) < 8:
        return None

    api_url = f"https://world.openfoodfacts.org/api/v0/product/{sanitized}.json"
    request = Request(api_url, headers={"User-Agent": "InventaireEpicerie/1.0 (+streamlit)"})

    try:
        with urlopen(request, timeout=5) as response:
            payload = json.load(response)
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, ValueError):
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


def _build_product_card(product: dict[str, Any]) -> str:
    """Construit un bloc HTML pour une carte produit de la vitrine."""

    name = escape(str(product.get("nom", "")))
    category = escape(str(product.get("categorie", "Autre")))
    price = float(product.get("prix_vente") or 0.0)
    stock = float(product.get("stock_actuel") or 0.0)
    ventes = float(product.get("ventes_30j") or 0.0)

    if stock <= 0:
        stock_label = "Rupture"
        stock_class = "is-danger"
    elif stock < 5:
        stock_label = "Stock bas"
        stock_class = "is-warning"
    else:
        stock_label = "Disponible"
        stock_class = "is-success"

    ean = product.get("ean")
    image_url = _fetch_product_image_url(ean)

    if image_url:
        media_html = (
            "<div class=\"catalog-card__media\">"
            f"<img src=\"{escape(str(image_url), quote=True)}\" alt=\"Visuel produit {name}\" "
            "loading=\"lazy\" decoding=\"async\"/>"
            "</div>"
        )
    else:
        placeholder_initial = escape((str(product.get("nom", ""))[:1] or "#").upper())
        media_html = (
            "<div class=\"catalog-card__media catalog-card__media--placeholder\" "
            "aria-label=\"Visuel indisponible\">"
            f"<span>{placeholder_initial}</span>"
            "</div>"
        )

    return f"""
    <div class="catalog-card">
        {media_html}
        <div class="catalog-card__head">
            <span class="catalog-card__category">{category}</span>
            <span class="catalog-card__stock {stock_class}">{stock_label}</span>
        </div>
        <h4 class="catalog-card__title">{name}</h4>
        <div class="catalog-card__price">{price:,.2f} €</div>
        <div class="catalog-card__meta">
            <span>Stock: {stock:,.0f}</span>
            <span>Ventes 30j: {ventes:,.0f}</span>
        </div>
    </div>
    """


def _render_product_cards(df: pd.DataFrame, columns: int = 3) -> None:
    """Affiche une grille responsive de cartes produit."""

    if df.empty:
        st.info("Aucun produit à afficher pour le moment.")
        return

    records = df.to_dict("records")
    columns = max(1, int(columns))

    for start in range(0, len(records), columns):
        cols = st.columns(columns)
        for col, product in zip(cols, records[start:start + columns]):
            with col:
                card_html = _build_product_card(product)
                st.markdown(card_html, unsafe_allow_html=True)

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

@st.cache_data(ttl=300)
def cached_product_options() -> dict[str, int]:
    """Retourne un dictionnaire {nom: id} mis en cache pour les sélecteurs."""
    return {name: pid for name, pid in get_product_options()}


def update_product_data():
    """
    Callback exécuté lorsque le produit dans la selectbox d'ajustement change.
    Charge immédiatement les détails du produit et stocke les informations de stock.
    """
    # 1. Récupérer le nom du produit sélectionné (via la 'key' adj_product)
    selected_product_name = st.session_state.adj_product 
    
    # 2. Trouver l'ID du produit (en utilisant le dictionnaire product_options)
    # NOTE: Vous devez vous assurer que product_options (produit_nom -> produit_id) est accessible globalement 
    # ou passé en argument si nécessaire. Assumons qu'il est accessible.
    
    # Si 'product_options' est une variable locale à la fonction Streamlit, vous devrez peut-être la mettre dans st.session_state 
    # ou refactoriser. Pour l'exemple, nous allons chercher l'ID via le nom.
    
    # On va assumer que 'product_options' est un dictionnaire (nom -> id) créé avant la selectbox.
    # Dans l'état de votre code, product_options n'est pas fourni, nous allons le charger.

    # 🚨 Hypothèse de travail: product_options est un dictionnaire NOM -> ID créé au début de la page.
    # Nous allons donc utiliser la fonction get_product_id_by_name pour plus de robustesse.
    
    # --- Code à ajouter à inventory_service.py OU à implémenter dans data_repository.py si la fonction n'existe pas ---
    # La fonction devrait ressembler à: get_product_id_by_name(name)
    #
    # Pour l'exemple, nous allons directement faire la recherche de détails pour avoir l'ID:
    
    # Reconstruire la liste des options (si elles sont cachées) pour trouver l'ID
    product_options = cached_product_options()
    
    selected_product_id = product_options.get(selected_product_name)

    # 3. Charger les détails immédiatement
    if selected_product_id:
        product_details = get_product_details(selected_product_id)
        
        if product_details:
            # Mettre à jour les variables de session utilisées pour l'affichage
            st.session_state.ajust_produit_id = product_details['id']
            st.session_state.ajust_stock_actuel = float(product_details['quantite_stock'])
            st.session_state.ajust_nom = product_details['nom']
            st.session_state.ajust_error = None # Effacer toute erreur précédente
        else:
             st.session_state.ajust_error = "Produit non trouvé après sélection."
    else:
        st.session_state.ajust_error = "Sélection de produit invalide."

@st.cache_data(ttl=300)
def load_products_list():
    sql_query = """
        SELECT
            p.id,
            p.nom,
            p.prix_vente,
            p.tva,
            p.stock_actuel AS quantite_stock,
            COALESCE(string_agg(pb.code, ', ' ORDER BY pb.code), '') AS codes_barres,
            CASE
                WHEN p.stock_actuel <= 0 THEN '❌ Rupture'
                WHEN p.stock_actuel < 5 THEN '⚠️ Faible'
                ELSE '✅ OK'
            END AS statut_stock
        FROM
            produits p
        LEFT JOIN
            produits_barcodes pb ON p.id = pb.produit_id
        GROUP BY
            p.id, p.nom, p.prix_vente, p.tva, p.stock_actuel
        ORDER BY
            p.nom;
    """
    try:
        df = query_df(sql_query)
        df['statut_stock'] = df['quantite_stock'].apply(lambda x: 'Stock OK' if x > 5 else ('Alerte Basse' if x > 0 else 'Épuisé'))
        return df
    except Exception as e:
        st.error(f"Erreur critique de chargement des produits: {e}. Vérifiez la vue 'v_stock_produits'.")
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_movement_timeseries(window_days: int = 30, product_id: int | None = None) -> pd.DataFrame:
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
        base_sql += " AND m.produit_id = :pid"
        params["pid"] = int(product_id)

    base_sql += """
        GROUP BY 1, m.type
        ORDER BY jour ASC, m.type
    """

    try:
        df = query_df(base_sql, params=params)
        if not df.empty:
            df["jour"] = pd.to_datetime(df["jour"]).dt.date
        return df
    except Exception as exc:
        st.error(f"Impossible de charger l'historique agrégé des mouvements: {exc}")
        return pd.DataFrame(columns=["jour", "type", "quantite"])


@st.cache_data(ttl=60)
def load_recent_movements(limit: int = 100, product_id: int | None = None) -> pd.DataFrame:
    sql = """
        SELECT
            m.date_mvt,
            p.nom AS produit,
            m.type,
            m.quantite,
            m.source
        FROM mouvements_stock m
        JOIN produits p ON p.id = m.produit_id
    """

    params: dict[str, int] = {"limit": int(limit)}

    if product_id is not None:
        sql += " WHERE m.produit_id = :pid"
        params["pid"] = int(product_id)

    sql += " ORDER BY m.date_mvt DESC LIMIT :limit"

    try:
        return query_df(sql, params=params)
    except Exception as exc:
        st.error(f"Impossible de charger les mouvements récents: {exc}")
        return pd.DataFrame(columns=["date_mvt", "produit", "type", "quantite", "source"])


@st.cache_data(ttl=60)
def load_table_preview(table_name: str, limit: int = 20) -> pd.DataFrame:
    allowed = {"produits", "produits_barcodes", "mouvements_stock"}
    if table_name not in allowed:
        raise ValueError(f"Table non autorisée pour l'aperçu: {table_name}")

    try:
        limit_value = max(1, int(limit))
    except (TypeError, ValueError):
        limit_value = 20

    sql = f"SELECT * FROM public.{table_name} ORDER BY id DESC LIMIT {limit_value}"

    try:
        return query_df(sql)
    except Exception as exc:
        st.warning(f"Impossible de lire la table {table_name}: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_table_counts() -> pd.DataFrame:
    sql = """
        SELECT 'produits' AS table, COUNT(*) AS lignes FROM produits
        UNION ALL
        SELECT 'produits_barcodes' AS table, COUNT(*) AS lignes FROM produits_barcodes
        UNION ALL
        SELECT 'mouvements_stock' AS table, COUNT(*) AS lignes FROM mouvements_stock
    """

    try:
        return query_df(sql)
    except Exception as exc:
        st.error(f"Impossible de compter les enregistrements des tables principales: {exc}")
        return pd.DataFrame(columns=["table", "lignes"])


@st.cache_data(ttl=60)
def load_stock_diagnostics() -> pd.DataFrame:
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

    try:
        return query_df(sql)
    except Exception as exc:
        st.error(f"Impossible de calculer le diagnostic stock/mouvements: {exc}")
        return pd.DataFrame(columns=["id", "nom", "stock_actuel", "stock_calcule", "ecart"])


# --- Registre centralisé pour l'invalidation des caches ---
CACHE_REGISTRY: dict[str, Any] = {}


def register_cache(name: str, func) -> None:
    """Enregistre une fonction cacheable pour l'invalidation orchestrée."""

    CACHE_REGISTRY[name] = func


def invalidate_data_caches(*names: str) -> None:
    """Vide les caches ciblés afin de garder les vues synchronisées après une mise à jour."""

    if not names:
        names = tuple(CACHE_REGISTRY.keys())

    for cache_name in names:
        cache_func = CACHE_REGISTRY.get(cache_name)
        if cache_func is None:
            continue
        try:
            cache_func.clear()
        except Exception as exc:
            st.warning(
                f"Impossible de vider le cache '{cache_name}'. Détail: {exc}",
                icon="⚠️",
            )


# Inscription des caches existants
register_cache("catalog", load_customer_catalog)
register_cache("trending", load_trending_products)
register_cache("product_options", cached_product_options)
register_cache("products_list", load_products_list)
register_cache("movement_timeseries", load_movement_timeseries)
register_cache("recent_movements", load_recent_movements)
register_cache("table_preview", load_table_preview)
register_cache("table_counts", load_table_counts)
register_cache("stock_diagnostics", load_stock_diagnostics)

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

name, authentication_status, username = authenticator.login('Connexion à l\'Inventaire', 'main')

if authentication_status:

    # --- UI Setup et Définition des Onglets ---
    st.session_state["user_role"] = credentials["usernames"][username]["role"]
    st.session_state["username"] = username

    st.title("📦 Inventaire — Gestion Complète")
    st.sidebar.caption(f'Bienvenue, **{name}** (Rôle: **{st.session_state["user_role"]}**)')
    authenticator.logout('Déconnexion', 'sidebar')

    # Définition des onglets fonctionnels de l'application
    (
        showcase_tab,
        pos_tab,
        catalog_tab,
        mvt_tab,
        dash_tab,
        scanner_tab,
        extract_tab,
        import_tab,
        admin_tab,
    ) = st.tabs([
        "Vitrine",
        "Vente (PoS)",
        "Catalogue",
        "Stock & Mvt",
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

            st.markdown(
                f"""
                <section class="catalog-hero catalog-hero--sunset">
                    <div class="catalog-hero__content">
                        <p class="catalog-hero__eyebrow">Expérience boutique</p>
                        <h2>Animez votre vitrine digitale avec des insights temps réel.</h2>
                        <p>Visualisez la vitalité de vos rayons, identifiez les alertes prioritaires et préparez vos opérations commerciales en toute confiance.</p>
                        <div class="catalog-hero__actions">
                            <span class="catalog-hero__chip">Nouveautés</span>
                            <span class="catalog-hero__chip catalog-hero__chip--outline">{total_products} références suivies</span>
                        </div>
                    </div>
                    <div class="catalog-hero__glance">
                        <div class="hero-stat">
                            <span class="hero-stat__label">Valeur stock</span>
                            <span class="hero-stat__value">{_format_number(stock_value)} €</span>
                        </div>
                        <div class="hero-stat">
                            <span class="hero-stat__label">Potentiel 30&nbsp;j</span>
                            <span class="hero-stat__value">{_format_number(potential_sales)} €</span>
                        </div>
                        <div class="hero-stat">
                            <span class="hero-stat__label">Alertes actives</span>
                            <span class="hero-stat__value hero-stat__value--accent">{low_stock_count}</span>
                        </div>
                    </div>
                </section>
                """,
                unsafe_allow_html=True,
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
                    if ean_value:
                        detail_image = _fetch_product_image_url(ean_value)
                        if detail_image:
                            st.image(detail_image, caption=f"EAN {ean_value}", width=240)
                        else:
                            st.caption("Aucun visuel trouvé pour ce code-barres.")


    # ---------------- Vente (PoS) ----------------
    with pos_tab:
        st.header("Terminal Point de Vente (PoS)")
        
        col_input, col_cart = st.columns([1, 2])
        
        with col_cart:
            st.markdown('<div class="app-tile">', unsafe_allow_html=True)
            st.subheader("🛒 Panier Actuel")

            cart_items = _ensure_cart_state()
            cart_df = _normalize_cart_dataframe(cart_items)

            if cart_df.empty:
                st.info("Le panier est vide. Veuillez ajouter des produits.")

            cart_df["prix_total"] = cart_df["prix_vente"] * cart_df["qty"]
            cart_df["total_tva"] = cart_df["prix_total"] * (cart_df["tva"] / 100)

            if not cart_df.empty:
                st.dataframe(
                    cart_df[["nom", "qty", "prix_vente", "prix_total"]],
                    column_config={
                        "nom": "Produit",
                        "qty": "Quantité",
                        "prix_vente": st.column_config.NumberColumn("P.U. (€)", format="%.2f €"),
                        "prix_total": st.column_config.NumberColumn("Total Ligne (€)", format="%.2f €"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

            total_ttc = float(cart_df["prix_total"].sum()) if not cart_df.empty else 0.0
            total_tva = float(cart_df["total_tva"].sum()) if not cart_df.empty else 0.0
            total_ht = total_ttc - total_tva

            col_tva, col_ht, col_ttc = st.columns(3)

            col_ht.metric("Total HT", f"{total_ht:.2f} €")
            col_tva.metric("Total TVA", f"{total_tva:.2f} €")
            col_ttc.metric("Total TTC", f"{total_ttc:.2f} €", delta_color="off")

            if st.button("Vider le Panier", help="Annule la transaction en cours.", key="clear_cart_btn"):
                _clear_cart()
                st.rerun()

            st.divider()
            if cart_items:
                if st.button("Finaliser la Vente", key="btn_finalize_sale", type="primary"):
                    with st.spinner("Traitement de la vente en cours..."):
                        sale_ok, sale_msg = process_sale_transaction(
                            cart_items,
                            st.session_state.get("username", "inconnu"),
                        )

                    if sale_ok:
                        st.success("Vente finalisée et stock mis à jour ✅")
                        _clear_cart()
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
                        error_msg = sale_msg or "Échec de la vente. Vérifiez le stock disponible et réessayez."
                        st.error(error_msg)

            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_input:
            st.markdown('<div class="app-tile">', unsafe_allow_html=True) 
            
            st.subheader("🛒 Saisie Produit")

            # --- 1. CHARGEMENT DYNAMIQUE DES PRODUITS ---
            try:
                product_options = cached_product_options()
                product_names = ["-- Sélectionner un produit --"] + list(product_options.keys())

                initial_input = st.session_state.get("last_barcode", "")
                if st.session_state.get("last_barcode"):
                    st.session_state["last_barcode"] = None

            except Exception as e:
                st.error(f"Erreur lors du chargement des produits: {e}")
                product_names = ["-- Erreur de chargement --"]
                product_options = {}

            # --- 2. FORMULAIRE DE SAISIE ---
            with st.form("pos_input_form", clear_on_submit=False):
                
                selected_product_name = st.selectbox(
                    "Sélectionner un Produit (Nom)", 
                    options=product_names,
                    index=0, 
                    key="pos_product_selectbox"
                )
                
                qty_to_add = st.number_input("Quantité", min_value=1, value=1, step=1, key='pos_qty_add')
                add_button = st.form_submit_button("Ajouter au Panier")
                
                # --- 3. LOGIQUE D'AJOUT ---
                if add_button and selected_product_name != "-- Sélectionner un produit --":
                    selected_product_id = product_options.get(selected_product_name)
                    
                    if selected_product_id:
                        st.session_state["product_to_add_id"] = selected_product_id
                        st.session_state["product_to_add_qty"] = qty_to_add
                        st.session_state["add_to_cart_triggered"] = True
                    else:
                        st.error("Erreur: ID produit non trouvé après sélection.")

                elif add_button:
                    st.warning("Veuillez sélectionner un produit pour l'ajouter au panier.")
            
            # --- BLOC D'EXÉCUTION DU PANIER ---
            if st.session_state.get("add_to_cart_triggered", False):

                product_id = st.session_state.get("product_to_add_id")
                quantity = st.session_state.get("product_to_add_qty")

                if product_id and quantity > 0:
                    try:
                        product_row = df_products[df_products['id'] == product_id].iloc[0]

                        quantity = int(quantity)
                        cart_items = _ensure_cart_state()

                        product_data = {
                            'id': int(product_row['id']),
                            'nom': product_row['nom'],
                            'prix_vente': float(product_row['prix_vente']),
                            'tva': float(product_row['tva']),
                            'qty': quantity
                        }

                        found = False
                        for item in cart_items:
                            if item['id'] == product_id:
                                item['qty'] += quantity
                                found = True
                                break

                        if not found:
                            cart_items.append(product_data)

                        st.toast(f"✅ {quantity} x {product_data['nom']} ajouté(s) au panier !", icon='🛒')
                        st.rerun()
                        
                    except IndexError:
                        st.error(f"Erreur : Produit ID {product_id} non trouvé dans le catalogue.")
                    except Exception as e:
                        st.error(f"Erreur inattendue lors de l'ajout au panier : {e}")

                # Réinitialisation des variables de session
                if "product_to_add_id" in st.session_state:
                    del st.session_state["product_to_add_id"]
                if "product_to_add_qty" in st.session_state:
                    del st.session_state["product_to_add_qty"]
                if "add_to_cart_triggered" in st.session_state:
                    del st.session_state["add_to_cart_triggered"]

            st.markdown('</div>', unsafe_allow_html=True)


    # ---------------- Catalogue ----------------
    with catalog_tab:
        st.header("Catalogue Produits et Administration")
        
        # --- LOGIQUE DE DÉSACTIVATION DES COLONNES ---
        non_editable_columns = ['id', 'quantite_stock', 'statut_stock',"codes_barres"]
        if st.session_state.get("user_role") == "admin":
            disabled_cols = non_editable_columns 
        else:
            disabled_cols = ['nom', 'prix_vente', 'tva', 'quantite_stock', 'statut_stock'] 
        
        st.caption("Le stock ne peut être modifié que via les mouvements (ventes/ajustements), pas ici.")
        
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
                    "codes_barres": st.column_config.TextColumn("Codes-barres (Séparés par ', ')"),
                    "statut_stock": st.column_config.TextColumn("Statut Stock")
                }
            )

            # Logique de persistance des modifications et suppression
            if st.session_state.get("user_role") == "admin":
                
                col_save, col_delete = st.columns([1, 1])
                
                # --- Enregistrement des modifications ---
                if col_save.button("Enregistrer les modifications du Catalogue", key="save_catalog_changes", type="primary"):
                    try:
                        changes = st.session_state["catalog_editor"]["edited_rows"]
                        
                        if changes:
                            updates_count = 0
                            for index, row_changes in changes.items():
                                product_id = df_products.loc[index, 'id']
                                
                                set_clauses = [f"{col}=:{col}" for col in row_changes.keys() if col not in non_editable_columns]
                                
                                if set_clauses:
                                    sql = f"UPDATE produits SET {', '.join(set_clauses)} WHERE id = :id"
                                    params = row_changes
                                    params['id'] = product_id
                                    exec_sql(text(sql).bindparams(**params))
                                    updates_count += 1

                            st.success(f"{updates_count} produit(s) mis à jour avec succès!")
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
                            st.info("Aucune modification n'a été détectée dans le tableau.")
                    
                    except Exception as e:
                        st.error(f"Erreur lors de l'enregistrement: {e}")
                
                # --- Suppression de produits ---
                product_to_delete = col_delete.selectbox(
                    "Sélectionner un produit à supprimer", 
                    df_products['nom'], 
                    index=None
                )
                if product_to_delete:
                    id_to_delete = df_products[df_products['nom'] == product_to_delete]['id'].iloc[0]
                    if col_delete.button(f"Confirmer la Suppression de {product_to_delete}", key="confirm_delete"):
                        try:
                            exec_sql(text("DELETE FROM produits WHERE id = :pid").bindparams(pid=id_to_delete))
                            st.toast(f"✅ Produit '{product_to_delete}' et données associées supprimés.", icon='🗑️')
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
                            st.error(f"Erreur lors de la suppression: {e}. Des contraintes de BDD peuvent bloquer.")

        st.divider()

        # Bloc d'ajout rapide de produit
        if st.session_state.get("user_role") == "admin":
            st.subheader("Ajout Rapide de Produit")
            
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
                                codes_list = [c.strip() for c in new_codes.split(';') if c.strip()]
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
        st.header("Gestion des Mouvements de Stock")

        if df_products.empty:
            st.info("Veuillez ajouter des produits au catalogue d'abord.")
            st.stop()

        product_options = cached_product_options()
        product_names = list(product_options.keys())
        filter_products = ["Tous les produits"] + product_names

        col_filter_product, col_filter_window, col_filter_limit = st.columns([3, 1, 1])
        selected_product_name = col_filter_product.selectbox(
            "Produit suivi",
            filter_products,
            key="movement_filter_product"
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

        if movement_ts.empty:
            st.info("Aucun mouvement enregistré pour la période sélectionnée.")
        else:
            total_entries = float(movement_ts.loc[movement_ts['type'] == 'ENTREE', 'quantite'].sum())
            total_outputs = float(movement_ts.loc[movement_ts['type'] == 'SORTIE', 'quantite'].sum())
            net_balance = total_entries - total_outputs

            col_metrics = st.columns(3)
            col_metrics[0].metric("Entrées enregistrées", f"+{total_entries:.2f}")
            col_metrics[1].metric("Sorties enregistrées", f"-{total_outputs:.2f}")
            col_metrics[2].metric("Variation nette", f"{net_balance:+.2f}")

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

        st.caption("Les données ci-dessus sont actualisées après chaque vente ou ajustement.")

        st.subheader("Mouvements récents détaillés")
        recent_display = recent_movements.copy()
        if recent_display.empty:
            st.info("Aucun mouvement à afficher pour le filtre en cours.")
        else:
            recent_display["date_mvt"] = pd.to_datetime(recent_display["date_mvt"]).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(recent_display, use_container_width=True, hide_index=True)

        st.divider()

        if st.session_state.get("user_role") == "admin":
            with st.form("stock_adjustment_form", clear_on_submit=True):
                st.subheader("Ajustement/Inventaire de Stock (Admin)")

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
                                """
                                INSERT INTO mouvements_stock (produit_id, type, quantite, source)
                                VALUES (:pid, :type, :quantite, :source)
                                """
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


    # ---------------- Dashboard ----------------
    with dash_tab:
        st.header("Tableau de Bord de l'Inventaire")
        
        # --- Requêtes SQL pour charger les données du Dashboard ---
        try:
            # 1. Requête des indicateurs clés (KPIs)
            df_kpis = query_df("""
                SELECT 
                    COUNT(id) AS total_produits,
                    SUM(quantite_stock * prix_vente) AS valeur_stock_ht,
                    SUM(quantite_stock) AS quantite_stock_total,
                    SUM(CASE WHEN quantite_stock <= 5 AND quantite_stock > 0 THEN 1 ELSE 0 END) AS alerte_stock_bas,
                    SUM(CASE WHEN quantite_stock = 0 THEN 1 ELSE 0 END) AS stock_epuise
                FROM v_stock_produits
            """)

            # 2. Requête pour les 5 produits les plus stockés (en valeur)
            df_top_stock_value = query_df("""
                SELECT nom, (quantite_stock * prix_vente) as valeur_stock
                FROM v_stock_produits
                ORDER BY valeur_stock DESC
                LIMIT 5
            """)

            # 3. Requête pour les 5 produits ayant généré le plus de sorties (ventes)
            df_top_sales = query_df("""
                SELECT 
                    p.nom, 
                    SUM(m.quantite) AS quantite_vendue
                FROM mouvements_stock m
                JOIN produits p ON m.produit_id = p.id
                WHERE m.type = 'SORTIE'
                GROUP BY p.nom
                ORDER BY quantite_vendue DESC
                LIMIT 5
            """)
            
            # 4. Requête du Stock par Statut
            df_status_count = df_products.groupby('statut_stock').size().reset_index(name='Nombre')

        except Exception as e:
            st.error(f"Erreur lors du chargement des données du tableau de bord: {e}")
            df_kpis = pd.DataFrame({'total_produits': [0], 'valeur_stock_ht': [0.0], 'quantite_stock_total': [0.0], 'alerte_stock_bas': [0], 'stock_epuise': [0]})
            df_top_stock_value = pd.DataFrame({'nom': [], 'valeur_stock': []})
            df_top_sales = pd.DataFrame({'nom': [], 'quantite_vendue': []})
            df_status_count = pd.DataFrame({'statut_stock': ['Stock OK', 'Alerte Basse', 'Épuisé'], 'Nombre': [0, 0, 0]})
        
        # Affichage des métriques (KPIs)
        col1, col2, col3, col4, col5 = st.columns(5)
        
        kpis = df_kpis.iloc[0]
        
        with col1:
            st.metric("Total Produits", f"{kpis['total_produits']}")
        with col2:
            st.metric("Valeur Stock HT (€)", f"💰 {kpis['valeur_stock_ht']:.2f} €")
        with col3:
            st.metric("Quantité Totale", f"{kpis['quantite_stock_total']:.2f}")
        with col4:
            alert_value = int(kpis['alerte_stock_bas'])
            st.metric("Produits en Alerte", f"⚠️ {alert_value}", delta=alert_value, delta_color="inverse")
        with col5:
            exhausted_value = int(kpis['stock_epuise'])
            st.metric("Produits Épuisés", f"❌ {exhausted_value}", delta=exhausted_value, delta_color="inverse")
        
        st.divider()
        
        col_chart_1, col_chart_2, col_chart_3 = st.columns(3)
        
        # Graphique 1: Top 5 Stock (Valeur)
        with col_chart_1:
            st.subheader("Top 5 Stock (Valeur HT)")
            if not df_top_stock_value.empty:
                st.bar_chart(df_top_stock_value, x='nom', y='valeur_stock', height=300)
            else:
                st.info("Aucune donnée de stock à afficher.")
        
        # Graphique 2: Top 5 Ventes (Quantité)
        with col_chart_2:
            st.subheader("Top 5 Ventes (Quantité)")
            if not df_top_sales.empty:
                st.bar_chart(df_top_sales, x='nom', y='quantite_vendue', height=300, color="#FF5733")
            else:
                st.info("Aucune donnée de vente à afficher.")
        
        # Graphique 3: Répartition du Stock par Statut
        with col_chart_3:
            st.subheader("Statut des Stocks")
            if not df_status_count.empty:
                st.plotly_chart(
                    px.pie(df_status_count, values='Nombre', names='statut_stock', title='Répartition'),
                    use_container_width=True,
                    config={}
                )
            else:
                st.info("Aucune donnée de statut à afficher.")


    # ---------------- Scanner ----------------
    with scanner_tab:
        st.header("Scanner de Code-Barres par Webcam")
        st.info("Lancer le scan et attendre la détection d'un code-barres. Le code s'affichera ici et sera automatiquement utilisé dans l'onglet 'Vente (PoS)'.")
        
        col_info, col_scanner = st.columns([1, 2])
        
        with col_info:
            if st.session_state.get("last_barcode"):
                st.success(f"Code-barres détecté : **{st.session_state['last_barcode']}**")
                # Afficher le produit correspondant
                try:
                    df_p = query_df(text("""
                        SELECT p.nom 
                        FROM produits p
                        JOIN produits_barcodes pb ON p.id = pb.produit_id
                        WHERE pb.code = :code
                        LIMIT 1
                    """).bindparams(code=st.session_state['last_barcode']))
                    if not df_p.empty:
                        st.caption(f"Produit correspondant : **{df_p['nom'].iloc[0]}**")
                except:
                    st.caption("Code-barres non encore associé à un produit.")
            else:
                st.caption("Lancez la vidéo pour commencer la détection.")
        
        with col_scanner:
            # Configuration WebRTC
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
        st.header("Extraction automatique de produits depuis une facture")
        st.caption(
            "Téléversez une facture Metro (PDF, DOCX ou texte brut) pour extraire automatiquement les lignes produits, "
            "les corriger si nécessaire, puis importez-les dans le catalogue."
        )

        uploaded_invoice_files = st.file_uploader(
            "Déposer une facture Metro",
            type=["pdf", "docx", "txt"],
            key="extract_invoice_file_uploader",
            help="Les formats PDF, DOCX et TXT sont pris en charge.",
            accept_multiple_files=True,
        )

        _process_uploaded_invoices(uploaded_invoice_files, "Extraction")
        _render_invoice_selector("Facture chargée", "extract_invoice_selector")

        extract_invoice_text = st.text_area(
            "Texte de la facture à analyser",
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
                        st.success(
                            f"{len(df_extracted)} ligne(s) produit détectée(s). Vérifiez et corrigez-les ci-dessous."
                        )
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

        extracted_df = st.session_state.get("invoice_products_df")
        if isinstance(extracted_df, pd.DataFrame) and not extracted_df.empty:
            st.subheader("Produits détectés")
            st.caption(
                "Vérifiez les informations extraites. Vous pouvez ajuster les noms, les prix, la TVA ou les codes-barres avant "
                "l'importation."
            )

            editable_df = st.data_editor(
                extracted_df,
                key="extract_invoice_products_editor",
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "nom": st.column_config.TextColumn("Nom du produit"),
                    "prix_vente": st.column_config.NumberColumn("Prix de vente (€)", format="%.2f"),
                    "tva": st.column_config.NumberColumn("TVA (%)", format="%.2f"),
                    "qte_init": st.column_config.NumberColumn("Quantité", step=1, format="%.0f"),
                    "codes": st.column_config.TextColumn("Codes-barres"),
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
                        summary = products_loader.load_products_from_df(editable_df)
                    st.session_state["invoice_import_summary"] = summary
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

        summary = st.session_state.get("invoice_import_summary")
        if isinstance(summary, dict):
            st.divider()
            st.subheader("Résumé de l'importation")
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
        st.header("Importation de Produits par Fichier CSV")

        uploaded_invoice_files = st.file_uploader(
            "Déposer une facture Metro",
            type=["pdf", "docx", "txt"],
            key="import_invoice_file_uploader",
            help="Les formats PDF, DOCX et TXT sont pris en charge.",
            accept_multiple_files=True,
        )

        _process_uploaded_invoices(uploaded_invoice_files, "Import")
        _render_invoice_selector("Facture chargée", "import_invoice_selector")

        import_invoice_text = st.text_area(
            "Texte de la facture à analyser",
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
                        st.success(
                            f"{len(df_extracted)} ligne(s) produit détectée(s). Vérifiez et corrigez-les ci-dessous."
                        )
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

        extracted_df = st.session_state.get("invoice_products_df")
        if isinstance(extracted_df, pd.DataFrame) and not extracted_df.empty:
            st.subheader("Produits détectés")
            st.caption(
                "Vérifiez les informations extraites. Vous pouvez ajuster les noms, les prix, la TVA ou les codes-barres avant "
                "l'importation."
            )

            editable_df = st.data_editor(
                extracted_df,
                key="import_invoice_products_editor",
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "nom": st.column_config.TextColumn("Nom du produit"),
                    "prix_vente": st.column_config.NumberColumn("Prix de vente (€)", format="%.2f"),
                    "tva": st.column_config.NumberColumn("TVA (%)", format="%.2f"),
                    "qte_init": st.column_config.NumberColumn("Quantité", step=1, format="%.0f"),
                    "codes": st.column_config.TextColumn("Codes-barres"),
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
                        summary = products_loader.load_products_from_df(editable_df)
                    st.session_state["invoice_import_summary"] = summary
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

        summary = st.session_state.get("invoice_import_summary")
        if isinstance(summary, dict):
            st.divider()
            st.subheader("Résumé de l'importation")
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
        st.header("Importation de Produits")

        extraction_tab, csv_tab_inner = st.tabs([
            "Extraction facture METRO",
            "Import CSV classique",
        ])

        with extraction_tab:
            st.subheader("Extraction automatique depuis une facture fournisseur")
            st.caption(
                "Téléversez un PDF/DOCX de facture METRO ou collez le texte brut de la section produits."
            )

            uploaded_invoice = st.file_uploader(
                "Télécharger une facture (PDF, DOCX ou TXT)",
                type=["pdf", "docx", "txt"],
                key="invoice_uploader",
            )
            manual_invoice_text = st.text_area(
                "Ou collez directement le texte brut de la facture",
                height=160,
                key="invoice_text_area",
                placeholder="Collez ici le texte issu de la facture (copier/coller depuis le PDF).",
            )

            extracted_text = ""
            if uploaded_invoice is not None:
                with st.spinner("Extraction du texte en cours..."):
                    extracted_text = invoice_extractor.extract_text_from_file(uploaded_invoice)
                if not extracted_text:
                    st.warning("Aucun texte détecté dans le fichier téléversé.")
                elif extracted_text.lower().startswith("erreur"):
                    st.error(extracted_text)
                    extracted_text = ""

            raw_invoice_text = manual_invoice_text.strip() or extracted_text.strip()

            if raw_invoice_text:
                with st.expander("Prévisualiser le texte brut extrait", expanded=False):
                    st.text(raw_invoice_text)

                col_margin, col_tva, col_stock = st.columns([1, 1, 1])
                with col_margin:
                    apply_margin = st.checkbox(
                        "Appliquer une marge", value=True, key="invoice_apply_margin"
                    )
                    margin_pct = st.number_input(
                        "Marge (%)",
                        min_value=0.0,
                        max_value=500.0,
                        value=30.0,
                        step=1.0,
                        key="invoice_margin_pct",
                    )
                with col_tva:
                    default_tva = st.number_input(
                        "TVA par défaut (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=20.0,
                        step=0.5,
                        key="invoice_default_tva",
                    )
                    tva_code_d = st.number_input(
                        "TVA code D (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=20.0,
                        step=0.5,
                        key="invoice_tva_d",
                    )
                    tva_code_p = st.number_input(
                        "TVA code P (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=5.5,
                        step=0.5,
                        key="invoice_tva_p",
                    )
                with col_stock:
                    seuil_alerte = st.number_input(
                        "Seuil d'alerte (stock)",
                        min_value=0.0,
                        max_value=1_000_000.0,
                        value=0.0,
                        step=1.0,
                        key="invoice_stock_threshold",
                    )
                    arrondi_qty = st.selectbox(
                        "Arrondi des quantités",
                        options=["aucun", "entier"],
                        index=0,
                        key="invoice_qty_rounding",
                    )

                tva_mapping = {"D": tva_code_d, "P": tva_code_p}
                base_df = invoice_extractor.extract_products_from_metro_invoice(
                    raw_invoice_text,
                    tva_map=tva_mapping,
                    default_tva=default_tva,
                )

                if base_df.empty:
                    st.warning("Aucun produit n'a été identifié dans le texte fourni.")
                else:
                    df_ready = base_df.copy()
                    df_ready["nom"] = df_ready["nom"].fillna("").astype(str).str.strip()
                    df_ready = df_ready[df_ready["nom"] != ""].copy()

                    df_ready["codes"] = df_ready["codes"].fillna("").astype(str).str.strip()
                    df_ready["qte_init"] = df_ready["qte_init"].fillna(0).astype(float)
                    if arrondi_qty == "entier":
                        df_ready["qte_init"] = df_ready["qte_init"].round().astype(int)
                    df_ready["prix_achat"] = df_ready["prix_achat"].fillna(0.0).astype(float)
                    df_ready["tva"] = df_ready["tva"].fillna(default_tva).astype(float)

                    if apply_margin:
                        df_ready["prix_vente"] = (
                            df_ready["prix_achat"] * (1 + margin_pct / 100.0)
                        )
                    df_ready["prix_vente"] = df_ready["prix_vente"].fillna(
                        df_ready["prix_achat"]
                    )

                    df_ready["prix_achat"] = df_ready["prix_achat"].round(2)
                    df_ready["prix_vente"] = df_ready["prix_vente"].round(2)
                    df_ready["tva"] = df_ready["tva"].round(2)
                    df_ready["seuil_alerte_defaut"] = seuil_alerte
                    df_ready["prix_total_estime"] = (
                        df_ready["prix_vente"] * df_ready["qte_init"]
                    ).round(2)

                    total_lignes = len(df_ready)
                    total_qte = float(df_ready["qte_init"].sum())
                    total_valeur = float(df_ready["prix_total_estime"].sum())

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Produits détectés", total_lignes)
                    c2.metric("Quantité totale", f"{total_qte:,.0f}".replace(",", " "))
                    c3.metric("Valeur TTC estimée", f"{total_valeur:,.2f} €")

                    display_cols = [
                        "nom",
                        "codes",
                        "numero_article",
                        "qte_init",
                        "prix_achat",
                        "prix_vente",
                        "tva",
                        "tva_code",
                        "montant_total_facture",
                        "prix_total_estime",
                    ]
                    available_cols = [col for col in display_cols if col in df_ready.columns]
                    st.dataframe(
                        df_ready[available_cols],
                        use_container_width=True,
                        hide_index=True,
                    )

                    csv_data = df_ready.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        "Télécharger les données extraites (CSV)",
                        data=csv_data,
                        file_name="produits_facture_metro.csv",
                        mime="text/csv",
                        key="invoice_download_button",
                    )

                    if st.button(
                        "Importer ces produits dans l'inventaire",
                        type="primary",
                        key="invoice_import_button",
                    ):
                        with st.spinner("Importation des produits extraits..."):
                            results = products_loader.load_products_from_df(df_ready)

                        st.success("Importation terminée!")
                        st.caption(
                            f"Lignes traitées : {results['rows_processed']} / {results['rows_received']}"
                        )

                        product_summary = []
                        if results["created"]:
                            product_summary.append(f"{results['created']} créé(s)")
                        if results["updated"]:
                            product_summary.append(f"{results['updated']} mis à jour")
                        if product_summary:
                            st.info("Produits : " + ", ".join(product_summary))
                        else:
                            st.info("Produits : aucune modification apportée.")

                        if results["stock_initialized"]:
                            st.caption(
                                f"{results['stock_initialized']} mouvement(s) de stock initial enregistrés."
                            )

                        barcode_stats = results["barcode"]
                        if any(barcode_stats.values()):
                            st.caption(
                                "Codes-barres — "
                                f"ajouts: {barcode_stats['added']}, "
                                f"conflits: {barcode_stats['conflicts']}, "
                                f"ignorés/erreurs: {barcode_stats['skipped']}"
                            )

                        if results['errors']:
                            st.warning(
                                f"{len(results['errors'])} ligne(s) non importée(s) en raison d'erreurs."
                            )
                            errors_df = pd.DataFrame(results['errors'])
                            st.dataframe(errors_df, use_container_width=True, hide_index=True)
                        else:
                            st.success("Toutes les lignes valides ont été importées avec succès.")

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
                st.info("Téléchargez une facture ou collez le texte brut pour lancer l'extraction.")

        with csv_tab_inner:
            st.subheader("Importation de Produits par Fichier CSV")

            uploaded_file = st.file_uploader(
                "Télécharger un fichier CSV de produits (colonnes requises : nom, prix_vente, tva, qte_init, codes (Optionnel))",
                type=['csv'],
                key="csv_import_uploader",
            )

            expected_cols = ["nom", "prix_vente", "tva", "qte_init", "codes"]
            st.caption(f"Colonnes attendues (minimum): {', '.join(expected_cols)}")

            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file, sep=",")

                    missing_cols = [col for col in expected_cols if col not in df.columns]
                    if missing_cols:
                        st.warning(
                            f"Attention: Le fichier CSV manque les colonnes : {', '.join(missing_cols)}. Des valeurs par défaut seront utilisées."
                        )

                    st.write("Aperçu des données à importer:")
                    st.dataframe(df.head(), use_container_width=True)

                    if 'nom' not in df.columns:
                        st.error("Le fichier CSV doit contenir au moins la colonne 'nom'. Importation impossible.")
                    else:
                        if st.button("Lancer l'Importation des Produits", type="primary", key="csv_import_button"):
                            with st.spinner("Importation en cours..."):
                                cols_to_check = {
                                    "prix_vente": 0.0,
                                    "tva": 20.0,
                                    "qte_init": 0.0,
                                    "codes": "",
                                }
                                for col, default in cols_to_check.items():
                                    if col not in df.columns:
                                        df[col] = default

                                df['prix_vente'] = df['prix_vente'].apply(to_float, minv=0.0)
                                df['tva'] = df['tva'].apply(to_float, minv=0.0, maxv=100.0)
                                df['qte_init'] = df['qte_init'].apply(to_float, minv=0.0)
                                df['codes'] = df['codes'].fillna('').astype(str)

                                df.dropna(subset=['nom'], inplace=True)

                                results = products_loader.load_products_from_df(df)

                            st.success("Importation terminée!")
                            st.caption(
                                f"Lignes traitées : {results['rows_processed']} / {results['rows_received']}"
                            )

                            product_summary = []
                            if results["created"]:
                                product_summary.append(f"{results['created']} créé(s)")
                            if results["updated"]:
                                product_summary.append(f"{results['updated']} mis à jour")
                            if product_summary:
                                st.info("Produits : " + ", ".join(product_summary))
                            else:
                                st.info("Produits : aucune modification apportée.")

                            if results["stock_initialized"]:
                                st.caption(
                                    f"{results['stock_initialized']} mouvement(s) de stock initial enregistrés."
                                )

                            barcode_stats = results["barcode"]
                            if any(barcode_stats.values()):
                                st.caption(
                                    "Codes-barres — "
                                    f"ajouts: {barcode_stats['added']}, "
                                    f"conflits: {barcode_stats['conflicts']}, "
                                    f"ignorés/erreurs: {barcode_stats['skipped']}"
                                )

                            if results['errors']:
                                st.warning(
                                    f"{len(results['errors'])} ligne(s) non importée(s) en raison d'erreurs."
                                )
                                errors_df = pd.DataFrame(results['errors'])
                                st.dataframe(errors_df, use_container_width=True, hide_index=True)
                            else:
                                st.success("Toutes les lignes valides ont été importées avec succès.")

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
                    st.error(f"Une erreur est survenue lors de la lecture ou du traitement du fichier: {e}")
                    st.exception(e)


    # ---------------- Maintenance (Admin) ----------------
    with admin_tab:
        st.header("Maintenance et Outils Administrateur")
        
        # Contrôle d'accès par rôle
        if st.session_state["user_role"] == "admin":
            
            st.subheader("Vérification et Réparation BDD")

            if st.button("Tester la connexion BDD"):
                try:
                    df = query_df("SELECT NOW() as now")
                    st.success(f"Connexion OK — serveur répond: {df.loc[0,'now']}")
                except Exception as e:
                    st.error("Connexion échouée :")
                    st.exception(e)

            if st.button("Vider le Cache Streamlit"):
                st.cache_data.clear()
                st.toast("Cache vidé. Les données seront rechargées au prochain rafraîchissement.", icon='🧹')

            st.divider()
            st.subheader("Gestion des sauvegardes de la base de données")

            tool_statuses = check_backup_tools()
            missing_tools = [status for status in tool_statuses if not status.available]

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
                        f"- ❌ `{status.name}` introuvable avec la configuration actuelle "
                        f"(`{status.configured}` depuis {status.source})."
                    )

            st.markdown("\n".join(status_lines))

            if missing_tools:
                st.error(
                    "Installez le client PostgreSQL ou ajustez les variables d'environnement "
                    "pour activer la sauvegarde et la restauration."
                )
            else:
                st.success("Les utilitaires PostgreSQL requis sont disponibles.")

            def _trigger_rerun():
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()

            backup_directory = get_backup_directory()
            st.caption(
                "Les fichiers générés sont conservés dans le dossier suivant : "
                f"`{backup_directory.resolve()}`"
            )

            feedback = st.session_state.pop("admin_backup_feedback", None)
            if feedback:
                level, message = feedback
                display = getattr(st, level, st.info)
                display(message)

            st.text_input(
                "Étiquette optionnelle pour la prochaine sauvegarde",
                key="admin_backup_label",
                placeholder="ex: apres_inventaire",
                help="L'étiquette est ajoutée au nom du fichier pour faciliter l'identification.",
            )

            if st.button("Créer une sauvegarde maintenant", key="admin_backup_create"):
                label = st.session_state.get("admin_backup_label", "").strip()
                with st.spinner("Création de la sauvegarde en cours..."):
                    try:
                        metadata = create_backup(
                            label=label or None,
                            database_url=DATABASE_URL,
                        )
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

            backups = list_backups()
            if not backups:
                st.info("Aucune sauvegarde trouvée pour le moment.")
            else:
                st.warning(
                    "La restauration réinitialise la base avec le contenu du fichier sélectionné.",
                    icon="⚠️",
                )
                for index, backup in enumerate(backups):
                    row = st.container()
                    with row:
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
                                    restore_backup(
                                        backup.name,
                                        database_url=DATABASE_URL,
                                    )
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

            st.divider()
            st.subheader("Aperçu des Tables Brutes & Diagnostics")

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
        else:
            st.error("Accès refusé. Seuls les administrateurs peuvent accéder à l'onglet Maintenance (Admin).")


# ==============================================================================
# --- FIN DU FLUX PRINCIPAL (Contrôle d'accès) ---
# ==============================================================================

elif authentication_status is False:
    st.error('Nom d\'utilisateur/mot de passe incorrect.')
elif authentication_status is None:
    st.warning('Veuillez entrer votre nom d\'utilisateur et votre mot de passe.')

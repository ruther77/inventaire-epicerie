# app.py

import os
import io
import math
import re
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from functools import lru_cache
import streamlit_authenticator as stauth
import plotly.express as px
import invoice_extractor

# Imports pour le Scanner et la Vidéo
import cv2 
from pyzbar.pyzbar import decode
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode, RTCConfiguration

# Importation des fonctions de gestion de la BDD et du chargeur 
from data_repository import (
    query_df,
    exec_sql,
    exec_sql_return_id,
    get_engine,
    get_product_details,
    get_product_options,
)
from inventory_service import *
import products_loader

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

    sql = text(f"SELECT * FROM public.{table_name} ORDER BY id DESC LIMIT :limit")
    try:
        return query_df(sql, params={"limit": int(limit)})
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
            END), 0) AS stock_calcule,
            ROUND(p.stock_actuel - COALESCE(SUM(CASE
                WHEN m.type = 'ENTREE' THEN m.quantite
                WHEN m.type = 'SORTIE' THEN -m.quantite
                WHEN m.type = 'INVENTAIRE' THEN m.quantite
                WHEN m.type = 'TRANSFERT' THEN m.quantite
                ELSE 0
            END), 0), 3) AS ecart
        FROM produits p
        LEFT JOIN mouvements_stock m ON m.produit_id = p.id
        GROUP BY p.id, p.nom, p.stock_actuel
        HAVING ABS(p.stock_actuel - COALESCE(SUM(CASE
            WHEN m.type = 'ENTREE' THEN m.quantite
            WHEN m.type = 'SORTIE' THEN -m.quantite
            WHEN m.type = 'INVENTAIRE' THEN m.quantite
            WHEN m.type = 'TRANSFERT' THEN m.quantite
            ELSE 0
        END), 0)) > 0.001
        ORDER BY ABS(ecart) DESC, p.nom
    """

    try:
        return query_df(sql)
    except Exception as exc:
        st.error(f"Impossible de calculer le diagnostic stock/mouvements: {exc}")
        return pd.DataFrame(columns=["id", "nom", "stock_actuel", "stock_calcule", "ecart"])

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
        pos_tab,
        catalog_tab,
        mvt_tab,
        dash_tab,
        scanner_tab,
        extract_tab,
        import_tab,
        admin_tab,
    ) = st.tabs([
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


    # ---------------- Vente (PoS) ----------------
    with pos_tab:
        st.header("Terminal Point de Vente (PoS)")
        
        col_input, col_cart = st.columns([1, 2])
        
        with col_cart: 
            st.markdown('<div class="app-tile">', unsafe_allow_html=True)
            st.subheader("🛒 Panier Actuel")
            
            # 1. Vérifiez si le panier existe et n'est pas vide
            if 'cart' not in st.session_state:
                st.session_state.cart =  []
                st.info("Le panier est vide. Veuillez ajouter des produits.")
            else:
                # 2. Création d'un DataFrame pour l'affichage
                cart_df = pd.DataFrame(st.session_state.cart)
                
                # 3. Sécurisation des colonnes attendues et calcul du sous-total TTC et de la TVA par ligne
                for column, default in (("prix_vente", 0.0), ("tva", 0.0), ("qty", 0)):
                    if column not in cart_df.columns:
                        cart_df[column] = default

                cart_df['prix_total'] = cart_df['prix_vente'].fillna(0.0) * cart_df['qty'].fillna(0)
                cart_df['total_tva'] = cart_df['prix_total'] * (cart_df['tva'].fillna(0.0) / 100)
                
                # 4. Affichage du tableau
                st.dataframe(
                    cart_df[['nom', 'qty', 'prix_vente', 'prix_total']],
                    column_config={
                        "nom": "Produit",
                        "qty": "Quantité",
                        "prix_vente": st.column_config.NumberColumn("P.U. (€)", format="%.2f €"),
                        "prix_total": st.column_config.NumberColumn("Total Ligne (€)", format="%.2f €")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # 5. Calcul des totaux
                total_ttc = cart_df['prix_total'].sum()
                total_tva = cart_df['total_tva'].sum()
                total_ht = total_ttc - total_tva
                
                col_tva, col_ht, col_ttc = st.columns(3)
                
                col_ht.metric("Total HT", f"{total_ht:.2f} €")
                col_tva.metric("Total TVA", f"{total_tva:.2f} €")
                col_ttc.metric("Total TTC", f"{total_ttc:.2f} €", delta_color="off")
                
                # 6. Bouton pour Vider le Panier
                if st.button("Vider le Panier", help="Annule la transaction en cours.", key="clear_cart_btn"):
                    st.session_state.cart = []
                    st.rerun()
                
                # Bouton de Validation de Vente
                st.divider()
                if st.session_state.cart:
                    if st.button("Finaliser la Vente", key="btn_finalize_sale", type="primary"):
                        with st.spinner("Traitement de la vente en cours..."):
                            sale_ok, sale_msg = process_sale_transaction(
                                st.session_state.cart,
                                st.session_state.get("username", "inconnu"),
                            )

                        if sale_ok:
                            st.success("Vente finalisée et stock mis à jour ✅")
                            st.session_state.cart = []
                            load_products_list.clear()
                            cached_product_options.clear()
                            load_movement_timeseries.clear()
                            load_recent_movements.clear()
                            load_table_counts.clear()
                            load_table_preview.clear()
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

                        product_data = {
                            'id': int(product_row['id']),
                            'nom': product_row['nom'],
                            'prix_vente': float(product_row['prix_vente']),
                            'tva': float(product_row['tva']),
                            'qty': quantity 
                        }

                        found = False
                        for item in st.session_state.cart:
                            if item['id'] == product_id:
                                item['qty'] += quantity
                                found = True
                                break
                        
                        if not found:
                            st.session_state.cart.append(product_data)
                        
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
                            load_products_list.clear()
                            cached_product_options.clear()
                            load_movement_timeseries.clear()
                            load_recent_movements.clear()
                            load_table_counts.clear()
                            load_table_preview.clear()
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
                            load_products_list.clear()
                            cached_product_options.clear()
                            load_movement_timeseries.clear()
                            load_recent_movements.clear()
                            load_table_counts.clear()
                            load_table_preview.clear()
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
                            load_products_list.clear()
                            cached_product_options.clear()
                            load_table_preview.clear()
                            load_recent_movements.clear()
                            load_table_counts.clear()

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
                                load_products_list.clear()
                                cached_product_options.clear()
                                load_movement_timeseries.clear()
                                load_recent_movements.clear()
                                load_table_counts.clear()
                                load_table_preview.clear()
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

        uploaded_invoice_file = st.file_uploader(
            "Déposer une facture Metro",
            type=["pdf", "docx", "txt"],
            key="invoice_file_uploader",
            help="Les formats PDF, DOCX et TXT sont pris en charge.",
        )

        if uploaded_invoice_file is not None:
            raw_bytes = uploaded_invoice_file.getvalue()
            proxy_file = io.BytesIO(raw_bytes)
            proxy_file.name = uploaded_invoice_file.name
            proxy_file.type = uploaded_invoice_file.type
            try:
                extracted_text = invoice_extractor.extract_text_from_file(proxy_file)
            except Exception as exc:  # pragma: no cover - protection runtime Streamlit
                st.error(f"Erreur lors de la lecture du fichier : {exc}")
            else:
                if extracted_text is None or not str(extracted_text).strip():
                    st.warning("Le fichier a été chargé mais aucun texte exploitable n'a été détecté.")
                elif str(extracted_text).lower().startswith("erreur"):
                    st.error(extracted_text)
                else:
                    base_name, _ = os.path.splitext(uploaded_invoice_file.name)
                    safe_name = base_name or "facture"
                    st.session_state["invoice_raw_text"] = extracted_text
                    st.session_state["invoice_text_input"] = extracted_text
                    st.session_state["invoice_products_df"] = None
                    st.session_state["invoice_import_summary"] = None
                    st.session_state["invoice_uploaded_name"] = f"{safe_name}_extraction.txt"
                    st.success(f"Texte extrait depuis {uploaded_invoice_file.name}.")

        st.text_area(
            "Texte de la facture à analyser",
            key="invoice_text_input",
            height=260,
            placeholder="Collez ici la section produits de la facture si nécessaire...",
        )

        col_extract_btn, col_reset_btn = st.columns(2)
        with col_extract_btn:
            if st.button("Analyser le texte", key="invoice_extract_button", type="primary"):
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
            if st.button("Réinitialiser l'extraction", key="invoice_reset_button"):
                st.session_state["invoice_raw_text"] = ""
                st.session_state["invoice_text_input"] = ""
                st.session_state["invoice_products_df"] = None
                st.session_state["invoice_import_summary"] = None
                st.session_state["invoice_uploaded_name"] = "facture.txt"
                st.info("Extraction réinitialisée.")

        if st.session_state.get("invoice_raw_text"):
            st.download_button(
                "Télécharger le texte brut",
                data=st.session_state["invoice_raw_text"].encode("utf-8"),
                file_name=st.session_state.get("invoice_uploaded_name", "facture.txt"),
                mime="text/plain",
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
                key="invoice_products_editor",
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "nom": st.column_config.TextColumn("Nom du produit"),
                    "prix_vente": st.column_config.NumberColumn("Prix de vente (€)", format="%.2f"),
                    "tva": st.column_config.TextColumn("TVA (%)"),
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
                )
            with col_import:
                if st.button("Importer ces produits", key="invoice_import_button", type="primary"):
                    with st.spinner("Import des produits en cours..."):
                        summary = products_loader.load_products_from_df(editable_df)
                    st.session_state["invoice_import_summary"] = summary
                    load_products_list.clear()
                    cached_product_options.clear()
                    load_movement_timeseries.clear()
                    load_recent_movements.clear()
                    load_table_counts.clear()
                    load_table_preview.clear()
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

        uploaded_file = st.file_uploader(
            "Télécharger un fichier CSV de produits (colonnes requises : nom, prix_vente, tva, qte_init, codes (Optionnel))", 
            type=['csv']
        )
        
        # Définition des colonnes attendues
        expected_cols = ["nom", "prix_vente", "tva", "qte_init", "codes"]
        st.caption(f"Colonnes attendues (minimum): {', '.join(expected_cols)}")
        
        if uploaded_file:
            try:
                # Lecture du fichier CSV
                df = pd.read_csv(uploaded_file, sep=",")
                
                # Vérification des colonnes manquantes
                missing_cols = [col for col in expected_cols if col not in df.columns]
                if missing_cols:
                    st.warning(f"Attention: Le fichier CSV manque les colonnes : {', '.join(missing_cols)}. Des valeurs par défaut seront utilisées.")

                st.write("Aperçu des données à importer:")
                st.dataframe(df.head(), use_container_width=True)
                
                if 'nom' not in df.columns:
                    st.error("Le fichier CSV doit contenir au moins la colonne 'nom'. Importation impossible.")
                else:
                    if st.button("Lancer l'Importation des Produits", type="primary"):
                        with st.spinner("Importation en cours..."):
                            # Préparation du DataFrame pour l'import
                            cols_to_check = {
                                "prix_vente": 0.0,
                                "tva": 20.0,
                                "qte_init": 0.0, 
                                "codes": ""
                            }
                            for col, default in cols_to_check.items():
                                if col not in df.columns:
                                    df[col] = default
                            
                            # Application de la fonction to_float
                            df['prix_vente'] = df['prix_vente'].apply(to_float, minv=0.0)
                            df['tva'] = df['tva'].apply(to_float, minv=0.0, maxv=100.0)
                            df['qte_init'] = df['qte_init'].apply(to_float, minv=0.0)
                            df['codes'] = df['codes'].fillna('').astype(str)

                            # Filtrer les lignes vides
                            df.dropna(subset=['nom'], inplace=True)
                            
                            # Logique d'importation
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

                        # Afficher les erreurs d'importation
                        if results['errors']:
                            st.warning(f"{len(results['errors'])} ligne(s) non importée(s) en raison d'erreurs.")
                            errors_df = pd.DataFrame(results['errors'])
                            st.dataframe(errors_df, use_container_width=True, hide_index=True)
                        else:
                            st.success("Toutes les lignes valides ont été importées avec succès.")

                        load_products_list.clear()
                        cached_product_options.clear()
                        load_movement_timeseries.clear()
                        load_recent_movements.clear()
                        load_table_counts.clear()
                        load_table_preview.clear()
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

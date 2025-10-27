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

# Imports pour le Scanner et la Vidéo
import cv2 
from pyzbar.pyzbar import decode
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode, RTCConfiguration

# Importation des fonctions de gestion de la BDD et du chargeur 
from data_repository import query_df, exec_sql, exec_sql_return_id, get_engine, get_product_details
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
    
# --- Configuration de l'Authentification ---
SECRET_KEY = '__auth_token_inventaire_secure_2025' 

hashed_passwords = stauth.Hasher(['jemmysev', 'userpass']).generate()

credentials = {
    "usernames": {
        "admin": {
            "email": "ulrich@inventaire.fr",
            "name": "ulrich",
            "password": hashed_passwords[0], 
            "role": "admin"
        },
        "user": {
            "email": "user@inventaire.fr",
            "name": "user",
            "password": hashed_passwords[1], 
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
            v = max(v, maxv)
        return round(v, 4)
    except Exception:
        return default

@st.cache_data(ttl=3600)

# Placez cette fonction n'importe où en haut de votre script app.py,
# ou avant la fonction principale de la page Streamlit.

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
    all_products = get_product_options() # Fonction à utiliser pour obtenir tous les produits (nom, id)
    product_options = {p[0]: p[1] for p in all_products} # Créer le dictionnaire nom -> id
    
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

def load_products_list():
    sql_query = """
        SELECT
            p.id,
            p.nom,
            p.prix_vente,
            p.tva,
            p.stock_actuel AS quantite_stock,
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


def update_product_info_callback():
    selected_name = st.session_state.adj_product
    # Retrouver l'ID depuis le DataFrame ou la liste d'options si nécessaire
    # Dans votre cas, l'ID est déjà mis à jour directement via la liste d'options
    selected_id = st.session_state.product_options[selected_name] # Nécessite de stocker product_options
    
    product_details = get_product_details(selected_id)
    
    if product_details:
        st.session_state.ajust_produit_id = product_details['id']
        st.session_state.ajust_stock_actuel = float(product_details['quantite_stock'])
        st.session_state.ajust_nom = product_details['nom']
    else:
        st.session_state.ajust_produit_id = None
        st.session_state.ajust_stock_actuel = 0.00
        st.session_state.ajust_nom = "Produit Inconnu"
        
        
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

    st.title("📦 Inventaire — Gestion Complète")
    st.sidebar.caption(f'Bienvenue, **{name}** (Rôle: **{st.session_state["user_role"]}**)')
    authenticator.logout('Déconnexion', 'sidebar')

    # Définition des 7 onglets
    pos_tab, catalog_tab, mvt_tab, dash_tab, scanner_tab, import_tab, admin_tab = st.tabs([
        "Vente (PoS)", "Catalogue", "Stock & Mvt", "Dashboard", "Scanner", "Importation", "Maintenance (Admin)"
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
                
                # 3. Calcul du sous-total TTC et de la TVA par ligne
                cart_df['prix_total'] = cart_df['prix_vente'] * cart_df['qty']
                cart_df['total_tva'] = cart_df['prix_total'] * (cart_df['tva'] / 100)
                
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
                        st.success("Vente Finalisée (Logique de mouvements de stock à implémenter ici)!")
                        st.session_state.cart = []
                        st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_input:
            st.markdown('<div class="app-tile">', unsafe_allow_html=True) 
            
            st.subheader("🛒 Saisie Produit")

            # --- 1. CHARGEMENT DYNAMIQUE DES PRODUITS ---
            try:
                products_df = query_df("SELECT id, nom FROM produits ORDER BY nom")
                
                product_options = {row['nom']: row['id'] for index, row in products_df.iterrows()}
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
                                for code in codes_list:
                                    sql_code = text("INSERT INTO produits_barcodes (produit_id, code_barres) VALUES (:pid, :code) ON CONFLICT (code_barres) DO NOTHING")
                                    exec_sql(sql_code.bindparams(pid=product_id, code=code))

                            st.success(f"Produit '{new_nom}' ajouté avec succès!")
                            load_products_list.clear() 
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

        product_options = {row['nom']: row['id'] for index, row in df_products.iterrows()}
        product_names = list(product_options.keys())

        # --- Ajustement de stock pour les admins ---
        if st.session_state.get("user_role") == "admin":
            with st.form("stock_adjustment_form", clear_on_submit=True):
                st.subheader("Ajustement/Inventaire de Stock (Admin)")
                
                col_prod, col_qty = st.columns(2)
                selected_product_name = col_prod.selectbox("Produit à ajuster", product_names, key='adj_product',)
                selected_product_id = product_options.get(selected_product_name)
                
                product_details = get_product_details(selected_product_id)
                """
                if product_details:
                # 🚨 ÉTAPE CLÉ : STOCKER LES INFOS DANS LA SESSION STATE
                    st.session_state.ajust_produit_id = product_details['id']
                    st.session_state.ajust_stock_actuel = float(product_details['quantite_stock'])
                    st.session_state.ajust_nom = product_details['nom']

                    st.info(f"Produit trouvé: **{st.session_state.ajust_nom}**")
                    st.warning(f"Stock actuel: **{st.session_state.ajust_stock_actuel:.2f}**")
        
                else:
                    # S'il n'est pas trouvé, nettoyer la session pour éviter les erreurs
                    st.session_state.ajust_produit_id = None
                    st.error("Produit non trouvé.")
                
                #current_stock = df_products[df_products['id'] == selected_product_id]['quantite_stock'].iloc[0] if selected_product_id else 0
                #st.caption(f"Stock actuel: **{current_stock:.2f}**")
      """          
                # Affichage des informations de stock AVANT le number_input, en utilisant la session state
        # qui a été mise à jour par le callback `update_product_data`.
                if st.session_state.get('ajust_nom'):
                    st.info(f"Produit trouvé: **{st.session_state.ajust_nom}**")
                    st.warning(f"Stock actuel: **{st.session_state.ajust_stock_actuel:.2f}**")
                elif st.session_state.get('ajust_error'):
                    st.error(st.session_state.ajust_error)
                else:
                    st.info("Sélectionnez un produit pour afficher le stock actuel.")
                
                target_stock = col_qty.number_input(
                    "Nouvelle Quantité Totale (Inventaire)", 
                    min_value=0.00, 
                    value=st.session_state.get('ajust_stock_actuel',0.00), 
                    step=0.01, 
                    format="%.2f", 
                    key='adj_target_qty'
                )
                
                
                
                if st.form_submit_button("Enregistrer l'Ajustement", type="primary"):
                    # 🚨 CORRECTION : RÉCUPÉRATION DES VARIABLES DEPUIS LA SESSION STATE
                    produit_id = st.session_state.get('ajust_produit_id')
                    stock_actuel = st.session_state.get('ajust_stock_actuel', 0) # Utiliser 0 par défaut
                    nouvelle_quantite = st.session_state.adj_target_qty
                    quantite_mvt = nouvelle_quantite - stock_actuel
                    nom_produit = st.session_state.get('ajust_nom', "Produit Inconnu")
                    
                    if not produit_id:
                        st.error("Erreur: Le produit n'a pas été trouvé ou sélectionné. Veuillez réessayer.")
                        # Utiliser 'return' pour stopper l'exécution du reste de la boucle
                    elif abs(quantite_mvt) < 0.001:
                        st.warning(f"Le stock de **{nom_produit}** n'a pas changé. ({stock_actuel:.2f} -> {nouvelle_quantite:.2f}) Aucune action BDD requise.")
                    
                    else:
                    
    # Assurez-vous que nouvelle_quantite est également récupérée correctement du formulaire
                
                    # 1. Construction des paramètres du mouvement (DICTIONNAIRE)
                        # Déterminer le type de mouvement et la quantité (toujours positive)
                        if quantite_mvt > 0:
                            mouvement_type = 'ENTREE' # On ajoute du stock
                            quantite_a_enregistrer = quantite_mvt
                        else:
                            mouvement_type = 'SORTIE' # On retire du stock
                            quantite_a_enregistrer = abs(quantite_mvt) # On prend la valeur absolue (qui sera > 0)
                            
                        mouvement_params = {
                        'pid': produit_id, 
                        'type': mouvement_type, 
                    # La quantité est la différence entre le nouveau stock et l'ancien stock
                        'quantite': quantite_a_enregistrer, 
                        'source': f"Inventaire par {st.session_state['username']}"
                        }

                        sql_mvt = """
                    INSERT INTO mouvements_stock (produit_id, type, quantite, source)
                    VALUES (:pid, :type, :quantite, :source)
                    """

                        try:
                    # 2. Appel à exec_sql : ENCAPSULEZ le dictionnaire dans une LISTE
                    # Ceci force exec_sql à traiter l'entrée comme une liste de 1 élément
                            exec_sql(sql_mvt, [mouvement_params]) # <--- MODIFICATION CLÉ !
        
                            st.success(f"Ajustement réussi. Le stock de {st.session_state.ajust_nom} est maintenant à {nouvelle_quantite} unités.")
                        # Nettoyer l'état de la session si nécessaire
                            st.session_state.ajust_produit_id = None
                            st.session_state.ajust_stock_actuel = None
                            #st.session_state.adj_target_qty = 0.00
                            st.rerun()

                        except Exception as e:
                            st.error(f"Erreur lors de l'enregistrement de l'ajustement: {e}")
                else:
                    st.info("Aucun changement de stock détecté.")
        else:
            st.subheader("Historique des Mouvements Récents")
        
        st.divider()
        st.subheader("Historique Détaillé des Mouvements")
        
        try:
            df_mvt = query_df("""
                SELECT 
                    m.date_mvt, 
                    p.nom as produit, 
                    m.type, 
                    m.quantite, 
                    m.source as utilisateur
                FROM mouvements_stock m
                JOIN produits p ON m.produit_id = p.id
                ORDER BY m.date_mvt DESC
                LIMIT 100
            """)
            st.dataframe(df_mvt, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Impossible de charger l'historique des mouvements: {e}")


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
                        WHERE pb.code_barres = :code
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
                        st.caption(f"{results['success_count']} produits ajoutés/mis à jour.")

                        # Afficher les erreurs d'importation
                        if results['errors']:
                            st.warning(f"{len(results['errors'])} ligne(s) non importée(s) en raison d'erreurs.")
                            errors_df = pd.DataFrame(results['errors'])
                            st.dataframe(errors_df, use_container_width=True, hide_index=True)
                        else:
                            st.success("Toutes les lignes valides ont été importées avec succès.")
                        
                        load_products_list.clear()
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
            st.subheader("Aperçu des Tables Brutes")
            
            # Affichage des 3 tables principales
            for t in ["produits","produits_barcodes","mouvements_stock"]:
                try:
                    df = query_df(f"SELECT * FROM public.{t} LIMIT 20")
                    st.expander(f"Table '{t}' ({len(df)} lignes) - Clic pour voir les 20 premières", expanded=False).dataframe(df, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.warning(f"Impossible de lire la table {t}: {e}")
        else:
            st.error("Accès refusé. Seuls les administrateurs peuvent accéder à l'onglet Maintenance (Admin).")


# ==============================================================================
# --- FIN DU FLUX PRINCIPAL (Contrôle d'accès) ---
# ==============================================================================

elif authentication_status is False:
    st.error('Nom d\'utilisateur/mot de passe incorrect.')
elif authentication_status is None:
    st.warning('Veuillez entrer votre nom d\'utilisateur et votre mot de passe.')

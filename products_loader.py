import os
import sys
import re
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from data_repository import exec_sql

# --- Fonctions de BDD : helpers locaux utilisant SQLAlchemy et data_repository ---

def insert_or_update_barcode(conn: Connection, produit_id: int, barcode: str):
    """Insère un code-barres s'il n'existe pas, ou ne fait rien si le lien existe déjà."""
    # Le 'ON CONFLICT (code) DO NOTHING' est plus simple et sécuritaire pour cet usage
    sql = """
    INSERT INTO produits_barcodes (produit_id, code)
    VALUES (:pid, :code)
    ON CONFLICT (code) DO NOTHING; 
    """
    # Exécution simple car nous utilisons déjà une connexion (conn)
    conn.execute(text(sql), {"pid": produit_id, "code": barcode})

def get_engine():
    """Crée et retourne l'engine de connexion à la base de données."""
    # Utilise la variable d'environnement ou le défaut Docker Compose
    DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql+psycopg2://postgres:postgres@db:5432/epicerie"
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def exec_sql_return_id_with_conn(conn: Connection, sql: str, params=None):
    """Exécute une requête SQL et retourne l'ID (colonne 0) en utilisant une connexion ouverte."""
    result = conn.execute(text(sql), params)
    row = result.fetchone()
    return row[0] if row else None


# --- Fonctions Utilitaires ---
ALCOHOL_KEYWORDS = [
    "biere", "bière", "beer", "vin", "whisky", "rhum", "vodka",
    "liqueur", "champagne", "cidre", "tequila", "gin", "pastis",
    "cognac", "armagnac", "porto"
]

def determine_categorie(nom_produit):
    """Détermine la catégorie à partir du nom du produit."""
    nom = str(nom_produit).upper()
    if any(k in nom for k in ALCOHOL_KEYWORDS):
        return 'Alcool'
    if 'JUS' in nom or 'BOISSON' in nom or 'EAU' in nom or 'SODA' in nom:
        return 'Boissons'
    if 'HYGIENE' in nom or 'SAVON' in nom or 'SHAMPOOING' in nom:
        return 'Hygiene'
    if 'AFRIQUE' in nom or 'YASSA' in nom or 'TIÈB' in nom:
        return 'Afrique'
    return 'Autre'

def create_initial_stock(conn: Connection, produit_id: int, quantite: float):
    """Insère un mouvement de stock initial pour le produit."""
    if quantite > 0:
        sql = """
            INSERT INTO mouvements_stock (produit_id, type, quantite, source)
            VALUES (:produit_id, 'ENTREE', :quantite, 'Inventaire Initial');
        """
        conn.execute(text(sql), {"produit_id": produit_id, "quantite": quantite})


# --- Fonction Principale d'Importation ---
def process_products_file(csv_path: str) -> dict:
    
    total_created = 0
    total_updated = 0
    total_stocked = 0
    total_rows = 0
    errors = []
    
    try:
        # CORRECTION : Utilisation du séparateur virgule (',')
        df_produits = pd.read_csv(csv_path, sep=',', dtype=str, keep_default_na=False)
        total_rows = len(df_produits)
        
    except Exception as e:
        # Si ça échoue ici, il y a un problème de fichier ou de séparateur
        return {"total_rows": 0, "total_created": 0, "total_updated": 0, "errors": [f"ERREUR FATALE LECTURE CSV: {e}"]}

    # 2. Ouverture de la connexion et de la transaction
    eng = get_engine()
    with eng.begin() as conn: 
        
        # 3. Boucle d'itération et d'insertion
        for i, row in df_produits.iterrows():
            try:
                # --- Préparation des Données (avec gestion des colonnes manquantes) ---
                nom = str(row["nom"]).strip()
                # 💡 NOUVEAU : Lecture de la colonne 'codes' du CSV
                codes = str(row.get('codes', '')).strip()
                # S'assure que c'est une chaîne, même si elle est vide
        #codes = str(codes).strip() if codes is not None else ""
                # Valeurs par défaut pour les colonnes manquantes
                prix_achat = float(row.get("prix_achat", 0.0) or 0.0)
                seuil_alerte_defaut = float(row.get("seuil_alerte_defaut", 0) or 0)
                qte_init = float(row.get("quantite_initiale") or row.get("qte_init", 0.0) or 0.0)
                
                # Les colonnes obligatoires dans votre CSV
                prix_vente = float(row["prix_vente"])
                tva = float(row["tva"])
                categorie = determine_categorie(nom)

                # --- Insertion du Produit (Logique UPDATE/INSERT) ---
                
                # 1. Tenter la mise à jour (UPDATE) si le produit existe déjà
                update_result = conn.execute(
                    text("""
                        UPDATE produits SET 
                            prix_achat = :prix_achat, 
                            prix_vente = :prix_vente, 
                            tva = :tva, 
                            seuil_alerte = :seuil_alerte,
                            categorie = :categorie,
                            updated_at = now()
                        WHERE lower(nom) = lower(:nom)
                        RETURNING id
                    """),
                    {
                        "nom": nom, "prix_achat": prix_achat, "prix_vente": prix_vente, 
                        "tva": tva, "seuil_alerte": seuil_alerte_defaut, "categorie": categorie
                    }
                )
                
                updated_row = update_result.fetchone()
                
                if updated_row:
                    produit_id = updated_row[0]
                    total_updated += 1
                else:
                    # 2. Si aucune ligne mise à jour, effectuer l'insertion (INSERT)
                    insert_result = conn.execute(
                        text("""
                            INSERT INTO produits (nom, prix_achat, prix_vente, tva, seuil_alerte, categorie) 
                            VALUES (:nom, :prix_achat, :prix_vente, :tva, :seuil_alerte, :categorie)
                            RETURNING id
                        """),
                        {
                            "nom": nom, "prix_achat": prix_achat, "prix_vente": prix_vente, 
                            "tva": tva, "seuil_alerte": seuil_alerte_defaut, "categorie": categorie
                        }
                    )
                    
                    inserted_row = insert_result.fetchone()
                    if inserted_row:
                        produit_id = inserted_row[0]
                        total_created += 1
                    else:
                        # Si l'insertion échoue ici (très improbable), on lève une erreur.
                        raise Exception("Insertion ratée sans exception SQL détaillée.")
                # --- Insertion du Stock Initial ---
                if produit_id and qte_init > 0:
                    create_initial_stock(conn, produit_id, qte_init)
                    total_stocked += 1
                
                if produit_id and codes:  # Si on a un ID et que la chaîne 'codes' n'est pas vide
                    print(f"DEBUG: Tentative d'insertion du code {codes} pour le produit ID {produit_id}")  # Journalisation pour suivi des imports
                    insert_or_update_barcode(conn, produit_id, codes) 
                    total_codes_added += 1
                
            except Exception as e:
                # Si l'insertion SQL échoue (IntegrityError, UniqueViolation, etc.)
                errors.append({"ligne": i + 2, "nom": nom, "erreur": str(e)})

# 4. Retour des résultats
    return {
        "total_rows": total_rows, "total_created": total_created, "total_updated": total_updated, 
        "total_stocked": total_stocked, "total_codes_added": 0, "total_codes_skipped": 0,
        "total_codes_conflicts": 0, "errors": errors
    }

# --- Bloc d'Exécution Principal ---
if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'Produit.csv'
    results = process_products_file(csv_path)

    print("--- RÉSULTATS DE L'IMPORTATION ---")
    print(f"Total de lignes traitées : {results['total_rows']}")
    print(f"Produits créés : {results['total_created']}, Mis à jour : {results['total_updated']}")
    
    if results['errors']:
        print(f"\n🚨 {len(results['errors'])} ERREURS TROUVÉES lors de l'importation (Top 5):")
        for error in results['errors'][:5]:
            print(f"  Ligne {error['ligne']} ({error['nom']}): {error['erreur']}")
    else:
        print("✅ Aucune erreur d'importation trouvée. La base de données devrait être mise à jour.")

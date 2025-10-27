from __future__ import annotations

import sys
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import exc as sa_exc, text
from sqlalchemy.engine import Connection

from data_repository import get_engine

# --- Fonctions utilitaires BDD ---


def insert_or_update_barcode(conn: Connection, produit_id: int, barcode: str) -> str:
    """Insère un code-barres et renvoie le statut de l'opération."""

    sql = """
    INSERT INTO produits_barcodes (produit_id, code)
    VALUES (:pid, :code)
    ON CONFLICT (code) DO NOTHING;
    """

    result = conn.execute(text(sql), {"pid": produit_id, "code": barcode})
    if result.rowcount and result.rowcount > 0:
        return "added"
    return "conflict"


def exec_sql_return_id_with_conn(conn: Connection, sql: str, params=None):
    """Exécute une requête SQL et retourne l'ID (colonne 0) en utilisant une connexion ouverte."""

    result = conn.execute(text(sql), params)
    row = result.fetchone()
    return row[0] if row else None


# --- Fonctions Utilitaires ---

ALCOHOL_KEYWORDS = [
    "biere",
    "bière",
    "beer",
    "vin",
    "whisky",
    "rhum",
    "vodka",
    "liqueur",
    "champagne",
    "cidre",
    "tequila",
    "gin",
    "pastis",
    "cognac",
    "armagnac",
    "porto",
]


def determine_categorie(nom_produit):
    """Détermine la catégorie à partir du nom du produit."""

    nom = str(nom_produit).upper()
    if any(k in nom for k in ALCOHOL_KEYWORDS):
        return "Alcool"
    if "JUS" in nom or "BOISSON" in nom or "EAU" in nom or "SODA" in nom:
        return "Boissons"
    if "HYGIENE" in nom or "SAVON" in nom or "SHAMPOOING" in nom:
        return "Hygiene"
    if "AFRIQUE" in nom or "YASSA" in nom or "TIÈB" in nom:
        return "Afrique"
    return "Autre"


def create_initial_stock(conn: Connection, produit_id: int, quantite: float):
    """Insère un mouvement de stock initial pour le produit."""

    if quantite <= 0:
        return

    sql = """
        INSERT INTO mouvements_stock (produit_id, type, quantite, source)
        VALUES (:produit_id, 'ENTREE', :quantite, 'Inventaire Initial');
    """
    conn.execute(text(sql), {"produit_id": produit_id, "quantite": quantite})


# --- Normalisation des données importées ---


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_codes(raw_codes: Any) -> List[str]:
    if raw_codes is None:
        return []

    if isinstance(raw_codes, list):
        iterator = raw_codes
    else:
        iterator = str(raw_codes).replace("\n", " ").split(";")

    cleaned: List[str] = []
    for chunk in iterator:
        for item in str(chunk).split(","):
            code = item.strip()
            if code:
                cleaned.append(code)
    return cleaned


# --- Fonction principale utilisée par l'application ---


def load_products_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Charge les produits à partir d'un DataFrame et retourne un résumé détaillé."""

    summary: Dict[str, Any] = {
        "rows_received": int(len(df)),
        "rows_processed": 0,
        "created": 0,
        "updated": 0,
        "stock_initialized": 0,
        "barcode": {"added": 0, "conflicts": 0, "skipped": 0},
        "errors": [],
    }

    if df.empty:
        return summary

    eng = get_engine()
    with eng.begin() as conn:
        for idx, row in df.iterrows():
            summary["rows_processed"] += 1

            try:
                nom = str(row.get("nom", "")).strip()
                if not nom:
                    raise ValueError("Nom de produit manquant")

                prix_vente = _coerce_float(row.get("prix_vente"))
                if prix_vente <= 0:
                    raise ValueError("Prix de vente invalide")

                prix_achat = _coerce_float(row.get("prix_achat"))
                tva = _coerce_float(row.get("tva"), default=0.0)
                seuil = _coerce_float(row.get("seuil_alerte_defaut", row.get("seuil_alerte")))
                quantite_initiale = _coerce_float(
                    row.get("qte_init", row.get("quantite_initiale")), default=0.0
                )

                categorie = str(row.get("categorie", "")).strip() or determine_categorie(nom)
                codes_list = _clean_codes(row.get("codes"))

                params = {
                    "nom": nom,
                    "prix_achat": prix_achat,
                    "prix_vente": prix_vente,
                    "tva": tva,
                    "seuil_alerte": seuil,
                    "categorie": categorie,
                }

                update_result = conn.execute(
                    text(
                        """
                        UPDATE produits
                        SET prix_achat = :prix_achat,
                            prix_vente = :prix_vente,
                            tva = :tva,
                            seuil_alerte = :seuil_alerte,
                            categorie = :categorie,
                            updated_at = now()
                        WHERE lower(nom) = lower(:nom)
                        RETURNING id
                        """
                    ),
                    params,
                )

                result_row = update_result.fetchone()

                if result_row:
                    produit_id = result_row[0]
                    summary["updated"] += 1
                else:
                    insert_result = conn.execute(
                        text(
                            """
                            INSERT INTO produits (nom, prix_achat, prix_vente, tva, seuil_alerte, categorie)
                            VALUES (:nom, :prix_achat, :prix_vente, :tva, :seuil_alerte, :categorie)
                            RETURNING id
                            """
                        ),
                        params,
                    )

                    inserted_row = insert_result.fetchone()
                    if not inserted_row:
                        raise RuntimeError("Insertion produit sans identifiant retourné")
                    produit_id = inserted_row[0]
                    summary["created"] += 1

                if produit_id and quantite_initiale > 0:
                    create_initial_stock(conn, produit_id, quantite_initiale)
                    summary["stock_initialized"] += 1

                for code in codes_list:
                    try:
                        status = insert_or_update_barcode(conn, produit_id, code)
                        summary["barcode"][status] += 1
                    except sa_exc.IntegrityError:
                        summary["barcode"]["conflicts"] += 1
                    except Exception as code_error:  # noqa: BLE001 - logging manuel dans le résumé
                        summary["barcode"]["skipped"] += 1
                        raise code_error

            except Exception as exc:  # noqa: BLE001 - le but est de collecter toutes les erreurs
                summary["errors"].append(
                    {"ligne": idx + 2, "nom": row.get("nom", "?"), "erreur": str(exc)}
                )

    return summary


# --- Support CLI historique ---


def process_products_file(csv_path: str) -> Dict[str, Any]:
    try:
        df_produits = pd.read_csv(csv_path, sep=",", dtype=str, keep_default_na=False)
    except Exception as exc:
        return {
            "rows_received": 0,
            "rows_processed": 0,
            "created": 0,
            "updated": 0,
            "stock_initialized": 0,
            "barcode": {"added": 0, "conflicts": 0, "skipped": 0},
            "errors": [f"ERREUR FATALE LECTURE CSV: {exc}"],
        }

    return load_products_from_df(df_produits)


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "Produit.csv"
    results = process_products_file(csv_path)

    print("--- RÉSULTATS DE L'IMPORTATION ---")
    print(
        f"Total de lignes reçues : {results['rows_received']} | "
        f"Traitées : {results['rows_processed']}"
    )
    print(
        f"Produits créés : {results['created']} | "
        f"Mis à jour : {results['updated']}"
    )

    if results["errors"]:
        print(f"\n🚨 {len(results['errors'])} erreur(s) rencontrée(s) lors de l'import.")
        for error in results["errors"][:5]:
            print(f"  Ligne {error['ligne']} ({error['nom']}): {error['erreur']}")
    else:
        print("✅ Importation terminée sans erreur bloquante.")


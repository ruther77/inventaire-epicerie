from __future__ import annotations

import sys
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import exc as sa_exc, text
from sqlalchemy.engine import Connection

from data_repository import get_engine

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


def _empty_summary(rows_received: int = 0) -> Dict[str, Any]:
    return {
        "rows_received": rows_received,
        "rows_processed": 0,
        "created": 0,
        "updated": 0,
        "stock_initialized": 0,
        "barcode": {"added": 0, "conflicts": 0, "skipped": 0},
        "errors": [],
    }


def _to_float(value: Any, default: float | None = 0.0) -> float | None:
    if value is None:
        return default

    if isinstance(value, (int, float)):
        numeric = float(value)
        if math.isnan(numeric):
            return default
        return numeric

    if isinstance(value, str):
        cleaned = (
            value.replace("€", "")
            .replace("\xa0", "")
            .replace(",", ".")
            .strip()
        )
        if not cleaned:
            return default
        try:
            return float(cleaned)
        except ValueError:
            return default

    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def insert_or_update_barcode(conn: Connection, produit_id: int, barcode: str) -> str:
    """Insère un code-barres et renvoie *added*, *skipped* ou *conflict*."""

    normalized = str(barcode or "").strip()
    if not normalized:
        return "skipped"

    existing = conn.execute(
        text(
            """
            SELECT produit_id
            FROM produits_barcodes
            WHERE lower(code) = lower(:code)
            LIMIT 1
            """
        ),
        {"code": normalized},
    ).fetchone()

    if existing:
        return "skipped" if int(existing.produit_id) == int(produit_id) else "conflict"

    conn.execute(
        text(
            """
            INSERT INTO produits_barcodes (produit_id, code)
            VALUES (:pid, :code)
            """
        ),
        {"pid": produit_id, "code": normalized},
    )
    return "added"


def exec_sql_return_id_with_conn(conn: Connection, sql: str, params=None):
    """Exécute une requête SQL et retourne l'ID (colonne 0) en utilisant une connexion ouverte."""

    result = conn.execute(text(sql), params)
    row = result.fetchone()
    return row[0] if row else None


def determine_categorie(nom_produit: Any) -> str:
    """Détermine la catégorie à partir du nom du produit."""

    nom = str(nom_produit).upper()
    if any(k.upper() in nom for k in ALCOHOL_KEYWORDS):
        return "Alcool"
    if any(keyword in nom for keyword in ["JUS", "BOISSON", "EAU", "SODA"]):
        return "Boissons"
    if any(keyword in nom for keyword in ["HYGIENE", "SAVON", "SHAMPOOING"]):
        return "Hygiene"
    if any(keyword in nom for keyword in ["AFRIQUE", "YASSA", "TIÈB", "TIEB"]):
        return "Afrique"
    return "Autre"


def create_initial_stock(conn: Connection, produit_id: int, quantite: float) -> bool:
    """Insère un mouvement de stock initial pour le produit et indique s'il a été créé."""

    if quantite <= 0:
        return False

    sql = text(
        """
        INSERT INTO mouvements_stock (produit_id, type, quantite, source)
        VALUES (:produit_id, 'ENTREE', :quantite, 'Inventaire Initial')
        """
    )
    conn.execute(sql, {"produit_id": produit_id, "quantite": quantite})
    return True


def _clean_codes(raw_codes: Any) -> List[str]:
    if raw_codes is None:
        return []

    if isinstance(raw_codes, list):
        iterator = raw_codes
    else:
        iterator = str(raw_codes).replace("\n", " ").split(";")

    cleaned: List[str] = []
    for chunk in iterator:
        raw = str(chunk).replace(",", " ")
        for item in raw.split():
            code = item.strip()
            if code:
                cleaned.append(code)
    return cleaned


def load_products_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Charge les produits à partir d'un DataFrame et retourne un résumé détaillé."""

    summary = _empty_summary(rows_received=int(len(df)))

    if df.empty:
        return summary

    engine = get_engine()
    with engine.begin() as conn:
        for idx, row in df.iterrows():
            summary["rows_processed"] += 1
            nom = str(row.get("nom", "")).strip()

            try:
                if not nom:
                    raise ValueError("Nom du produit manquant")

                prix_vente = _to_float(row.get("prix_vente"), default=None)
                if prix_vente is None:
                    raise ValueError("Prix de vente manquant ou invalide")

                tva = _to_float(row.get("tva"), default=None)
                if tva is None:
                    raise ValueError("TVA manquante ou invalide")

                prix_achat = _to_float(row.get("prix_achat"), default=0.0) or 0.0
                seuil_alerte = _to_float(
                    row.get("seuil_alerte_defaut", row.get("seuil_alerte")),
                    default=0.0,
                ) or 0.0
                qte_init = _to_float(
                    row.get("quantite_initiale", row.get("qte_init")),
                    default=0.0,
                ) or 0.0
                codes_list = _clean_codes(row.get("codes"))
                categorie = determine_categorie(nom)

                params = {
                    "nom": nom,
                    "prix_achat": prix_achat,
                    "prix_vente": prix_vente,
                    "tva": tva,
                    "seuil_alerte": seuil_alerte,
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

                produit_row = update_result.fetchone()
                if produit_row:
                    produit_id = produit_row[0]
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
                    if inserted_row is None:
                        raise RuntimeError("Insertion du produit sans ID retourné")
                    produit_id = inserted_row[0]
                    summary["created"] += 1

                if create_initial_stock(conn, produit_id, qte_init):
                    summary["stock_initialized"] += 1

                for code in codes_list:
                    try:
                        status = insert_or_update_barcode(conn, produit_id, code)
                    except sa_exc.IntegrityError:
                        summary["barcode"]["conflicts"] += 1
                    except Exception:
                        summary["barcode"]["skipped"] += 1
                        raise
                    else:
                        if status == "added":
                            summary["barcode"]["added"] += 1
                        elif status == "conflict":
                            summary["barcode"]["conflicts"] += 1
                        else:
                            summary["barcode"]["skipped"] += 1

            except Exception as exc:
                summary["errors"].append(
                    {
                        "ligne": int(idx) + 2,  # 1-based index + header
                        "nom": nom or "<inconnu>",
                        "erreur": str(exc),
                    }
                )
    return summary


def process_products_file(csv_path: str) -> Dict[str, Any]:
    """Lit un fichier CSV puis délègue le traitement à :func:`load_products_from_df`."""

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        summary = _empty_summary()
        summary["errors"].append(
            {"ligne": 0, "nom": "", "erreur": f"Fichier introuvable: {csv_path}"}
        )
        return summary
    except Exception as exc:
        summary = _empty_summary()
        summary["errors"].append(
            {"ligne": 0, "nom": "", "erreur": str(exc)}
        )
        return summary

    return load_products_from_df(df)


if __name__ == "__main__":
    import sys

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


import os, sys, re
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/epicerie")

def norm_cols(df):
    cols_map = {
        "Nom":"nom", "nom":"nom",
        "Prix de vente":"prix_vente", "prix_vente":"prix_vente", "prix": "prix_vente",
        "TVA":"tva", "tva":"tva",
        "Code-barres":"codes", "codes":"codes", "code_barres":"codes", "barcode":"codes", "ean":"codes",
        "qte_init":"qte_init", "Quantité disponible":"qte_init", "stock_initial":"qte_init"
    }
    return df.rename(columns={c: cols_map.get(c,c) for c in df.columns})

def read_any(path):
    p = path.lower()
    if p.endswith(".csv"):
        try:
            return pd.read_csv(path)
        except Exception:
            # try semicolon CSV (common in FR locales)
            return pd.read_csv(path, sep=";")
    elif p.endswith(".xlsx") or p.endswith(".xls"):
        return pd.read_excel(path)
    else:
        raise SystemExit(f"Format non supporté: {path}")

def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python seed_products.py <csv|xlsx path>")

    path = sys.argv[1]
    print(f"Lecture: {path}")
    df = read_any(path)
    print("Colonnes détectées:", list(df.columns))
    df = norm_cols(df)

    if "nom" not in df.columns:
        raise SystemExit("La colonne 'Nom' est obligatoire (ou mappée en 'nom').")

    if "tva" not in df.columns: df["tva"] = 0.0
    if "prix_vente" not in df.columns: df["prix_vente"] = 0.0
    if "qte_init" not in df.columns: df["qte_init"] = 0.0

    eng = create_engine(DATABASE_URL, pool_pre_ping=True)
    created=updated=stocked=codes_added=0

    with eng.begin() as conn:
        for _, row in df.iterrows():
            nom = str(row["nom"]).strip()
            if not nom:
                continue
            tva = float(row.get("tva",0) or 0)
            pv  = float(row.get("prix_vente",0) or 0)
            qte = float(row.get("qte_init",0) or 0)

            r = conn.execute(text("SELECT id FROM produits WHERE LOWER(nom)=LOWER(:n)"), {"n": nom}).fetchone()
            if r:
                pid = r[0]
                conn.execute(text("UPDATE produits SET prix_vente=:pv, tva=:tva WHERE id=:id"),
                             {"pv": pv, "tva": tva, "id": pid})
                updated += 1
            else:
                r = conn.execute(text(\"\"\"\
                    INSERT INTO produits(nom, prix_vente, tva, actif) 
                    VALUES (:n, :pv, :tva, TRUE) RETURNING id
                \"\"\"), {"n": nom, "pv": pv, "tva": tva})
                pid = r.scalar()
                created += 1

            if qte and qte != 0:
                conn.execute(text(\"\"\"\
                    INSERT INTO mouvements_stock(produit_id, type, quantite, source) 
                    VALUES (:pid, 'ENTREE', :qte, 'SEED_INITIAL')
                \"\"\"), {"pid": pid, "qte": qte})
                stocked += 1

            codes = str(row.get("codes","")).strip()
            if codes and codes.lower() != "nan":
                parts = [c.strip() for c in re.split(r"[;,\\s]+", codes) if c.strip()]
                for code in parts:
                    try:
                        conn.execute(text(\"\"\"\
                            INSERT INTO produits_barcodes(produit_id, code) VALUES (:pid, :code)
                        \"\"\"), {"pid": pid, "code": code})
                        codes_added += 1
                    except Exception:
                        pass

    print(f\"Import terminé — créés: {created}, maj: {updated}, stocks: {stocked}, codes: {codes_added}\")

if __name__ == "__main__":
    main()

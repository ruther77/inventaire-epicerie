#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Charge des produits depuis un tableur Excel dans la BDD, avec codes-barres.
- Connexion via l'URL SQLAlchemy dans la variable d'environnement DATABASE_URL
- Tables: produits, mouvements_stock, produits_barcodes
- Idempotent sur 'nom' du produit et 'code' du code-barres (UNIQUE(code) en BDD)
- Colonne attendue pour codes: 'Code-barres' (peut contenir un code ou plusieurs séparés par virgule/point-virgule/espace)
"""
import os
import sys
import argparse
import re
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ALCOHOL_KEYWORDS = [
    "biere","bière","beer","vin","whisky","whiskey","rhum","rum","vodka",
    "liqueur","champagne","cidre","tequila","gin","pastis","sake","saké",
    "cognac","armagnac","porto","martini"
]

FOOD_HINTS = [
    "epicerie","épicerie","riz","pates","pâtes","farine","sucre","huile","lait",
    "yaourt","conserve","thon","sardine","maquereau","maquereaux","biscuit","biscuiterie",
    "chocolat","semoule","couscous","haricot","lentille","soupe","purée","sirop","céréale","cereale",
    "tomate","poulet","boeuf","boeuf","dinde","agneau","poisson","sauce","condiment","épice","epice",
    "eau"
]

BARCODE_SEP_RE = re.compile(r"[,\;\s]+")

def guess_tva(nom: str, categorie: str|None) -> float:
    name = (nom or "").lower()
    cat  = (categorie or "").lower()
    if "alcool" in cat or any(k in name for k in ALCOHOL_KEYWORDS):
        return 20.0
    if any(k in cat for k in ["epicerie","épicerie"]):
        return 5.5
    if "boisson" in cat:
        return 20.0 if any(k in name for k in ALCOHOL_KEYWORDS) else 5.5
    if any(k in name for k in FOOD_HINTS):
        return 5.5
    return 20.0

def normalize_barcode(val) -> list[str]:
    """
    Retourne une liste de codes propres (str de chiffres) à partir d'une cellule.
    Gère les numériques Excel (scientifiques), les multiples séparés par virgule/point-virgule/espace.
    Filtre à des longueurs plausibles (8,12,13,14) sans les forcer strictement.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)) or (isinstance(val, str) and not val.strip()):
        return []
    s = str(val).strip()
    # Si Excel a mis en exponentiel, tenter conversion
    try:
        if re.fullmatch(r"\d+(\.0+)?", s):
            s = str(int(float(s)))
    except Exception:
        pass
    # Split si multiples
    parts = BARCODE_SEP_RE.split(s)
    out = []
    for p in parts:
        p = re.sub(r"\D", "", p)  # garder que les chiffres
        if not p:
            continue
        if len(p) in (8,12,13,14):  # EAN-8, UPC-A(12), EAN-13, ITF-14
            out.append(p)
        else:
            # accepter quand même si longueur atypique, mais éviter les trucs très courts
            if len(p) >= 6:
                out.append(p)
    # dédupliquer en conservant l'ordre
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            uniq.append(x); seen.add(x)
    return uniq

def get_engine() -> Engine:
    dburl = os.getenv("DATABASE_URL")
    if not dburl:
        raise RuntimeError("DATABASE_URL n'est pas défini.")
    return create_engine(dburl, pool_pre_ping=True)

def upsert_produit(conn, nom: str, prix_vente: float|None, tva: float|None, actif: bool=True, prix_achat: float|None=None, seuil_alerte: float|None=None):
    row = conn.execute(text("SELECT id FROM produits WHERE lower(nom)=:n"), {"n": nom.lower()}).fetchone()
    if row:
        pid = row[0]
        conn.execute(text("""
            UPDATE produits
               SET prix_vente = COALESCE(:pv, prix_vente),
                   tva        = COALESCE(:tva, tva),
                   actif      = :actif
             WHERE id = :id
        """), {"pv": prix_vente, "tva": tva, "actif": actif, "id": pid})
        return pid, False
    else:
        res = conn.execute(text("""
            INSERT INTO produits (nom, prix_achat, prix_vente, tva, seuil_alerte, actif)
            VALUES (:nom, :pa, :pv, :tva, :seuil, :actif)
            RETURNING id
        """), {"nom": nom, "pa": prix_achat, "pv": prix_vente, "tva": tva, "seuil": seuil_alerte, "actif": actif})
        pid = res.scalar_one()
        return pid, True

def has_any_mvt(conn, produit_id: int) -> bool:
    r = conn.execute(text("SELECT 1 FROM mouvements_stock WHERE produit_id=:id LIMIT 1"), {"id": produit_id}).fetchone()
    return bool(r)

def create_initial_stock(conn, produit_id: int, quantite: float, source: str="Import Excel"):
    conn.execute(text("""
        INSERT INTO mouvements_stock (produit_id, type, quantite, source)
        VALUES (:pid, 'ENTREE', :qte, :src)
    """), {"pid": produit_id, "qte": quantite, "src": source})

def ensure_barcodes(conn, produit_id: int, codes: list[str]) -> tuple[int,int,int]:
    """
    Insère les codes si absents. Gère l'unicité sur 'code'.
    - premier code = is_principal=True si aucun principal existant.
    - si un code existe pour un autre produit, on le signale en conflit (skip).
    Retourne (added, skipped_existing_same_product, conflicts_other_product).
    """
    added = skipped = conflicts = 0

    # Y a-t-il déjà un principal ?
    r = conn.execute(text("SELECT 1 FROM produits_barcodes WHERE produit_id=:p AND is_principal"), {"p": produit_id}).fetchone()
    has_principal = bool(r)

    for idx, code in enumerate(codes):
        row = conn.execute(text("SELECT id, produit_id FROM produits_barcodes WHERE code=:c"), {"c": code}).fetchone()
        if row:
            # Existe déjà
            if row[1] == produit_id:
                skipped += 1
            else:
                conflicts += 1
            continue
        conn.execute(text("""
            INSERT INTO produits_barcodes (produit_id, code, symbologie, pays_iso2, is_principal)
            VALUES (:pid, :code, NULL, NULL, :princ)
        """), {
            "pid": produit_id,
            "code": code,
            "princ": (False if has_principal else (idx == 0))
        })
        if not has_principal and idx == 0:
            has_principal = True
        added += 1
    return added, skipped, conflicts

def main():
    p = argparse.ArgumentParser(description="Import de produits + codes-barres depuis Excel vers la BDD.")
    p.add_argument("excel_path", help="Chemin du tableur")
    p.add_argument("--sheet", help="Nom de feuille")
    p.add_argument("--dry-run", action="store_true", help="Prévisualisation sans écrire en BDD")
    p.add_argument("--prix-achat", type=float, help="Prix d'achat par défaut si inconnu")
    p.add_argument("--seuil-alerte", type=float, default=5, help="Seuil d'alerte stock par défaut")
    args = p.parse_args()

    df = pd.read_excel(args.excel_path, sheet_name=args.sheet) if args.sheet else pd.read_excel(args.excel_path)

    # Colonnes minimales
    required = ["Nom","Prix de vente"]
    for k in required:
        if k not in df.columns:
            raise RuntimeError(f"Colonne obligatoire manquante: '{k}'")
    # Facultatives
    qty_col = "Quantité disponible" if "Quantité disponible" in df.columns else None
    cat_col = "Catégorie de produits" if "Catégorie de produits" in df.columns else None
    bar_col = None
    for c in df.columns:
        if str(c).strip().lower() in ("code-barres","code barre","code-barre","barcode","ean","code ean","gtin"):
            bar_col = c; break

    plan_rows = []
    for _, r in df.iterrows():
        nom = str(r.get("Nom","")).strip()
        if not nom:
            continue

        pv  = r.get("Prix de vente", None)
        pv  = float(pv) if (pv is not None and pd.notna(pv)) else None

        qte = float(r.get(qty_col, 0) or 0) if qty_col else 0.0
        cat = r.get(cat_col) if cat_col else None
        tva = guess_tva(nom, cat if (cat is not None and pd.notna(cat)) else None)

        codes = []
        if bar_col is not None:
            codes = normalize_barcode(r.get(bar_col))

        plan_rows.append({
            "nom": nom,
            "prix_vente": pv,
            "tva_estimee": tva,
            "quantite_initiale": qte,
            "codes": codes
        })

    plan_df = pd.DataFrame([
        {"nom": x["nom"], "prix_vente": x["prix_vente"], "tva": x["tva_estimee"], "qte_init": x["quantite_initiale"], "codes": ", ".join(x["codes"])}
        for x in plan_rows
    ])

    if args.dry_run:
        print("=== APERÇU (25 premières lignes) ===")
        print(plan_df.head(25).to_string(index=False))
        print("\nTotal lignes prêtes:", len(plan_df))
        return

    engine = get_engine()
    total_created = total_updated = total_stocked = 0
    total_codes_added = total_codes_skipped = total_codes_conflicts = 0

    with engine.begin() as conn:
        for row in plan_rows:
            pid, is_new = upsert_produit(
                conn,
                nom=row["nom"],
                prix_vente=row["prix_vente"],
                tva=row["tva_estimee"],
                actif=True,
                prix_achat=args.prix_achat,
                seuil_alerte=args.seuil_alerte
            )
            if is_new: total_created += 1
            else:      total_updated += 1

            if row["quantite_initiale"] and row["quantite_initiale"] > 0:
                if not has_any_mvt(conn, pid):
                    create_initial_stock(conn, pid, row["quantite_initiale"])
                    total_stocked += 1

            if row["codes"]:
                a, s, c = ensure_barcodes(conn, pid, row["codes"])
                total_codes_added     += a
                total_codes_skipped   += s
                total_codes_conflicts += c

    print(f"Import terminé. Produits créés: {total_created}, mis à jour: {total_updated}, stocks initiaux ajoutés: {total_stocked}.")
    print(f"Codes-barres ajoutés: {total_codes_added}, déjà présents (même produit): {total_codes_skipped}, en conflit (autre produit): {total_codes_conflicts}.")

    out_csv = os.path.splitext(os.path.basename(args.excel_path))[0] + "_plan_import.csv"
    plan_df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"Plan d'import sauvegardé: {out_csv}")

if __name__ == "__main__":
    main()


import os
import io
import math
import re
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Inventaire Épicerie", layout="wide")
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql+psycopg2://postgres:postgres@db:5432/epicerie"

@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def query_df(sql, params=None):
    eng = get_engine()
    with eng.begin() as conn:
        return pd.read_sql(text(sql), conn, params=params)

def to_float(x, default=0.0, minv=None, maxv=None):
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

st.title("📦 Inventaire — Catalogue & Import")

catalog_tab, import_tab, admin_tab = st.tabs(["Catalogue", "Import", "Admin"])


# ---------------- Catalogue ----------------
with catalog_tab:
    st.subheader("Produits (vue rapide)")

    colf = st.columns([3,2,2,2,1])
    with colf[0]:
        q = st.text_input("Recherche (nom ou code-barres)", "")
    with colf[1]:
        sort = st.selectbox("Trier par", ["nom", "prix_vente", "tva", "id"], index=0)
    with colf[2]:
        page_size = st.selectbox("Taille page", [25, 50, 100, 200], index=1)
    with colf[3]:
        page = st.number_input("Page", min_value=1, value=1, step=1)
    with colf[4]:
        if st.button("⟳ Rafraîchir"):
            st.rerun()

    # WHERE + params
    base_where = "WHERE 1=1"
    params = {}
    if q:
        base_where += " AND (LOWER(p.nom) LIKE LOWER(:q) OR EXISTS (SELECT 1 FROM public.produits_barcodes b WHERE b.produit_id=p.id AND b.code ILIKE :q))"
        params["q"] = f"%{q}%"

    try:
        # Compteur total
        total = query_df(f"""
            SELECT COUNT(*) AS n
            FROM public.produits p
            {base_where}
        """, params).iloc[0]["n"]
        st.caption(f"Total : {int(total)} produit(s)")

        # Pagination robuste
        import math
        page_max = max(1, math.ceil(total / int(page_size))) if int(page_size) > 0 else 1
        if int(page) > page_max:
            st.info(f"Page {int(page)} > max {page_max}. Ajustez la pagination.")
        offset = (int(page) - 1) * int(page_size)

        # Requête simple (sans agrégat) + sous-requête pour codes (optionnel)
        df = query_df(f"""
            SELECT p.id, p.nom, p.prix_vente, p.tva,
                   COALESCE((
                       SELECT string_agg(DISTINCT b.code, ', ')
                       FROM public.produits_barcodes b
                       WHERE b.produit_id = p.id
                   ), '') AS codes
            FROM public.produits p
            {base_where}
            ORDER BY {sort} ASC
            LIMIT :limit OFFSET :offset
        """, {**params, "limit": int(page_size), "offset": int(offset)})

        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "prix_vente": st.column_config.NumberColumn("Prix (€)", format="%.2f"),
                "tva": st.column_config.NumberColumn("TVA (%)", format="%.2f"),
                "codes": st.column_config.TextColumn("Codes-barres"),
            }
        )

        if not df.empty:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Exporter la sélection (CSV)", data=csv,
                               file_name="produits_export.csv", mime="text/csv")
        else:
            if int(total) > 0:
                st.info("Aucune ligne sur cette page avec ces filtres. Essayez une autre page ou effacez la recherche.")
    except Exception as e:
        st.error("Impossible d'afficher le catalogue.")
        st.exception(e)
# ---------------- Import ----------------

with import_tab:
    st.subheader("Importer des produits (CSV ou Excel)")
    up = st.file_uploader("Déposez un fichier .csv ou .xlsx", type=["csv","xlsx"], accept_multiple_files=False)
    map_help = st.expander("Aide sur le mapping des colonnes")
    with map_help:
        st.markdown("""
- **Nom** → `nom` (obligatoire)
- **Prix de vente** → `prix_vente` (décimaux FR/€ acceptés)
- **TVA** → `tva` (optionnel, défaut 0)
- **Code-barres/EAN** → `codes` (séparés par virgule/point-virgule/espace)
- **qte_init / Quantité disponible / stock_initial** → `qte_init` (créera un mouvement **ENTREE**)
        """)
    if up:
        try:
            if up.name.lower().endswith(".csv"):
                try:
                    df = pd.read_csv(up)
                except Exception:
                    up.seek(0)
                    df = pd.read_csv(up, sep=";")
            else:
                df = pd.read_excel(up)
        except Exception as e:
            st.error(f"Erreur de lecture du fichier: {e}")
            df = None

        if df is not None:
            cols_map = {
                "Nom":"nom","nom":"nom",
                "Prix de vente":"prix_vente","prix_vente":"prix_vente","prix":"prix_vente",
                "TVA":"tva","tva":"tva",
                "Code-barres":"codes","codes":"codes","code_barres":"codes","barcode":"codes","ean":"codes",
                "qte_init":"qte_init","Quantité disponible":"qte_init","stock_initial":"qte_init"
            }
            df2 = df.rename(columns={c: cols_map.get(c,c) for c in df.columns})

            if "nom" not in df2.columns:
                st.error("Colonne obligatoire manquante : 'Nom'.")
                st.stop()

            if "tva" not in df2.columns: df2["tva"] = 0.0
            if "prix_vente" not in df2.columns: df2["prix_vente"] = 0.0
            if "qte_init" not in df2.columns: df2["qte_init"] = 0.0

            df2["tva"] = df2["tva"].map(lambda v: to_float(v, 0.0, minv=0.0, maxv=100.0))
            df2["prix_vente"] = df2["prix_vente"].map(lambda v: to_float(v, 0.0, minv=0.0))
            df2["qte_init"] = df2["qte_init"].map(lambda v: to_float(v, 0.0))

            eng = get_engine()
            created=updated=stocked=codes_added=0
            errors = []

            with eng.connect() as conn:
                for i, row in df2.iterrows():
                    nom = str(row["nom"]).strip() if pd.notna(row["nom"]) else ""
                    if not nom:
                        continue
                    tva = row["tva"]
                    pv  = row["prix_vente"]
                    qte = row["qte_init"]
                    codes_raw = str(row.get("codes","")).strip()

                    trans = conn.begin()
                    try:
                        r = conn.execute(text("SELECT id FROM public.produits WHERE LOWER(nom)=LOWER(:n)"), {"n": nom}).fetchone()
                        if r:
                            pid = r[0]
                            conn.execute(
                                text("UPDATE public.produits SET prix_vente=:pv, tva=:tva WHERE id=:id"),
                                {"pv": pv, "tva": tva, "id": pid}
                            )
                            updated += 1
                        else:
                            r = conn.execute(
                                text("""
                                    INSERT INTO public.produits(nom, prix_vente, tva, actif)
                                    VALUES (:n, :pv, :tva, TRUE)
                                    RETURNING id
                                """),
                                {"n": nom, "pv": pv, "tva": tva}
                            )
                            pid = r.scalar()
                            created += 1

                        if qte and qte != 0:
                            conn.execute(
                                text("""
                                    INSERT INTO public.mouvements_stock(produit_id, type, quantite, source)
                                    VALUES (:pid, 'ENTREE', :qte, 'IMPORT_INITIAL')
                                """),
                                {"pid": pid, "qte": qte}
                            )
                            stocked += 1

                        if codes_raw and codes_raw.lower() != "nan":
                            parts = [c.strip() for c in re.split(r"[;,\s]+", codes_raw) if c.strip()]
                            for code in parts:
                                conn.execute(
                                    text("""
                                        INSERT INTO public.produits_barcodes(produit_id, code)
                                        VALUES (:pid, :code)
                                        ON CONFLICT DO NOTHING
                                    """),
                                    {"pid": pid, "code": code}
                                )
                                codes_added += 1

                        trans.commit()
                    except Exception as e:
                        trans.rollback()
                        errors.append((i, nom, str(e)))

            msg = f"Import OK — créés: {created}, mis à jour: {updated}, stocks initiaux: {stocked}, codes-barres ajoutés: {codes_added}."
            if errors:
                st.warning(msg + f" ⚠️ {len(errors)} lignes ignorées (voir détails et export).")
                err_df = pd.DataFrame(errors, columns=["ligne", "nom", "erreur"])
                st.dataframe(err_df, use_container_width=True)
                st.download_button("⬇️ Télécharger erreurs (CSV)",
                                   err_df.to_csv(index=False).encode("utf-8"),
                                   file_name="import_erreurs.csv", mime="text/csv")
            else:
                st.success(msg)

            st.dataframe(df2.head(50))

# ---------------- Admin ----------------
with admin_tab:
    st.subheader("Maintenance")
    st.caption("DB URL utilisée : " + (os.getenv("DATABASE_URL") or "postgresql+psycopg2://postgres:postgres@db:5432/epicerie").replace("postgresql+psycopg2://","postgresql://").replace(":postgres@",":***@"))
    st.write("• Vérifier la connexion BDD")
    if st.button("Tester la connexion"):
        try:
            df = query_df("SELECT NOW() as now")
            st.success(f"Connexion OK — serveur répond: {df.loc[0,'now']}")
        except Exception as e:
            st.error("Connexion échouée :")
            st.exception(e)

    st.divider()
    st.write("• Aperçu des tables")
    for t in ["produits","produits_barcodes","mouvements_stock"]:
        try:
            df = query_df(f"SELECT * FROM public.{t} LIMIT 20")
            st.write(f"Table **{t}**")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.info(f"Table {t} indisponible : {e}")

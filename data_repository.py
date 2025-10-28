import os
import pandas as pd
from sqlalchemy import create_engine, text, TextClause
from sqlalchemy.engine import Engine
import streamlit as st 


from functools import lru_cache

# Utilisation d'une variable d'environnement ou d'une valeur par défaut
_DEFAULT_DB_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or f"postgresql+psycopg2://postgres:postgres@{_DEFAULT_DB_HOST}:5432/epicerie"
)

@st.cache_resource
def get_engine() -> Engine:
    """Retourne le moteur SQLAlchemy, mis en cache par Streamlit."""
    return create_engine(
        DATABASE_URL, 
        pool_pre_ping=True, 
        pool_size=10,        # Taille du pool de connexions (10 par défaut)
        max_overflow=20      # Permet 20 connexions temporaires en cas de pic
    )

def query_df(sql: str | TextClause, params=None) -> pd.DataFrame:
    """Exécute une requête SELECT et retourne le résultat sous forme de DataFrame Pandas."""
    statement = sql if isinstance(sql, TextClause) else text(sql)
    eng = get_engine()
    with eng.begin() as conn:
        return pd.read_sql(statement, conn, params=params)

# db_manager.py (Renommé : data_repository.py)
# ...

def exec_sql(sql: str | TextClause, params=None) -> None:
    """
    Exécute une requête d'écriture (INSERT, UPDATE, DELETE).
    Supporte l'exécution en lot si params est une liste.
    """
    statement = text(sql) if isinstance(sql, str) else sql
    eng = get_engine()
    with eng.begin() as conn:
        # Si params est une liste (exécution en lot), utilise executemany
        if isinstance(params, list):
            conn.execute(statement, params)
        elif params is None:
            conn.execute(statement)
        else:
            conn.execute(statement, params)

def exec_sql_return_id(sql: str | TextClause, params=None):
    """
    Exécute une requête et retourne l'ID (via RETURNING id). 
    Ne supporte pas l'exécution en lot (car une seule ID est retournée).
    """
    statement = text(sql) if isinstance(sql, str) else sql
    eng = get_engine()
    with eng.begin() as conn:
        # params doit être un dict ou None, non une liste pour l'insertion simple.
        result = conn.execute(statement, params) 
        row = result.fetchone()
        return row[0] if row else None


# ... (Vos fonctions existantes : get_engine, query_df, exec_sql, exec_sql_return_id) ...


def get_product_options() -> list[tuple[str, int]]:
    """Retourne la liste des produits actifs (nom, id) triés par nom."""
    sql = text(
        """
        SELECT nom, id
        FROM produits
        WHERE actif = TRUE
        ORDER BY nom
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql)
        return [(row.nom, row.id) for row in result]

def get_product_details(identifier: str | int) -> dict | None:
    """
    Recherche les détails d'un produit par son ID ou un de ses codes-barres.

    Args:
        identifier: ID du produit (int) ou code-barres (str).

    Returns:
        Un dictionnaire contenant les détails du produit (id, nom, stock_actuel)
        ou None si le produit n'est pas trouvé.
    """
    sql_query = """
    SELECT 
        p.id, 
        p.nom, 
        p.stock_actuel AS quantite_stock
    FROM 
        produits p
    LEFT JOIN 
        produits_barcodes pb ON p.id = pb.produit_id
    WHERE 
        p.actif = TRUE 
        -- Recherche par ID du produit (si l'identifiant est numérique)
        AND (
            p.id = :identifier_int 
            -- Recherche par code-barres (si l'identifiant est une chaîne de caractères)
            OR pb.code = :identifier_str
        )
    -- Limite à un seul résultat, même si un produit a plusieurs codes-barres
    LIMIT 1;
    """
    
    # 1. Préparation des paramètres
    params = {}
    identifier_str = str(identifier).strip()
    
    # Tente de convertir en entier pour la recherche par ID
    try:
        identifier_int = int(identifier_str)
        params['identifier_int'] = identifier_int
    except ValueError:
        # Si ce n'est pas un entier, l'ID ne peut pas être utilisé, on met None.
        params['identifier_int'] = None 
        
    # L'identifiant est toujours une chaîne pour la recherche par code-barres
    params['identifier_str'] = identifier_str
    
    # 2. Exécution de la requête
    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(text(sql_query), params)
        row = result.fetchone()
        
    # 3. Formatage du résultat
    if row:
        # Utiliser _asdict() si la ligne est un RowProxy (standard pour SQLAlchemy)
        return row._asdict()
    else:
        return None

import logging
import os

import pandas as pd
from sqlalchemy import create_engine, text, TextClause
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.engine import Engine
import streamlit as st

# Utilisation d'une variable d'environnement ou d'une valeur par défaut
_DEFAULT_DB_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or f"postgresql+psycopg2://postgres:postgres@{_DEFAULT_DB_HOST}:5432/epicerie"
)


logger = logging.getLogger(__name__)


def _get_pool_setting(env_var: str, default: int) -> int:
    value = os.getenv(env_var)
    if value in (None, ""):
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid integer for %s: %r. Falling back to default %d.",
            env_var,
            value,
            default,
        )
        return default

    if parsed < 0:
        logger.warning(
            "Negative value for %s: %r. Falling back to default %d.",
            env_var,
            value,
            default,
        )
        return default

    return parsed

@st.cache_resource
def get_engine() -> Engine:
    """Retourne le moteur SQLAlchemy, mis en cache par Streamlit."""
    pool_size = _get_pool_setting("SQLALCHEMY_POOL_SIZE", 10)
    max_overflow = _get_pool_setting("SQLALCHEMY_MAX_OVERFLOW", 20)

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )

def _normalize_statement(sql: str | ClauseElement) -> ClauseElement:
    if isinstance(sql, str):
        return text(sql)
    if isinstance(sql, ClauseElement):
        return sql
    raise TypeError("sql must be a string or SQLAlchemy ClauseElement")


def query_df(sql: str | ClauseElement, params=None) -> pd.DataFrame:
    """Exécute une requête SELECT et retourne le résultat sous forme de DataFrame Pandas."""
    statement = _normalize_statement(sql)
    if params is not None and not isinstance(params, dict):
        raise TypeError("params must be a mapping when provided")

    # Pré-lie les paramètres pour simplifier les tentatives de repli en cas d'erreur
    bound_statement = statement.bindparams(**params) if params is not None else statement

    eng = get_engine()
    with eng.begin() as conn:
        try:
            result = conn.execute(bound_statement)
        except TypeError as exc:
            # Certains drivers (ex: psycopg2 via pandas) peuvent exiger une chaîne brute.
            # Dans ce cas, on recompile la requête avec valeurs littérales pour utiliser exec_driver_sql.
            if isinstance(bound_statement, TextClause):
                compiled = bound_statement.compile(compile_kwargs={"literal_binds": True})
                sql_text = str(compiled)
                result = conn.exec_driver_sql(sql_text)
            else:
                raise exc

        columns = list(result.keys())
        rows = result.fetchall()

        if not rows:
            return pd.DataFrame(columns=columns)

        return pd.DataFrame([tuple(row) for row in rows], columns=columns)

# db_manager.py (Renommé : data_repository.py)
# ...

def exec_sql(sql: str | ClauseElement, params=None) -> None:
    """
    Exécute une requête d'écriture (INSERT, UPDATE, DELETE).
    Supporte l'exécution en lot si params est une liste.
    """
    statement = _normalize_statement(sql)
    eng = get_engine()
    with eng.begin() as conn:
        # Si params est une liste (exécution en lot), utilise executemany
        if isinstance(params, list):
            conn.execute(statement, params)
        elif params is None:
            conn.execute(statement)
        else:
            conn.execute(statement, params)

def exec_sql_return_id(sql: str | ClauseElement, params=None):
    """
    Exécute une requête et retourne l'ID (via RETURNING id). 
    Ne supporte pas l'exécution en lot (car une seule ID est retournée).
    """
    statement = _normalize_statement(sql)
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


# --- Gestion des utilisateurs -------------------------------------------------

_USER_PUBLIC_FIELDS = (
    "id",
    "username",
    "email",
    "full_name",
    "role",
    "is_active",
    "created_at",
    "updated_at",
)


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if hasattr(row, "_asdict"):
        return row._asdict()
    return dict(row)


def fetch_user_by_username(username: str) -> dict | None:
    sql = text(
        """
        SELECT id, username, email, full_name, role, hashed_password, is_active, created_at, updated_at
        FROM users
        WHERE LOWER(username) = LOWER(:username)
        LIMIT 1
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql, {"username": username})
        return _row_to_dict(result.fetchone())


def fetch_user_by_id(user_id: int) -> dict | None:
    sql = text(
        """
        SELECT id, username, email, full_name, role, hashed_password, is_active, created_at, updated_at
        FROM users
        WHERE id = :user_id
        LIMIT 1
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql, {"user_id": user_id})
        return _row_to_dict(result.fetchone())


def list_users() -> list[dict]:
    sql = text(
        """
        SELECT id, username, email, full_name, role, is_active, created_at, updated_at
        FROM users
        ORDER BY username ASC
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql)
        return [dict(row) for row in result.mappings().all()]


def create_user_record(data: dict) -> dict:
    sql = text(
        """
        INSERT INTO users (username, email, full_name, role, hashed_password, is_active)
        VALUES (:username, :email, :full_name, :role, :hashed_password, :is_active)
        RETURNING id, username, email, full_name, role, is_active, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, data)
        row = result.fetchone()
    return _row_to_dict(row) or {}


def update_user_record(user_id: int, updates: dict) -> dict | None:
    if not updates:
        existing = fetch_user_by_id(user_id)
        if existing is None:
            return None
        return {key: existing[key] for key in _USER_PUBLIC_FIELDS}

    allowed = {"username", "email", "full_name", "role", "hashed_password", "is_active"}
    filtered = {key: value for key, value in updates.items() if key in allowed}
    if not filtered:
        existing = fetch_user_by_id(user_id)
        if existing is None:
            return None
        return {key: existing[key] for key in _USER_PUBLIC_FIELDS}

    assignments: list[str] = []
    params = {"user_id": user_id}
    for index, (field, value) in enumerate(filtered.items()):
        param_name = f"value_{index}"
        assignments.append(f"{field} = :{param_name}")
        params[param_name] = value

    assignments.append("updated_at = now()")

    sql = text(
        f"""
        UPDATE users
        SET {', '.join(assignments)}
        WHERE id = :user_id
        RETURNING id, username, email, full_name, role, is_active, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, params)
        row = result.fetchone()
    return _row_to_dict(row)


def delete_user_record(user_id: int) -> bool:
    sql = text("DELETE FROM users WHERE id = :user_id")
    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, {"user_id": user_id})
        return result.rowcount > 0


def count_active_admins(exclude_user_id: int | None = None) -> int:
    base_sql = "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = TRUE"
    params: dict[str, int] = {}
    if exclude_user_id is not None:
        base_sql += " AND id <> :exclude_id"
        params["exclude_id"] = exclude_user_id

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(text(base_sql), params)
        scalar = result.scalar()  # type: ignore[assignment]
    return int(scalar or 0)

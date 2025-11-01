import logging
import os
from functools import lru_cache
from typing import Callable

import pandas as pd
from sqlalchemy import TextClause, create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.sql.elements import ClauseElement


DATABASE_URL_ENV = "DATABASE_URL"


logger = logging.getLogger(__name__)


_FALLBACK_DATABASE_URL = "sqlite+pysqlite:///:memory:"
_warned_missing_database_url = False


def _require_database_url() -> str:
    """Return the configured database URL or raise when it is missing."""

    url = os.getenv(DATABASE_URL_ENV)
    if url:
        return url

    raise RuntimeError(
        f"{DATABASE_URL_ENV} environment variable must be set. "
        "Use configure_engine(database_url=...) to inject a custom value when running tests."
    )


def _resolve_database_url() -> str:
    """Return the configured database URL or fall back to an in-memory SQLite database."""

    global _warned_missing_database_url  # noqa: PLW0603 - module level cache for warning

    url = os.getenv(DATABASE_URL_ENV)
    if url:
        return url

    if not _warned_missing_database_url:
        logger.warning(
            "%s is not set. Using fallback %s intended for local testing only.",
            DATABASE_URL_ENV,
            _FALLBACK_DATABASE_URL,
        )
        _warned_missing_database_url = True

    return _FALLBACK_DATABASE_URL


# Re-export the resolved URL for legacy callers (e.g. Streamlit dashboard).
# This mirrors the previous module level constant while keeping validation.
DATABASE_URL = _require_database_url()


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

_ENGINE_FACTORY: Callable[[], Engine] | None = None


def _build_engine(database_url: str) -> Engine:
    engine_kwargs: dict = {"pool_pre_ping": True}

    if database_url.startswith("sqlite"):
        return create_engine(database_url, **engine_kwargs)

    engine_kwargs["pool_size"] = _get_pool_setting("SQLALCHEMY_POOL_SIZE", 10)
    engine_kwargs["max_overflow"] = _get_pool_setting("SQLALCHEMY_MAX_OVERFLOW", 20)

    return create_engine(database_url, **engine_kwargs)


def _default_engine_factory() -> Engine:
    database_url = _resolve_database_url()
    return _build_engine(database_url)


def _resolve_engine_factory() -> Callable[[], Engine]:
    return _ENGINE_FACTORY or _default_engine_factory


@lru_cache(maxsize=1)
def _cached_engine() -> Engine:
    engine = _resolve_engine_factory()()
    if not isinstance(engine, Engine):
        raise TypeError("Engine factory must return a SQLAlchemy Engine instance.")
    return engine


def configure_engine(*, engine_factory: Callable[[], Engine] | None = None, database_url: str | None = None) -> None:
    """Allow applications to override the engine factory and keep a unified configuration."""

    global _ENGINE_FACTORY  # noqa: PLW0603 - runtime configuration hook
    global DATABASE_URL

    if engine_factory and database_url:
        raise ValueError("Provide either engine_factory or database_url, not both.")

    if database_url is not None:
        def _factory() -> Engine:
            return _build_engine(database_url)

        _ENGINE_FACTORY = _factory
        DATABASE_URL = database_url
    else:
        _ENGINE_FACTORY = engine_factory
        # When relying on environment variables, refresh the exported constant.
        # If the variable is missing we keep the previous (validated) value.
        try:
            DATABASE_URL = _require_database_url()
        except RuntimeError:
            logger.debug("DATABASE_URL environment variable missing when configuring custom engine factory.")

    _cached_engine.cache_clear()


def get_engine() -> Engine:
    """Retourne le moteur SQLAlchemy, mis en cache via un LRU interne."""

    return _cached_engine()

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


# --- Gestion des catégories ---------------------------------------------------


def list_categories() -> list[dict]:
    sql = text(
        """
        SELECT
            c.id,
            c.nom,
            c.description,
            c.created_at,
            c.updated_at,
            COUNT(p.id) AS produits_count
        FROM categories c
        LEFT JOIN produits p ON p.categorie = c.nom
        GROUP BY c.id, c.nom, c.description, c.created_at, c.updated_at
        ORDER BY c.nom ASC
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql)
        return [dict(row) for row in result.mappings().all()]


def fetch_category(category_id: int) -> dict | None:
    sql = text(
        """
        SELECT id, nom, description, created_at, updated_at
        FROM categories
        WHERE id = :category_id
        LIMIT 1
        """
    )
    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql, {"category_id": category_id})
        row = result.fetchone()
        return dict(row) if row else None


def create_category_record(payload: dict) -> dict:
    sql = text(
        """
        INSERT INTO categories (nom, description)
        VALUES (:nom, :description)
        RETURNING id, nom, description, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        row = conn.execute(sql, payload).mappings().one()
    return dict(row)


def update_category_record(category_id: int, payload: dict) -> dict | None:
    allowed = {"nom", "description"}
    filtered = {key: value for key, value in payload.items() if key in allowed and value is not None}

    if not filtered:
        return fetch_category(category_id)

    assignments = [f"{field} = :{field}" for field in filtered]
    filtered["category_id"] = category_id

    sql = text(
        f"""
        UPDATE categories
        SET {', '.join(assignments)}, updated_at = now()
        WHERE id = :category_id
        RETURNING id, nom, description, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, filtered)
        row = result.fetchone()
    return dict(row) if row else None


def delete_category_record(category_id: int) -> bool:
    sql = text("DELETE FROM categories WHERE id = :category_id")
    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, {"category_id": category_id})
        return result.rowcount > 0


# --- Gestion des clients ------------------------------------------------------


def list_clients() -> list[dict]:
    sql = text(
        """
        SELECT id, nom, telephone, email, adresse, created_at, updated_at
        FROM clients
        ORDER BY nom ASC
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql)
        return [dict(row) for row in result.mappings().all()]


def fetch_client(client_id: int) -> dict | None:
    sql = text(
        """
        SELECT id, nom, telephone, email, adresse, created_at, updated_at
        FROM clients
        WHERE id = :client_id
        LIMIT 1
        """
    )
    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql, {"client_id": client_id})
        row = result.fetchone()
        return dict(row) if row else None


def create_client_record(payload: dict) -> dict:
    sql = text(
        """
        INSERT INTO clients (nom, telephone, email, adresse)
        VALUES (:nom, :telephone, :email, :adresse)
        RETURNING id, nom, telephone, email, adresse, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        row = conn.execute(sql, payload).mappings().one()
    return dict(row)


def update_client_record(client_id: int, payload: dict) -> dict | None:
    allowed = {"nom", "telephone", "email", "adresse"}
    filtered = {key: value for key, value in payload.items() if key in allowed}

    if not filtered:
        return fetch_client(client_id)

    assignments = [f"{field} = :{field}" for field in filtered]
    filtered["client_id"] = client_id

    sql = text(
        f"""
        UPDATE clients
        SET {', '.join(assignments)}, updated_at = now()
        WHERE id = :client_id
        RETURNING id, nom, telephone, email, adresse, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, filtered)
        row = result.fetchone()
    return dict(row) if row else None


def delete_client_record(client_id: int) -> bool:
    sql = text("DELETE FROM clients WHERE id = :client_id")
    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, {"client_id": client_id})
        return result.rowcount > 0


# --- Gestion des fournisseurs -------------------------------------------------


def list_suppliers() -> list[dict]:
    sql = text(
        """
        SELECT id, nom, telephone, email, adresse, created_at, updated_at
        FROM fournisseurs
        ORDER BY nom ASC
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql)
        return [dict(row) for row in result.mappings().all()]


def fetch_supplier(supplier_id: int) -> dict | None:
    sql = text(
        """
        SELECT id, nom, telephone, email, adresse, created_at, updated_at
        FROM fournisseurs
        WHERE id = :supplier_id
        LIMIT 1
        """
    )
    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql, {"supplier_id": supplier_id})
        row = result.fetchone()
        return dict(row) if row else None


def create_supplier_record(payload: dict) -> dict:
    sql = text(
        """
        INSERT INTO fournisseurs (nom, telephone, email, adresse)
        VALUES (:nom, :telephone, :email, :adresse)
        RETURNING id, nom, telephone, email, adresse, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        row = conn.execute(sql, payload).mappings().one()
    return dict(row)


def update_supplier_record(supplier_id: int, payload: dict) -> dict | None:
    allowed = {"nom", "telephone", "email", "adresse"}
    filtered = {key: value for key, value in payload.items() if key in allowed}

    if not filtered:
        return fetch_supplier(supplier_id)

    assignments = [f"{field} = :{field}" for field in filtered]
    filtered["supplier_id"] = supplier_id

    sql = text(
        f"""
        UPDATE fournisseurs
        SET {', '.join(assignments)}, updated_at = now()
        WHERE id = :supplier_id
        RETURNING id, nom, telephone, email, adresse, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, filtered)
        row = result.fetchone()
    return dict(row) if row else None


def delete_supplier_record(supplier_id: int) -> bool:
    sql = text("DELETE FROM fournisseurs WHERE id = :supplier_id")
    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, {"supplier_id": supplier_id})
        return result.rowcount > 0


# --- Gestion des commandes ----------------------------------------------------


def list_orders() -> list[dict]:
    sql = text(
        """
        SELECT
            o.id,
            o.numero,
            o.date_commande,
            o.client_id,
            o.statut,
            o.total_ht,
            o.total_ttc,
            o.created_at,
            o.updated_at,
            c.nom AS client_nom,
            COUNT(l.id) AS lignes_count
        FROM commandes o
        LEFT JOIN clients c ON c.id = o.client_id
        LEFT JOIN commandes_lignes l ON l.commande_id = o.id
        GROUP BY o.id, c.nom
        ORDER BY o.date_commande DESC, o.id DESC
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql)
        return [dict(row) for row in result.mappings().all()]


def create_order_record(order_payload: dict, line_items: list[dict]) -> dict:
    sql = text(
        """
        INSERT INTO commandes (numero, date_commande, client_id, statut, total_ht, total_ttc)
        VALUES (:numero, :date_commande, :client_id, :statut, :total_ht, :total_ttc)
        RETURNING id, numero, date_commande, client_id, statut, total_ht, total_ttc, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        order_row = conn.execute(sql, order_payload).mappings().one()

        if line_items:
            payload = [
                {
                    "commande_id": order_row["id"],
                    "produit_id": item.get("produit_id"),
                    "quantite": item.get("quantite"),
                    "prix_unitaire": item.get("prix_unitaire"),
                    "tva": item.get("tva", 0),
                }
                for item in line_items
            ]
            conn.execute(
                text(
                    """
                    INSERT INTO commandes_lignes (commande_id, produit_id, quantite, prix_unitaire, tva)
                    VALUES (:commande_id, :produit_id, :quantite, :prix_unitaire, :tva)
                    """
                ),
                payload,
            )

    return dict(order_row)


def update_order_record(order_id: int, updates: dict) -> dict | None:
    allowed = {"statut", "client_id", "date_commande"}
    filtered = {key: value for key, value in updates.items() if key in allowed}

    if not filtered:
        sql_fetch = text(
            """
            SELECT id, numero, date_commande, client_id, statut, total_ht, total_ttc, created_at, updated_at
            FROM commandes
            WHERE id = :order_id
            LIMIT 1
            """
        )
        eng = get_engine()
        with eng.connect() as conn:
            row = conn.execute(sql_fetch, {"order_id": order_id}).fetchone()
            return dict(row) if row else None

    assignments = [f"{field} = :{field}" for field in filtered]
    filtered["order_id"] = order_id

    sql = text(
        f"""
        UPDATE commandes
        SET {', '.join(assignments)}, updated_at = now()
        WHERE id = :order_id
        RETURNING id, numero, date_commande, client_id, statut, total_ht, total_ttc, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, filtered)
        row = result.fetchone()
    return dict(row) if row else None


# --- Gestion des approvisionnements ------------------------------------------


def list_procurements() -> list[dict]:
    sql = text(
        """
        SELECT
            a.id,
            a.numero,
            a.date_appro,
            a.fournisseur_id,
            a.statut,
            a.total_ht,
            a.created_at,
            a.updated_at,
            f.nom AS fournisseur_nom,
            COUNT(l.id) AS lignes_count
        FROM approvisionnements a
        LEFT JOIN fournisseurs f ON f.id = a.fournisseur_id
        LEFT JOIN approvisionnements_lignes l ON l.approvisionnement_id = a.id
        GROUP BY a.id, f.nom
        ORDER BY a.date_appro DESC, a.id DESC
        """
    )

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.execute(sql)
        return [dict(row) for row in result.mappings().all()]


def create_procurement_record(procurement_payload: dict, line_items: list[dict]) -> dict:
    sql = text(
        """
        INSERT INTO approvisionnements (numero, date_appro, fournisseur_id, statut, total_ht)
        VALUES (:numero, :date_appro, :fournisseur_id, :statut, :total_ht)
        RETURNING id, numero, date_appro, fournisseur_id, statut, total_ht, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        row = conn.execute(sql, procurement_payload).mappings().one()

        if line_items:
            payload = [
                {
                    "approvisionnement_id": row["id"],
                    "produit_id": item.get("produit_id"),
                    "quantite": item.get("quantite"),
                    "prix_unitaire": item.get("prix_unitaire"),
                }
                for item in line_items
            ]
            conn.execute(
                text(
                    """
                    INSERT INTO approvisionnements_lignes (approvisionnement_id, produit_id, quantite, prix_unitaire)
                    VALUES (:approvisionnement_id, :produit_id, :quantite, :prix_unitaire)
                    """
                ),
                payload,
            )

    return dict(row)


def update_procurement_record(procurement_id: int, updates: dict) -> dict | None:
    allowed = {"statut", "fournisseur_id", "date_appro"}
    filtered = {key: value for key, value in updates.items() if key in allowed}

    if not filtered:
        sql_fetch = text(
            """
            SELECT id, numero, date_appro, fournisseur_id, statut, total_ht, created_at, updated_at
            FROM approvisionnements
            WHERE id = :procurement_id
            LIMIT 1
            """
        )
        eng = get_engine()
        with eng.connect() as conn:
            row = conn.execute(sql_fetch, {"procurement_id": procurement_id}).fetchone()
            return dict(row) if row else None

    assignments = [f"{field} = :{field}" for field in filtered]
    filtered["procurement_id"] = procurement_id

    sql = text(
        f"""
        UPDATE approvisionnements
        SET {', '.join(assignments)}, updated_at = now()
        WHERE id = :procurement_id
        RETURNING id, numero, date_appro, fournisseur_id, statut, total_ht, created_at, updated_at
        """
    )

    eng = get_engine()
    with eng.begin() as conn:
        result = conn.execute(sql, filtered)
        row = result.fetchone()
    return dict(row) if row else None

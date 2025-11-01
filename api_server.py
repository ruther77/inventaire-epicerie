"""API publique légère pour interagir avec l'inventaire."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Sequence

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy import exc as sa_exc

from data_repository import get_engine, query_df

load_dotenv()


class MovementType(str, Enum):
    """Types de mouvements autorisés dans l'application."""

    ENTREE = "ENTREE"
    SORTIE = "SORTIE"
    TRANSFERT = "TRANSFERT"
    INVENTAIRE = "INVENTAIRE"


class StockUpdate(BaseModel):
    """Payload minimal pour enregistrer un mouvement de stock."""

    product_id: int = Field(gt=0, description="Identifiant du produit concerné")
    quantity: float = Field(gt=0, description="Quantité de l'entrée ou sortie")
    type: MovementType = Field(description="Type de mouvement")
    source: str | None = Field(
        default="External API",
        description="Libellé libre pour identifier la source du mouvement",
        max_length=200,
    )


class BulkStockUpdate(BaseModel):
    """Requête permettant d'enregistrer plusieurs mouvements d'un coup."""

    updates: Sequence[StockUpdate] = Field(
        ..., min_length=1, max_length=500, description="Liste des mouvements à enregistrer"
    )


class ProductSummary(BaseModel):
    id: int
    nom: str
    categorie: str | None = None
    prix_vente: float | None = None
    tva: float | None = None
    stock_actuel: float | None = Field(default=None, description="Stock actuel en unité")
    actif: bool | None = None


class ProductDetail(ProductSummary):
    prix_achat: float | None = None
    seuil_alerte: float | None = None
    barcodes: list[str] = Field(default_factory=list)
    dernier_mouvement: datetime | None = None
    mouvements_total: int = 0


class StockMovement(BaseModel):
    id: int
    produit_id: int
    type: MovementType
    quantite: float
    source: str | None = None
    date_mvt: datetime | None = None


class StockUpdateResult(BaseModel):
    movement_id: int
    product_id: int
    type: MovementType
    quantity: float
    source: str | None = None
    date: datetime | None = None


class BulkUpdateResponse(BaseModel):
    accepted: int
    results: list[StockUpdateResult]
    errors: list[str] = Field(default_factory=list)


app = FastAPI(title="Inventaire API", version="1.0.0")


INSERT_MOVEMENT_WITH_RETURNING = text(
    """
    INSERT INTO mouvements_stock (produit_id, type, quantite, source)
    VALUES (:pid, :mvt_type, :qty, :src)
    RETURNING id, produit_id, type, quantite, source, date_mvt
    """
)

INSERT_MOVEMENT = text(
    """
    INSERT INTO mouvements_stock (produit_id, type, quantite, source)
    VALUES (:pid, :mvt_type, :qty, :src)
    """
)

FETCH_MOVEMENT_BY_ID = text(
    """
    SELECT id, produit_id, type, quantite, source, date_mvt
    FROM mouvements_stock
    WHERE id = :mid
    """
)

FETCH_LAST_MOVEMENT_SQLITE = text(
    """
    SELECT id, produit_id, type, quantite, source, date_mvt
    FROM mouvements_stock
    WHERE rowid = last_insert_rowid()
    """
)


def _normalize_source(source: str | None) -> str:
    cleaned = (source or "").strip()
    return cleaned or "External API"


def _fetch_product_basic(product_id: int) -> ProductDetail | None:
    sql = text(
        """
        SELECT id, nom, categorie, prix_vente, prix_achat, tva, stock_actuel,
               seuil_alerte, actif
        FROM produits
        WHERE id = :pid
        """
    )
    df = query_df(sql, {"pid": product_id})
    if df.empty:
        return None

    record = df.to_dict("records")[0]

    barcodes_df = query_df(
        text(
            """
            SELECT code
            FROM produits_barcodes
            WHERE produit_id = :pid
            ORDER BY code ASC
            """
        ),
        {"pid": product_id},
    )
    barcodes = [str(row["code"]) for row in barcodes_df.to_dict("records")] if not barcodes_df.empty else []

    stats_df = query_df(
        text(
            """
            SELECT MAX(date_mvt) AS dernier_mouvement, COUNT(*) AS mouvements_total
            FROM mouvements_stock
            WHERE produit_id = :pid
            """
        ),
        {"pid": product_id},
    )
    dernier_mvt = None
    total = 0
    if not stats_df.empty:
        stats = stats_df.to_dict("records")[0]
        dernier_mvt = stats.get("dernier_mouvement")
        total = int(stats.get("mouvements_total") or 0)

    payload = {
        **record,
        "barcodes": barcodes,
        "dernier_mouvement": dernier_mvt,
        "mouvements_total": total,
    }

    return ProductDetail.model_validate(payload)


def _insert_stock_movement(update: StockUpdate) -> StockUpdateResult:
    engine = get_engine()
    params = {
        "pid": int(update.product_id),
        "mvt_type": update.type.value,
        "qty": float(update.quantity),
        "src": _normalize_source(update.source),
    }

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM produits WHERE id = :pid"), {"pid": params["pid"]}
        ).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="Produit introuvable.")

        row = None
        movement_id: int | None = None
        try:
            result = conn.execute(INSERT_MOVEMENT_WITH_RETURNING, params)
            mapping = result.mappings().first()
            if mapping:
                row = mapping
                raw_id = mapping.get("id")
                if raw_id is not None:
                    movement_id = int(raw_id)
        except sa_exc.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except sa_exc.DBAPIError as exc:
            message = str(getattr(exc, "orig", exc)).upper()
            if "RETURNING" in message and conn.dialect.name == "sqlite":
                conn.execute(INSERT_MOVEMENT, params)
                row = conn.execute(FETCH_LAST_MOVEMENT_SQLITE).mappings().first()
            else:
                raise

        if row is None:
            if conn.dialect.name == "sqlite":
                row = conn.execute(FETCH_LAST_MOVEMENT_SQLITE).mappings().first()
            elif movement_id is not None:
                row = conn.execute(FETCH_MOVEMENT_BY_ID, {"mid": movement_id}).mappings().first()

        if not row:
            raise HTTPException(status_code=500, detail="Impossible de récupérer le mouvement créé.")

        row_map = dict(row)

        return StockUpdateResult(
            movement_id=int(row_map["id"]),
            product_id=int(row_map["produit_id"]),
            type=MovementType(row_map["type"]),
            quantity=float(row_map["quantite"]),
            source=row_map.get("source"),
            date=row_map.get("date_mvt"),
        )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Simple vérification de santé incluant la base de données."""

    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - remontée explicite
        raise HTTPException(status_code=503, detail=f"Base de données indisponible: {exc}") from exc
    return {"status": "ok"}


@app.get("/products", response_model=list[ProductSummary])
def list_products(
    query: str | None = Query(default=None, min_length=1, max_length=120, alias="search"),
    include_inactive: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ProductSummary]:
    filters: list[str] = []
    params: dict[str, object] = {"limit": limit, "offset": offset}

    if not include_inactive:
        filters.append("(p.actif IS NULL OR p.actif = TRUE)")

    if query:
        filters.append(
            "(LOWER(p.nom) LIKE :pattern OR EXISTS ("
            "SELECT 1 FROM produits_barcodes pb "
            "WHERE pb.produit_id = p.id AND LOWER(pb.code) LIKE :pattern"
            "))"
        )
        params["pattern"] = f"%{query.lower()}%"

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    sql = text(
        f"""
        SELECT
            p.id,
            p.nom,
            p.categorie,
            p.prix_vente,
            p.tva,
            p.stock_actuel,
            p.actif
        FROM produits p
        {where_clause}
        ORDER BY p.nom ASC
        LIMIT :limit OFFSET :offset
        """
    )

    df = query_df(sql, params)
    if df.empty:
        return []
    return [ProductSummary(**record) for record in df.to_dict("records")]


@app.get("/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int) -> ProductDetail:
    detail = _fetch_product_basic(product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return detail


@app.get("/products/{product_id}/movements", response_model=list[StockMovement])
def get_product_movements(
    product_id: int,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[StockMovement]:
    detail = _fetch_product_basic(product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    sql = text(
        """
        SELECT id, produit_id, type, quantite, source, date_mvt
        FROM mouvements_stock
        WHERE produit_id = :pid
        ORDER BY date_mvt DESC, id DESC
        LIMIT :limit
        """
    )
    df = query_df(sql, {"pid": product_id, "limit": limit})
    if df.empty:
        return []
    return [StockMovement(**record) for record in df.to_dict("records")]


@app.get("/stock/movements", response_model=list[StockMovement])
def list_stock_movements(
    product_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[StockMovement]:
    params: dict[str, object] = {"limit": limit}
    filters: list[str] = []
    if product_id is not None:
        filters.append("m.produit_id = :pid")
        params["pid"] = product_id
        if _fetch_product_basic(product_id) is None:
            raise HTTPException(status_code=404, detail="Produit introuvable")

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    sql = text(
        f"""
        SELECT m.id, m.produit_id, m.type, m.quantite, m.source, m.date_mvt
        FROM mouvements_stock m
        {where_clause}
        ORDER BY m.date_mvt DESC, m.id DESC
        LIMIT :limit
        """
    )
    df = query_df(sql, params)
    if df.empty:
        return []
    return [StockMovement(**record) for record in df.to_dict("records")]


@app.post("/stock/update", response_model=StockUpdateResult)
def update_stock_external(update: StockUpdate) -> StockUpdateResult:
    """Enregistre un mouvement de stock simple."""

    return _insert_stock_movement(update)


@app.post("/stock/bulk-update", response_model=BulkUpdateResponse)
def bulk_update_stock(payload: BulkStockUpdate) -> BulkUpdateResponse:
    """Permet d'enregistrer plusieurs mouvements dans une seule requête."""

    results: list[StockUpdateResult] = []
    errors: list[str] = []
    for update in payload.updates:
        try:
            results.append(_insert_stock_movement(update))
        except HTTPException as exc:
            errors.append(f"product_id={update.product_id}: {exc.detail}")

    response_payload = BulkUpdateResponse(accepted=len(results), results=results, errors=errors)
    if errors:
        return JSONResponse(
            status_code=status.HTTP_207_MULTI_STATUS,
            content=response_payload.model_dump(mode="json"),
        )
    return response_payload


# COMMANDE POUR LANCER L'API : uvicorn api_server:app --reload --port 8000


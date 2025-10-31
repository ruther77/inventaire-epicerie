"""FastAPI application exposing the inventory features for the new SPA."""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Iterable, List

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from data_repository import query_df
from inventory_service import process_sale_transaction
from product_service import (
    InvalidBarcodeError,
    ProductNotFoundError,
    update_catalog_entry,
)


class ProductPayload(BaseModel):
    """Lightweight projection of a product for the SPA."""

    id: int
    nom: str
    categorie: str | None = None
    prix_vente: float = Field(..., ge=0)
    prix_achat: float | None = Field(default=None, ge=0)
    stock_actuel: float | None = Field(default=None, ge=0)
    tva: float | None = Field(default=None, ge=0)


class POSCartLine(BaseModel):
    id: int = Field(..., description="Identifiant du produit")
    qty: float = Field(..., gt=0, description="Quantité vendue")
    nom: str | None = Field(default=None, description="Nom affiché dans le ticket")
    prix_vente: float | None = Field(default=None, ge=0)
    tva: float | None = Field(default=None, ge=0)

    @validator("nom")
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CheckoutRequest(BaseModel):
    cart: List[POSCartLine]
    username: str | None = Field(default=None, description="Utilisateur effectuant la vente")


class CheckoutResponse(BaseModel):
    success: bool
    message: str | None = None
    receipt_filename: str | None = None
    receipt_base64: str | None = None


class ProductUpdateRequest(BaseModel):
    nom: str | None = None
    categorie: str | None = None
    prix_vente: float | None = Field(default=None, ge=0)
    prix_achat: float | None = Field(default=None, ge=0)
    tva: float | None = Field(default=None, ge=0)
    actif: bool | None = None
    seuil_alerte: float | None = Field(default=None, ge=0)
    barcodes: List[str] | None = Field(default=None, description="Codes-barres associés")

    @validator("barcodes")
    def _clean_barcodes(cls, value: Iterable[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for raw in value:
            text = str(raw or "").strip()
            if text:
                cleaned.append(text)
        return cleaned


def _fetch_products() -> list[ProductPayload]:
    """Retourne la liste des produits via la base de données."""

    sql = """
        SELECT
            p.id,
            p.nom,
            p.categorie,
            COALESCE(p.prix_vente, 0) AS prix_vente,
            p.prix_achat,
            p.stock_actuel,
            p.tva
        FROM produits p
        ORDER BY p.nom ASC
    """
    df = query_df(sql)
    if df.empty:
        return []
    return [ProductPayload(**record) for record in df.to_dict("records")]


def _compute_inventory_value() -> dict[str, float]:
    sql = """
        SELECT
            SUM(COALESCE(prix_achat, 0) * COALESCE(stock_actuel, 0)) AS total_achat,
            SUM(COALESCE(prix_vente, 0) * COALESCE(stock_actuel, 0)) AS total_vente
        FROM produits
    """
    df = query_df(sql)
    if df.empty:
        return {"total_purchase_value": 0.0, "total_sale_value": 0.0}
    row = df.iloc[0]
    return {
        "total_purchase_value": float(row.get("total_achat") or 0),
        "total_sale_value": float(row.get("total_vente") or 0),
    }


@lru_cache
def create_app() -> FastAPI:
    app = FastAPI(title="Inventaire Epicerie API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/products", response_model=list[ProductPayload])
    def list_products() -> list[ProductPayload]:
        return _fetch_products()

    @app.get("/inventory/summary")
    def inventory_summary() -> dict[str, float]:
        return _compute_inventory_value()

    @app.post("/pos/checkout", response_model=CheckoutResponse)
    def checkout(payload: CheckoutRequest) -> CheckoutResponse:
        success, message, receipt = process_sale_transaction(
            [item.dict() for item in payload.cart],
            payload.username or "api_user",
        )

        if not success:
            return CheckoutResponse(success=False, message=message)

        receipt_filename = None
        receipt_base64 = None
        if receipt:
            receipt_filename = receipt.get("filename")
            raw_content = receipt.get("content")
            if isinstance(raw_content, bytes):
                receipt_base64 = base64.b64encode(raw_content).decode("ascii")

        return CheckoutResponse(
            success=True,
            message=message,
            receipt_filename=receipt_filename,
            receipt_base64=receipt_base64,
        )

    @app.patch("/products/{product_id}")
    def update_product(product_id: int, payload: ProductUpdateRequest) -> dict[str, object]:
        try:
            result = update_catalog_entry(
                product_id,
                {
                    key: value
                    for key, value in payload.dict(exclude={"barcodes"}).items()
                    if value is not None
                },
                payload.barcodes,
            )
        except ProductNotFoundError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidBarcodeError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return {"status": "updated", "result": result}

    return app


app = create_app()

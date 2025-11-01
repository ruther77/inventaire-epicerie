"""Procurement management endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from data_repository import (
    create_procurement_record,
    list_procurements,
    update_procurement_record,
)

from ..security import get_current_active_user, require_catalog_manager
from .schemas import ProcurementCreate, ProcurementLinePayload, ProcurementRead, ProcurementUpdate
from .utils import as_decimal, ensure_datetime

router = APIRouter(prefix="/procurements", tags=["procurements"])


def _compute_procurement_total(lines: Iterable[ProcurementLinePayload]) -> Decimal:
    total = Decimal("0")
    for line in lines:
        qty = as_decimal(line.quantite)
        unit = as_decimal(line.prix_unitaire)
        if qty <= 0 or unit < 0:
            continue
        total += qty * unit
    return total


def _procurement_to_model(row: dict) -> ProcurementRead:
    return ProcurementRead(
        id=row["id"],
        numero=row["numero"],
        date_appro=row["date_appro"],
        fournisseur_id=row.get("fournisseur_id"),
        fournisseur_nom=row.get("fournisseur_nom"),
        statut=row["statut"],
        total_ht=float(row.get("total_ht") or 0),
        lignes_count=int(row.get("lignes_count") or 0),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("", response_model=list[ProcurementRead])
def list_procurements_endpoint(_: dict = Depends(get_current_active_user)) -> list[ProcurementRead]:
    rows = list_procurements()
    return [_procurement_to_model(row) for row in rows]


@router.post("", response_model=ProcurementRead, status_code=status.HTTP_201_CREATED)
def create_procurement(payload: ProcurementCreate, _: dict = Depends(require_catalog_manager)) -> ProcurementRead:
    total_ht = _compute_procurement_total(payload.lignes)
    procurement_payload = {
        "numero": payload.numero,
        "date_appro": ensure_datetime(payload.date_appro),
        "fournisseur_id": payload.fournisseur_id,
        "statut": payload.statut or "Reçu",
        "total_ht": float(total_ht),
    }
    line_items = [
        {
            "produit_id": line.produit_id,
            "quantite": line.quantite,
            "prix_unitaire": line.prix_unitaire,
        }
        for line in payload.lignes
    ]
    try:
        created = create_procurement_record(procurement_payload, line_items)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fournisseur ou produit introuvable",
        ) from exc
    enriched = next((row for row in list_procurements() if row["id"] == created["id"]), None)
    data = enriched or {**created, "fournisseur_nom": None, "lignes_count": len(line_items)}
    return _procurement_to_model(data)


@router.patch("/{procurement_id}", response_model=ProcurementRead)
def update_procurement(
    procurement_id: int,
    payload: ProcurementUpdate,
    _: dict = Depends(require_catalog_manager),
) -> ProcurementRead:
    updates = payload.model_dump(exclude_unset=True)
    if "date_appro" in updates and updates["date_appro"] is not None:
        updates["date_appro"] = ensure_datetime(updates["date_appro"])
    record = update_procurement_record(procurement_id, updates)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approvisionnement introuvable")
    enriched = next((row for row in list_procurements() if row["id"] == record["id"]), None)
    data = enriched or {**record, "fournisseur_nom": None, "lignes_count": 0}
    return _procurement_to_model(data)

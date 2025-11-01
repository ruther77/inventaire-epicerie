"""Order management endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from .._fastapi_compat import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from data_repository import create_order_record, list_orders as repository_list_orders, update_order_record

from ..security import get_current_active_user, require_partner_access
from .schemas import OrderCreate, OrderLinePayload, OrderRead, OrderUpdate
from .utils import as_decimal, ensure_datetime

router = APIRouter(prefix="/orders", tags=["orders"])


def _compute_order_totals(lines: Iterable[OrderLinePayload]) -> tuple[Decimal, Decimal]:
    total_ht = Decimal("0")
    total_ttc = Decimal("0")

    for line in lines:
        qty = as_decimal(line.quantite)
        unit_price = as_decimal(line.prix_unitaire)
        if qty <= 0 or unit_price < 0:
            continue

        line_ht = qty * unit_price
        total_ht += line_ht

        tva_rate = as_decimal(line.tva)
        if tva_rate < 0:
            tva_rate = Decimal("0")
        total_ttc += line_ht * (Decimal("1") + tva_rate / Decimal("100"))

    return total_ht, total_ttc


def _order_to_model(row: dict) -> OrderRead:
    return OrderRead(
        id=row["id"],
        numero=row["numero"],
        date_commande=row["date_commande"],
        client_id=row.get("client_id"),
        client_nom=row.get("client_nom"),
        statut=row["statut"],
        total_ht=float(row.get("total_ht") or 0),
        total_ttc=float(row.get("total_ttc") or 0),
        lignes_count=int(row.get("lignes_count") or 0),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("", response_model=list[OrderRead])
def list_orders(_: dict = Depends(require_partner_access)) -> list[OrderRead]:
    rows = repository_list_orders()
    return [_order_to_model(row) for row in rows]


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, _: dict = Depends(require_partner_access)) -> OrderRead:
    total_ht, total_ttc = _compute_order_totals(payload.lignes)
    order_payload = {
        "numero": payload.numero,
        "date_commande": ensure_datetime(payload.date_commande),
        "client_id": payload.client_id,
        "statut": payload.statut or "Brouillon",
        "total_ht": float(total_ht),
        "total_ttc": float(total_ttc),
    }
    line_items = [
        {
            "produit_id": line.produit_id,
            "quantite": line.quantite,
            "prix_unitaire": line.prix_unitaire,
            "tva": line.tva,
        }
        for line in payload.lignes
    ]
    try:
        created = create_order_record(order_payload, line_items)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client ou produit introuvable",
        ) from exc
    enriched = next((row for row in repository_list_orders() if row["id"] == created["id"]), None)
    data = enriched or {**created, "client_nom": None, "lignes_count": len(line_items)}
    return _order_to_model(data)


@router.patch("/{order_id}", response_model=OrderRead)
def update_order(order_id: int, payload: OrderUpdate, _: dict = Depends(require_partner_access)) -> OrderRead:
    updates = payload.model_dump(exclude_unset=True)
    if "date_commande" in updates and updates["date_commande"] is not None:
        updates["date_commande"] = ensure_datetime(updates["date_commande"])
    record = update_order_record(order_id, updates)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    enriched = next((row for row in repository_list_orders() if row["id"] == record["id"]), None)
    data = enriched or {**record, "client_nom": None, "lignes_count": 0}
    return _order_to_model(data)

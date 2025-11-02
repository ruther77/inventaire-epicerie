"""Supplier management endpoints."""

from __future__ import annotations

from .._fastapi_compat import APIRouter, Depends, HTTPException, Response, status

from data_repository import (
    create_supplier_record,
    delete_supplier_record,
    list_suppliers,
    update_supplier_record,
)

from ..security import get_current_active_user, require_catalog_manager
from .schemas import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _supplier_to_model(row: dict) -> SupplierRead:
    return SupplierRead(
        id=row["id"],
        nom=row["nom"],
        telephone=row.get("telephone"),
        email=row.get("email"),
        adresse=row.get("adresse"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("", response_model=list[SupplierRead])
def list_suppliers_endpoint(_: dict = Depends(get_current_active_user)) -> list[SupplierRead]:
    rows = list_suppliers()
    return [_supplier_to_model(row) for row in rows]


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, _: dict = Depends(require_catalog_manager)) -> SupplierRead:
    record = create_supplier_record(payload.model_dump())
    return _supplier_to_model(record)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(supplier_id: int, payload: SupplierUpdate, _: dict = Depends(require_catalog_manager)) -> SupplierRead:
    updates = payload.model_dump(exclude_unset=True)
    record = update_supplier_record(supplier_id, updates)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fournisseur introuvable")
    return _supplier_to_model(record)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, _: dict = Depends(require_catalog_manager)) -> Response:
    if not delete_supplier_record(supplier_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fournisseur introuvable")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

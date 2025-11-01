"""Category management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from data_repository import (
    create_category_record,
    delete_category_record,
    list_categories,
    update_category_record,
)

from ..security import get_current_active_user, require_catalog_manager
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


def _category_to_model(row: dict) -> CategoryRead:
    return CategoryRead(
        id=row["id"],
        nom=row["nom"],
        description=row.get("description"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        produits_count=int(row.get("produits_count") or 0),
    )


@router.get("", response_model=list[CategoryRead])
def list_categories_endpoint(_: dict = Depends(get_current_active_user)) -> list[CategoryRead]:
    rows = list_categories()
    return [_category_to_model(row) for row in rows]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, _: dict = Depends(require_catalog_manager)) -> CategoryRead:
    record = create_category_record(payload.model_dump())
    enriched = next((row for row in list_categories() if row["id"] == record["id"]), None)
    data = enriched or {**record, "produits_count": 0}
    return _category_to_model(data)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, _: dict = Depends(require_catalog_manager)) -> CategoryRead:
    updates = payload.model_dump(exclude_unset=True)
    record = update_category_record(category_id, updates)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")
    enriched = next((row for row in list_categories() if row["id"] == record["id"]), None)
    data = enriched or {**record, "produits_count": 0}
    return _category_to_model(data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, _: dict = Depends(require_catalog_manager)) -> Response:
    if not delete_category_record(category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

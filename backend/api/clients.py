"""Client management endpoints."""

from __future__ import annotations

from .._fastapi_compat import APIRouter, Depends, HTTPException, Response, status

from data_repository import (
    create_client_record,
    delete_client_record,
    list_clients,
    update_client_record,
)

from ..security import get_current_active_user, require_admin
from .schemas import ClientCreate, ClientRead, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


def _client_to_model(row: dict) -> ClientRead:
    return ClientRead(
        id=row["id"],
        nom=row["nom"],
        telephone=row.get("telephone"),
        email=row.get("email"),
        adresse=row.get("adresse"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("", response_model=list[ClientRead])
def list_clients_endpoint(_: dict = Depends(get_current_active_user)) -> list[ClientRead]:
    rows = list_clients()
    return [_client_to_model(row) for row in rows]


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, _: dict = Depends(require_admin)) -> ClientRead:
    record = create_client_record(payload.model_dump())
    return _client_to_model(record)


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(client_id: int, payload: ClientUpdate, _: dict = Depends(require_admin)) -> ClientRead:
    updates = payload.model_dump(exclude_unset=True)
    record = update_client_record(client_id, updates)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")
    return _client_to_model(record)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, _: dict = Depends(require_admin)) -> Response:
    if not delete_client_record(client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

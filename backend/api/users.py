"""User management endpoints."""

from __future__ import annotations

import logging
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from inventory_service import get_saved_views_service

from ..security import get_current_active_user, get_password_hash, require_admin
from .schemas import SavedViewCollection, SavedViewEntry, UserCreate, UserRead, UserUpdate
from .utils import get_main_module

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _normalise_saved_views_payload(slots: dict[str, list[SavedViewEntry | dict]]) -> dict[str, list[dict]]:
    if not isinstance(slots, dict):
        return {}

    normalised: dict[str, list[dict]] = {}
    for slot, views in slots.items():
        if not isinstance(slot, str):
            continue
        cleaned: list[dict] = []
        if not isinstance(views, Iterable):
            continue
        for view in views:
            try:
                model = SavedViewEntry.model_validate(view)
            except ValidationError:
                logger.debug("Ignoring invalid saved view entry", extra={"slot": slot, "view": view})
                continue
            cleaned.append(model.model_dump(exclude_none=True))
        if cleaned:
            normalised[slot] = cleaned
    return normalised


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: dict = Depends(get_current_active_user)) -> UserRead:
    return UserRead(**current_user)


@router.get("/me/saved-views", response_model=SavedViewCollection)
def read_saved_views(current_user: dict = Depends(get_current_active_user)) -> SavedViewCollection:
    service = get_saved_views_service()
    raw_slots = service.fetch_views(current_user["id"])
    slots = _normalise_saved_views_payload(raw_slots)
    return SavedViewCollection(slots=slots)


@router.put("/me/saved-views", response_model=SavedViewCollection)
def update_saved_views(payload: SavedViewCollection, current_user: dict = Depends(get_current_active_user)) -> SavedViewCollection:
    slots = _normalise_saved_views_payload(payload.slots)
    service = get_saved_views_service()
    service.persist_views(current_user["id"], slots)
    return SavedViewCollection(slots=slots)


@router.get("", response_model=list[UserRead])
def list_users(_: dict = Depends(require_admin)) -> list[UserRead]:
    records = get_main_module().repository_list_users()
    return [UserRead(**record) for record in records]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, _: dict = Depends(require_admin)) -> UserRead:
    main = get_main_module()
    data = {
        "username": payload.username,
        "email": payload.email,
        "full_name": payload.full_name,
        "role": payload.role.lower(),
        "hashed_password": get_password_hash(payload.password),
        "is_active": payload.is_active,
    }
    try:
        record = main.create_user_record(data)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nom d'utilisateur ou e-mail déjà utilisé",
        ) from exc

    return UserRead(**record)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, _: dict = Depends(require_admin)) -> UserRead:
    main = get_main_module()
    existing = main.fetch_user_by_id(user_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    updates = payload.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] is not None:
        updates["role"] = updates["role"].lower()

    password = updates.pop("password", None)
    if password:
        updates["hashed_password"] = get_password_hash(password)

    target_role = updates.get("role", existing["role"])
    target_active = updates.get("is_active", existing["is_active"])
    if existing["role"] == "admin" and existing["is_active"]:
        if target_role != "admin" or target_active is False:
            if main.count_active_admins(exclude_user_id=user_id) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de retirer le dernier administrateur actif",
                )

    try:
        record = main.update_user_record(user_id, updates)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nom d'utilisateur ou e-mail déjà utilisé",
        ) from exc

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    return UserRead(**record)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, _: dict = Depends(require_admin)) -> Response:
    main = get_main_module()
    existing = main.fetch_user_by_id(user_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    if existing["role"] == "admin" and existing["is_active"]:
        if main.count_active_admins(exclude_user_id=user_id) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de supprimer le dernier administrateur actif",
            )

    if not main.delete_user_record(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    return Response(status_code=status.HTTP_204_NO_CONTENT)

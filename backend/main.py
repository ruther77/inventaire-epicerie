"""FastAPI application exposing the inventory features for the new SPA."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import lru_cache
from typing import Iterable, List
import hashlib
import hmac
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Response, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import re

import jwt
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.exc import IntegrityError

from data_repository import (
    count_active_admins,
    create_category_record,
    create_client_record,
    create_order_record,
    create_procurement_record,
    create_supplier_record,
    create_user_record,
    delete_category_record,
    delete_client_record,
    delete_supplier_record,
    delete_user_record,
    fetch_user_by_id,
    fetch_user_by_username,
    list_categories,
    list_clients,
    list_orders as repository_list_orders,
    list_procurements,
    list_suppliers,
    list_users as repository_list_users,
    query_df,
    update_category_record,
    update_client_record,
    update_order_record,
    update_procurement_record,
    update_supplier_record,
    update_user_record,
)
from inventory_service import get_saved_views_service, process_sale_transaction
from product_service import (
    InvalidBarcodeError,
    ProductNotFoundError,
    update_catalog_entry,
)


ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
if not AUTH_SECRET_KEY:
    raise RuntimeError("AUTH_SECRET_KEY environment variable must be configured for API startup.")
ALLOWED_ROLES = {"admin", "standard"}
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_ITERATIONS = int(os.getenv("AUTH_PBKDF2_ITERATIONS", "390000"))
PASSWORD_ALGORITHM = "sha256"
PASSWORD_SALT_BYTES = 16

if len(AUTH_SECRET_KEY) < 32:
    raise RuntimeError("AUTH_SECRET_KEY must be at least 32 characters long for JWT signing security.")

_raw_allowed_origins = os.getenv("API_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [origin.strip() for origin in _raw_allowed_origins.split(",") if origin.strip()]
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
ALLOW_ALL_ORIGINS = len(ALLOWED_ORIGINS) == 1 and ALLOWED_ORIGINS[0] == "*"

token_bearer = HTTPBearer(auto_error=False)


class InvalidTokenError(Exception):
    """Levée lorsque le jeton d'authentification est invalide."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


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

    @field_validator("nom", mode="before")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class CheckoutRequest(BaseModel):
    cart: List[POSCartLine]
    username: str | None = Field(default=None, description="Utilisateur effectuant la vente")


class CheckoutResponse(BaseModel):
    success: bool
    message: str | None = None
    receipt_filename: str | None = None
    receipt_base64: str | None = None
    total_ht: float | None = None
    total_ttc: float | None = None


class SavedViewBadge(BaseModel):
    label: str
    variant: str | None = None


class SavedViewEntry(BaseModel):
    id: str
    label: str
    description: str | None = None
    to: str | None = None
    badge: SavedViewBadge | None = None


class SavedViewCollection(BaseModel):
    slots: dict[str, list[SavedViewEntry]] = Field(default_factory=dict)


class ProductUpdateRequest(BaseModel):
    nom: str | None = None
    categorie: str | None = None
    prix_vente: float | None = Field(default=None, ge=0)
    prix_achat: float | None = Field(default=None, ge=0)
    tva: float | None = Field(default=None, ge=0)
    actif: bool | None = None
    seuil_alerte: float | None = Field(default=None, ge=0)
    barcodes: List[str] | None = Field(default=None, description="Codes-barres associés")

    @field_validator("barcodes", mode="before")
    @classmethod
    def _clean_barcodes(cls, value: Iterable[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for raw in value:
            text = str(raw or "").strip()
            if text:
                cleaned.append(text)
        return cleaned


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6, max_length=200)


class UserRead(BaseModel):
    id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    role: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: str | None = None
    full_name: str | None = Field(default=None, max_length=200)
    role: str = Field(default="standard")
    password: str = Field(..., min_length=6, max_length=200)
    is_active: bool = True

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str) -> str:
        role = str(value).lower()
        if role not in ALLOWED_ROLES:
            raise ValueError("Rôle utilisateur invalide")
        return role

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = str(value).strip()
        if not email:
            return None
        if not EMAIL_REGEX.match(email):
            raise ValueError("Adresse e-mail invalide")
        return email


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = Field(default=None, max_length=200)
    role: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=200)
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        role = str(value).lower()
        if role not in ALLOWED_ROLES:
            raise ValueError("Rôle utilisateur invalide")
        return role

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = str(value).strip()
        if not email:
            return None
        if not EMAIL_REGEX.match(email):
            raise ValueError("Adresse e-mail invalide")
        return email


class CategoryBase(BaseModel):
    nom: str = Field(..., min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("nom")
    @classmethod
    def _strip_nom(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom de la catégorie ne peut pas être vide.")
        return cleaned

    @field_validator("description")
    @classmethod
    def _strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("nom")
    @classmethod
    def _strip_optional_nom(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom de la catégorie ne peut pas être vide.")
        return cleaned

    @field_validator("description")
    @classmethod
    def _strip_optional_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CategoryRead(CategoryBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    produits_count: int = 0


class ClientBase(BaseModel):
    nom: str = Field(..., min_length=2, max_length=200)
    telephone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=200)
    adresse: str | None = Field(default=None, max_length=500)

    @field_validator("nom")
    @classmethod
    def _strip_nom(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom ne peut pas être vide.")
        return cleaned

    @field_validator("telephone", "email", "adresse")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=2, max_length=200)
    telephone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=200)
    adresse: str | None = Field(default=None, max_length=500)

    @field_validator("nom")
    @classmethod
    def _strip_optional_nom(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom ne peut pas être vide.")
        return cleaned

    @field_validator("telephone", "email", "adresse")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ClientRead(ClientBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SupplierBase(BaseModel):
    nom: str = Field(..., min_length=2, max_length=200)
    telephone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=200)
    adresse: str | None = Field(default=None, max_length=500)

    @field_validator("nom")
    @classmethod
    def _strip_nom(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom ne peut pas être vide.")
        return cleaned

    @field_validator("telephone", "email", "adresse")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=2, max_length=200)
    telephone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=200)
    adresse: str | None = Field(default=None, max_length=500)

    @field_validator("nom")
    @classmethod
    def _strip_optional_nom(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom ne peut pas être vide.")
        return cleaned

    @field_validator("telephone", "email", "adresse")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SupplierRead(SupplierBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrderLinePayload(BaseModel):
    produit_id: int | None = Field(default=None, description="Identifiant produit")
    quantite: float = Field(..., gt=0)
    prix_unitaire: float = Field(..., ge=0)
    tva: float = Field(default=0, ge=0)


class OrderCreate(BaseModel):
    numero: str = Field(..., min_length=3, max_length=60)
    date_commande: datetime | None = None
    client_id: int | None = None
    statut: str | None = Field(default="Brouillon", max_length=60)
    lignes: List[OrderLinePayload] = Field(default_factory=list)

    @field_validator("numero")
    @classmethod
    def _strip_numero(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le numéro de commande ne peut pas être vide.")
        return cleaned

    @field_validator("statut")
    @classmethod
    def _strip_statut(cls, value: str | None) -> str:
        if value is None:
            return "Brouillon"
        cleaned = value.strip()
        return cleaned or "Brouillon"


class OrderRead(BaseModel):
    id: int
    numero: str
    date_commande: datetime
    client_id: int | None = None
    client_nom: str | None = None
    statut: str
    total_ht: float
    total_ttc: float
    lignes_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrderUpdate(BaseModel):
    client_id: int | None = None
    statut: str | None = Field(default=None, max_length=60)
    date_commande: datetime | None = None

    @field_validator("statut")
    @classmethod
    def _strip_optional_statut(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ProcurementLinePayload(BaseModel):
    produit_id: int | None = Field(default=None)
    quantite: float = Field(..., gt=0)
    prix_unitaire: float = Field(..., ge=0)


class ProcurementCreate(BaseModel):
    numero: str = Field(..., min_length=3, max_length=60)
    date_appro: datetime | None = None
    fournisseur_id: int | None = None
    statut: str | None = Field(default="Reçu", max_length=60)
    lignes: List[ProcurementLinePayload] = Field(default_factory=list)

    @field_validator("numero")
    @classmethod
    def _strip_numero(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le numéro d'approvisionnement ne peut pas être vide.")
        return cleaned

    @field_validator("statut")
    @classmethod
    def _strip_statut(cls, value: str | None) -> str:
        if value is None:
            return "Reçu"
        cleaned = value.strip()
        return cleaned or "Reçu"


class ProcurementRead(BaseModel):
    id: int
    numero: str
    date_appro: datetime
    fournisseur_id: int | None = None
    fournisseur_nom: str | None = None
    statut: str
    total_ht: float
    lignes_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProcurementUpdate(BaseModel):
    fournisseur_id: int | None = None
    statut: str | None = Field(default=None, max_length=60)
    date_appro: datetime | None = None

    @field_validator("statut")
    @classmethod
    def _strip_optional_statut(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        scheme, iterations_text, salt_segment, hash_segment = hashed_password.split("$", 3)
    except ValueError:
        return False

    if scheme != f"pbkdf2_{PASSWORD_ALGORITHM}":
        return False

    try:
        iterations = int(iterations_text)
    except ValueError:
        return False

    salt = _b64url_decode(salt_segment)
    stored_hash = _b64url_decode(hash_segment)
    computed = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(stored_hash, computed)


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return (
        f"pbkdf2_{PASSWORD_ALGORITHM}$"
        f"{PASSWORD_ITERATIONS}$"
        f"{_b64url_encode(salt)}$"
        f"{_b64url_encode(derived)}"
    )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, AUTH_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("jeton expiré") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("jeton invalide") from exc

    return payload


def _public_user(user: dict) -> dict:
    return {
        key: user.get(key)
        for key in ("id", "username", "email", "full_name", "role", "is_active", "created_at", "updated_at")
        if key in user
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(token_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide") from exc

    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide")

    user = fetch_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur inconnu")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte utilisateur inactif")

    return _public_user(user)


def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


def require_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits administrateur requis")
    return current_user


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


def _load_active_products_map(product_ids: set[int]) -> dict[int, dict[str, object]]:
    if not product_ids:
        return {}

    ids = list(product_ids)
    placeholders = ", ".join(f":pid_{index}" for index, _ in enumerate(ids))
    params = {f"pid_{index}": pid for index, pid in enumerate(ids)}
    sql = text(
        f"""
        SELECT id,
               nom,
               COALESCE(prix_vente, 0) AS prix_vente,
               COALESCE(tva, 0) AS tva
        FROM produits
        WHERE actif = TRUE AND id IN ({placeholders})
        """
    )
    df = query_df(sql, params)
    if df.empty:
        return {}
    return {int(record["id"]): record for record in df.to_dict("records")}


def _as_decimal(value: float | int | str | None) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _quantize_currency(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _prepare_checkout_payload(cart: list[POSCartLine]) -> tuple[list[dict[str, object]], Decimal, Decimal]:
    if not cart:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le panier est vide.")

    product_ids = {line.id for line in cart}
    product_map = _load_active_products_map(product_ids)
    missing = sorted(pid for pid in product_ids if pid not in product_map)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Produits introuvables ou inactifs: {', '.join(map(str, missing))}",
        )

    sanitized: list[dict[str, object]] = []
    total_ht = Decimal("0")
    total_ttc = Decimal("0")

    for line in cart:
        qty = _as_decimal(line.qty)
        if qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quantité invalide pour le produit {line.id}",
            )

        product_data = product_map[line.id]
        unit_price = _as_decimal(product_data.get("prix_vente"))
        tva_rate = _as_decimal(product_data.get("tva"))

        sanitized.append(
            {
                "id": line.id,
                "nom": product_data.get("nom") or f"Produit {line.id}",
                "prix_vente": float(unit_price),
                "tva": float(tva_rate),
                "qty": float(qty),
            }
        )

        line_ht = qty * unit_price
        total_ht += line_ht
        total_ttc += line_ht * (Decimal("1") + tva_rate / Decimal("100"))

    return sanitized, total_ht, total_ttc


def _compute_order_totals(lines: Iterable[OrderLinePayload]) -> tuple[Decimal, Decimal]:
    total_ht = Decimal("0")
    total_ttc = Decimal("0")

    for line in lines:
        qty = _as_decimal(line.quantite)
        unit_price = _as_decimal(line.prix_unitaire)
        if qty <= 0 or unit_price < 0:
            continue

        line_ht = qty * unit_price
        total_ht += line_ht

        tva_rate = _as_decimal(line.tva)
        if tva_rate < 0:
            tva_rate = Decimal("0")
        total_ttc += line_ht * (Decimal("1") + tva_rate / Decimal("100"))

    return total_ht, total_ttc


def _compute_procurement_total(lines: Iterable[ProcurementLinePayload]) -> Decimal:
    total = Decimal("0")
    for line in lines:
        qty = _as_decimal(line.quantite)
        unit = _as_decimal(line.prix_unitaire)
        if qty <= 0 or unit < 0:
            continue
        total += qty * unit
    return total


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


def _ensure_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _category_to_model(row: dict) -> CategoryRead:
    return CategoryRead(
        id=row["id"],
        nom=row["nom"],
        description=row.get("description"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        produits_count=int(row.get("produits_count") or 0),
    )


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
        allow_origins=["*"] if ALLOW_ALL_ORIGINS else ALLOWED_ORIGINS,
        allow_credentials=not ALLOW_ALL_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/auth/login", response_model=LoginResponse)
    def login(payload: LoginRequest) -> LoginResponse:
        user = fetch_user_by_username(payload.username)
        if not user or not user.get("hashed_password"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
        if not user.get("is_active"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte utilisateur inactif")
        if not verify_password(payload.password, user["hashed_password"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")

        access_token = create_access_token({"sub": user["username"], "role": user.get("role", "standard")})
        return LoginResponse(access_token=access_token, user=UserRead(**_public_user(user)))

    @app.get("/users/me", response_model=UserRead)
    def read_current_user(current_user: dict = Depends(get_current_active_user)) -> UserRead:
        return UserRead(**current_user)

    @app.get("/users/me/saved-views", response_model=SavedViewCollection)
    def read_saved_views(current_user: dict = Depends(get_current_active_user)) -> SavedViewCollection:
        service = get_saved_views_service()
        raw_slots = service.fetch_views(current_user["id"])
        slots = _normalise_saved_views_payload(raw_slots)
        return SavedViewCollection(slots=slots)

    @app.put("/users/me/saved-views", response_model=SavedViewCollection)
    def update_saved_views(
        payload: SavedViewCollection,
        current_user: dict = Depends(get_current_active_user),
    ) -> SavedViewCollection:
        slots = _normalise_saved_views_payload(payload.slots)
        service = get_saved_views_service()
        service.persist_views(current_user["id"], slots)
        return SavedViewCollection(slots=slots)

    @app.get("/users", response_model=list[UserRead])
    def list_users(_: dict = Depends(require_admin)) -> list[UserRead]:
        records = repository_list_users()
        return [UserRead(**record) for record in records]

    @app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
    def create_user(payload: UserCreate, _: dict = Depends(require_admin)) -> UserRead:
        data = {
            "username": payload.username,
            "email": payload.email,
            "full_name": payload.full_name,
            "role": payload.role.lower(),
            "hashed_password": get_password_hash(payload.password),
            "is_active": payload.is_active,
        }
        try:
            record = create_user_record(data)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nom d'utilisateur ou e-mail déjà utilisé",
            ) from exc

        return UserRead(**record)

    @app.patch("/users/{user_id}", response_model=UserRead)
    def update_user(user_id: int, payload: UserUpdate, _: dict = Depends(require_admin)) -> UserRead:
        existing = fetch_user_by_id(user_id)
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
                if count_active_admins(exclude_user_id=user_id) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Impossible de retirer le dernier administrateur actif",
                    )

        try:
            record = update_user_record(user_id, updates)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nom d'utilisateur ou e-mail déjà utilisé",
            ) from exc

        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

        return UserRead(**record)

    @app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_user(user_id: int, _: dict = Depends(require_admin)) -> Response:
        existing = fetch_user_by_id(user_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

        if existing["role"] == "admin" and existing["is_active"]:
            if count_active_admins(exclude_user_id=user_id) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de supprimer le dernier administrateur actif",
                )

        if not delete_user_record(user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/categories", response_model=list[CategoryRead])
    def list_categories_endpoint(_: dict = Depends(get_current_active_user)) -> list[CategoryRead]:
        rows = list_categories()
        return [_category_to_model(row) for row in rows]

    @app.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
    def create_category(payload: CategoryCreate, _: dict = Depends(require_admin)) -> CategoryRead:
        record = create_category_record(payload.model_dump())
        enriched = next((row for row in list_categories() if row["id"] == record["id"]), None)
        data = enriched or {**record, "produits_count": 0}
        return _category_to_model(data)

    @app.patch("/categories/{category_id}", response_model=CategoryRead)
    def update_category(category_id: int, payload: CategoryUpdate, _: dict = Depends(require_admin)) -> CategoryRead:
        updates = payload.model_dump(exclude_unset=True)
        record = update_category_record(category_id, updates)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")
        enriched = next((row for row in list_categories() if row["id"] == record["id"]), None)
        data = enriched or {**record, "produits_count": 0}
        return _category_to_model(data)

    @app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_category(category_id: int, _: dict = Depends(require_admin)) -> Response:
        if not delete_category_record(category_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/clients", response_model=list[ClientRead])
    def list_clients_endpoint(_: dict = Depends(get_current_active_user)) -> list[ClientRead]:
        return [_client_to_model(row) for row in list_clients()]

    @app.post("/clients", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
    def create_client(payload: ClientCreate, _: dict = Depends(get_current_active_user)) -> ClientRead:
        record = create_client_record(payload.model_dump())
        return _client_to_model(record)

    @app.patch("/clients/{client_id}", response_model=ClientRead)
    def update_client(client_id: int, payload: ClientUpdate, _: dict = Depends(get_current_active_user)) -> ClientRead:
        updates = payload.model_dump(exclude_unset=True)
        record = update_client_record(client_id, updates)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")
        return _client_to_model(record)

    @app.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_client(client_id: int, _: dict = Depends(get_current_active_user)) -> Response:
        if not delete_client_record(client_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/suppliers", response_model=list[SupplierRead])
    def list_suppliers_endpoint(_: dict = Depends(get_current_active_user)) -> list[SupplierRead]:
        return [_supplier_to_model(row) for row in list_suppliers()]

    @app.post("/suppliers", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
    def create_supplier(payload: SupplierCreate, _: dict = Depends(get_current_active_user)) -> SupplierRead:
        record = create_supplier_record(payload.model_dump())
        return _supplier_to_model(record)

    @app.patch("/suppliers/{supplier_id}", response_model=SupplierRead)
    def update_supplier(supplier_id: int, payload: SupplierUpdate, _: dict = Depends(get_current_active_user)) -> SupplierRead:
        updates = payload.model_dump(exclude_unset=True)
        record = update_supplier_record(supplier_id, updates)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fournisseur introuvable")
        return _supplier_to_model(record)

    @app.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_supplier(supplier_id: int, _: dict = Depends(get_current_active_user)) -> Response:
        if not delete_supplier_record(supplier_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fournisseur introuvable")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/orders", response_model=list[OrderRead])
    def list_orders(_: dict = Depends(get_current_active_user)) -> list[OrderRead]:
        rows = repository_list_orders()
        return [_order_to_model(row) for row in rows]

    @app.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
    def create_order(payload: OrderCreate, _: dict = Depends(get_current_active_user)) -> OrderRead:
        total_ht, total_ttc = _compute_order_totals(payload.lignes)
        order_payload = {
            "numero": payload.numero,
            "date_commande": _ensure_datetime(payload.date_commande),
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

    @app.patch("/orders/{order_id}", response_model=OrderRead)
    def update_order(order_id: int, payload: OrderUpdate, _: dict = Depends(get_current_active_user)) -> OrderRead:
        updates = payload.model_dump(exclude_unset=True)
        if "date_commande" in updates and updates["date_commande"] is not None:
            updates["date_commande"] = _ensure_datetime(updates["date_commande"])
        record = update_order_record(order_id, updates)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
        enriched = next((row for row in repository_list_orders() if row["id"] == record["id"]), None)
        data = enriched or {**record, "client_nom": None, "lignes_count": 0}
        return _order_to_model(data)

    @app.get("/procurements", response_model=list[ProcurementRead])
    def list_procurements_endpoint(_: dict = Depends(get_current_active_user)) -> list[ProcurementRead]:
        rows = list_procurements()
        return [_procurement_to_model(row) for row in rows]

    @app.post("/procurements", response_model=ProcurementRead, status_code=status.HTTP_201_CREATED)
    def create_procurement(payload: ProcurementCreate, _: dict = Depends(get_current_active_user)) -> ProcurementRead:
        total_ht = _compute_procurement_total(payload.lignes)
        procurement_payload = {
            "numero": payload.numero,
            "date_appro": _ensure_datetime(payload.date_appro),
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

    @app.patch("/procurements/{procurement_id}", response_model=ProcurementRead)
    def update_procurement(
        procurement_id: int,
        payload: ProcurementUpdate,
        _: dict = Depends(get_current_active_user),
    ) -> ProcurementRead:
        updates = payload.model_dump(exclude_unset=True)
        if "date_appro" in updates and updates["date_appro"] is not None:
            updates["date_appro"] = _ensure_datetime(updates["date_appro"])
        record = update_procurement_record(procurement_id, updates)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approvisionnement introuvable")
        enriched = next((row for row in list_procurements() if row["id"] == record["id"]), None)
        data = enriched or {**record, "fournisseur_nom": None, "lignes_count": 0}
        return _procurement_to_model(data)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/products", response_model=list[ProductPayload])
    def list_products(_: dict = Depends(get_current_active_user)) -> list[ProductPayload]:
        return _fetch_products()

    @app.get("/inventory/summary")
    def inventory_summary(_: dict = Depends(get_current_active_user)) -> dict[str, float]:
        return _compute_inventory_value()

    @app.post("/pos/checkout", response_model=CheckoutResponse)
    def checkout(
        payload: CheckoutRequest,
        current_user: dict = Depends(get_current_active_user),
    ) -> CheckoutResponse:
        sanitized_cart, total_ht, total_ttc = _prepare_checkout_payload(payload.cart)
        success, message, receipt = process_sale_transaction(
            sanitized_cart,
            current_user.get("username") or "api_user",
        )

        total_ht_value = float(_quantize_currency(total_ht))
        total_ttc_value = float(_quantize_currency(total_ttc))

        if not success:
            return CheckoutResponse(
                success=False,
                message=message,
                total_ht=total_ht_value,
                total_ttc=total_ttc_value,
            )

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
            total_ht=total_ht_value,
            total_ttc=total_ttc_value,
        )

    @app.patch("/products/{product_id}")
    def update_product(
        product_id: int,
        payload: ProductUpdateRequest,
        _: dict = Depends(require_admin),
    ) -> dict[str, object]:
        try:
            result = update_catalog_entry(
                product_id,
                {
                    key: value
                    for key, value in payload.model_dump(exclude={"barcodes"}).items()
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

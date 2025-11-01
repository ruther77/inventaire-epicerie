"""Shared Pydantic schemas for the FastAPI routers."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List
import re

from pydantic import BaseModel, Field, ValidationError, field_validator

ALLOWED_ROLES = {"admin", "standard", "catalog_manager", "moderator", "partner"}
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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

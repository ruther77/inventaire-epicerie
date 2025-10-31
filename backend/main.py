"""FastAPI application exposing the inventory features for the new SPA."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Iterable, List
import hashlib
import hmac
import json
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Response, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import re

from pydantic import BaseModel, Field, validator
from sqlalchemy.exc import IntegrityError

from data_repository import (
    count_active_admins,
    create_user_record,
    fetch_user_by_id,
    fetch_user_by_username,
    list_users as repository_list_users,
    query_df,
    update_user_record,
    delete_user_record,
)
from inventory_service import process_sale_transaction
from product_service import (
    InvalidBarcodeError,
    ProductNotFoundError,
    update_catalog_entry,
)


ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "__inventaire_epicerie_secret__")
ALLOWED_ROLES = {"admin", "standard"}
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_ITERATIONS = int(os.getenv("AUTH_PBKDF2_ITERATIONS", "390000"))
PASSWORD_ALGORITHM = "sha256"
PASSWORD_SALT_BYTES = 16

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

    @validator("role")
    def _validate_role(cls, value: str) -> str:
        role = value.lower()
        if role not in ALLOWED_ROLES:
            raise ValueError("Rôle utilisateur invalide")
        return role

    @validator("email")
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip()
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

    @validator("role")
    def _validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        role = value.lower()
        if role not in ALLOWED_ROLES:
            raise ValueError("Rôle utilisateur invalide")
        return role

    @validator("email")
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip()
        if not email:
            return None
        if not EMAIL_REGEX.match(email):
            raise ValueError("Adresse e-mail invalide")
        return email


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
    to_encode["exp"] = int(expire.timestamp())

    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode_access_token(token: str) -> dict:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise InvalidTokenError("format de jeton invalide") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, signature):
        raise InvalidTokenError("signature invalide")

    payload_bytes = _b64url_decode(payload_segment)
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as exc:
        raise InvalidTokenError("charge utile illisible") from exc

    exp = payload.get("exp")
    if exp is not None:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts >= int(exp):
            raise InvalidTokenError("jeton expiré")

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

        updates = payload.dict(exclude_unset=True)
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

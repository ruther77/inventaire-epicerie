"""Authentication helpers shared across API routers."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any
import secrets

import jwt
from ._fastapi_compat import (
    Depends,
    HTTPAuthorizationCredentials,
    HTTPBearer,
    HTTPException,
    Security,
    status,
)

from data_repository import fetch_user_by_username

from .settings import APISettings, get_settings


token_bearer = HTTPBearer(auto_error=False)


class InvalidTokenError(Exception):
    """Raised when an authentication token cannot be validated."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def get_password_hash(password: str, settings: APISettings | None = None) -> str:
    cfg = settings or get_settings()
    salt = secrets.token_bytes(cfg.password_salt_bytes)
    derived = hashlib.pbkdf2_hmac(
        cfg.password_algorithm,
        password.encode("utf-8"),
        salt,
        cfg.auth_pbkdf2_iterations,
    )
    return (
        f"pbkdf2_{cfg.password_algorithm}$"
        f"{cfg.auth_pbkdf2_iterations}$"
        f"{_b64url_encode(salt)}$"
        f"{_b64url_encode(derived)}"
    )


def verify_password(plain_password: str, hashed_password: str, settings: APISettings | None = None) -> bool:
    cfg = settings or get_settings()
    try:
        scheme, iterations_text, salt_segment, hash_segment = hashed_password.split("$", 3)
    except ValueError:
        return False

    if scheme != f"pbkdf2_{cfg.password_algorithm}":
        return False

    try:
        iterations = int(iterations_text)
    except ValueError:
        return False

    salt = _b64url_decode(salt_segment)
    stored_hash = _b64url_decode(hash_segment)
    computed = hashlib.pbkdf2_hmac(
        cfg.password_algorithm,
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(stored_hash, computed)


def create_access_token(data: dict[str, Any], settings: APISettings | None = None, *, expires_delta: timedelta | None = None) -> str:
    cfg = settings or get_settings()
    to_encode = data.copy()
    expire_delta = expires_delta or timedelta(minutes=cfg.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode["exp"] = expire
    return jwt.encode(to_encode, cfg.auth_secret_key, algorithm="HS256")


def decode_access_token(token: str, settings: APISettings | None = None) -> dict[str, Any]:
    cfg = settings or get_settings()
    try:
        payload = jwt.decode(token, cfg.auth_secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("jeton expiré") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("jeton invalide") from exc
    return payload


def _resolve_user_from_credentials(credentials: HTTPAuthorizationCredentials) -> dict:
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

    return public_user(user)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Security(token_bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")

    return _resolve_user_from_credentials(credentials)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(token_bearer),
) -> dict | None:
    if credentials is None:
        return None

    return _resolve_user_from_credentials(credentials)


def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


MANAGEMENT_ROLES = {"admin", "catalog_manager"}
CATALOG_EDITOR_ROLES = MANAGEMENT_ROLES | {"moderator"}
PARTNER_ROLES = {"admin", "partner"}


def _normalize_role(role: str | None) -> str:
    return str(role or "standard").lower()


def _enforce_roles(current_user: dict, allowed_roles: set[str], detail: str) -> dict:
    role = _normalize_role(current_user.get("role"))
    if role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return current_user


def require_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    return _enforce_roles(current_user, {"admin"}, "Droits administrateur requis")


def require_catalog_manager(current_user: dict = Depends(get_current_active_user)) -> dict:
    return _enforce_roles(current_user, MANAGEMENT_ROLES, "Droits gestion catalogue requis")


def require_catalog_editor(current_user: dict = Depends(get_current_active_user)) -> dict:
    return _enforce_roles(
        current_user,
        CATALOG_EDITOR_ROLES,
        "Droits de gestion ou de modération du catalogue requis",
    )


def require_partner_access(current_user: dict = Depends(get_current_active_user)) -> dict:
    return _enforce_roles(current_user, PARTNER_ROLES, "Droits partenaire requis")


def require_moderator(current_user: dict = Depends(get_current_active_user)) -> dict:
    return _enforce_roles(current_user, {"admin", "moderator"}, "Droits de modération requis")


def public_user(user: dict) -> dict:
    return {
        key: user.get(key)
        for key in ("id", "username", "email", "full_name", "role", "is_active", "created_at", "updated_at")
        if key in user
    }

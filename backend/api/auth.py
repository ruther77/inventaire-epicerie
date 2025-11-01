"""Authentication endpoints."""

from __future__ import annotations

from .._fastapi_compat import APIRouter, HTTPException, status

from data_repository import fetch_user_by_username

from ..security import create_access_token, public_user, verify_password
from .schemas import LoginRequest, LoginResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = fetch_user_by_username(payload.username)
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte utilisateur inactif")
    if not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")

    access_token = create_access_token({"sub": user["username"], "role": user.get("role", "standard")})
    return LoginResponse(access_token=access_token, user=UserRead(**public_user(user)))

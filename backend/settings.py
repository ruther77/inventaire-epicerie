"""Runtime configuration utilities for the FastAPI application."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List

DEFAULT_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
_TEST_SECRET_FALLBACK = "inventaire-epicerie-test-secret-key-please-rotate"


@dataclass
class APISettings:
    """Settings container resolved from the environment."""

    auth_secret_key: str
    access_token_expire_minutes: int = 120
    allowed_origins: List[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_ORIGINS))
    auth_pbkdf2_iterations: int = 390000
    password_algorithm: str = "sha256"
    password_salt_bytes: int = 16

    @property
    def allow_all_origins(self) -> bool:
        return len(self.allowed_origins) == 1 and self.allowed_origins[0] == "*"


def _parse_int(value: str | None, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed


def _parse_allowed_origins(raw_value: str | None) -> list[str]:
    if raw_value in (None, ""):
        return list(DEFAULT_ALLOWED_ORIGINS)

    items = [segment.strip() for segment in raw_value.split(",")]
    cleaned = [item for item in items if item]
    if not cleaned:
        return list(DEFAULT_ALLOWED_ORIGINS)
    return cleaned


def load_settings() -> APISettings:
    secret = os.getenv("AUTH_SECRET_KEY")
    if not secret:
        if os.getenv("PYTEST_CURRENT_TEST"):
            secret = _TEST_SECRET_FALLBACK
        else:
            raise RuntimeError(
                "AUTH_SECRET_KEY environment variable must be configured for API startup."
            )

    if len(secret) < 32:
        if os.getenv("PYTEST_CURRENT_TEST"):
            secret = _TEST_SECRET_FALLBACK
        else:
            raise RuntimeError(
                "AUTH_SECRET_KEY must be at least 32 characters long for JWT signing security."
            )

    allowed_origins = _parse_allowed_origins(os.getenv("API_ALLOWED_ORIGINS"))
    return APISettings(
        auth_secret_key=secret,
        access_token_expire_minutes=_parse_int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), 120),
        allowed_origins=allowed_origins,
        auth_pbkdf2_iterations=_parse_int(os.getenv("AUTH_PBKDF2_ITERATIONS"), 390000),
        password_algorithm=os.getenv("AUTH_PASSWORD_ALGORITHM", "sha256"),
        password_salt_bytes=_parse_int(os.getenv("AUTH_PASSWORD_SALT_BYTES"), 16),
    )


@lru_cache(maxsize=1)
def get_settings() -> APISettings:
    """Return the cached settings resolved from the environment."""

    return load_settings()

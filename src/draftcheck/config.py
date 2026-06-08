"""Configuration for the V3 DraftCheck app."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal, cast


SameSite = Literal["lax", "strict", "none"]


def _bool_from_env(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean environment value: {value}")


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


def _samesite_from_env(value: str | None) -> SameSite:
    normalized = (value or "lax").strip().lower()
    if normalized not in {"lax", "strict", "none"}:
        raise ValueError("SESSION_COOKIE_SAMESITE must be lax, strict, or none")
    return cast(SameSite, normalized)


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    frontend_url: str = "http://localhost:5173"
    auth_token_hash_pepper: str = ""
    session_cookie_name: str = "draftcheck_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: SameSite = "lax"
    cors_allowed_origins: tuple[str, ...] = ("http://localhost:5173",)

    @classmethod
    def from_env(cls) -> Settings:
        app_env = os.getenv("DRAFTCHECK_ENV") or os.getenv("APP_ENV") or "local"
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        secure_override = _bool_from_env(os.getenv("SESSION_COOKIE_SECURE"))
        secure = secure_override if secure_override is not None else app_env.lower() == "production"
        origins = _split_csv(os.getenv("CORS_ALLOWED_ORIGINS")) or (frontend_url,)
        return cls(
            app_env=app_env,
            frontend_url=frontend_url,
            auth_token_hash_pepper=os.getenv("AUTH_TOKEN_HASH_PEPPER", ""),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "draftcheck_session"),
            session_cookie_secure=secure,
            session_cookie_samesite=_samesite_from_env(os.getenv("SESSION_COOKIE_SAMESITE")),
            cors_allowed_origins=origins,
        )


def get_settings() -> Settings:
    return Settings.from_env()

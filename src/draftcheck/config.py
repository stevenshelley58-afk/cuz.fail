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


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


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
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "LotFile"
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    smtp_timeout_seconds: int = 10
    llm_provider: str = "mock"
    llm_model: str = ""
    llm_timeout_seconds: int = 30
    llm_max_output_tokens: int = 700
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = ""
    openrouter_app_name: str = "LotFile"

    @classmethod
    def from_env(cls) -> Settings:
        app_env = os.getenv("DRAFTCHECK_ENV") or os.getenv("APP_ENV") or "local"
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        secure_override = _bool_from_env(os.getenv("SESSION_COOKIE_SECURE"))
        secure = secure_override if secure_override is not None else app_env.lower() == "production"
        origins = _split_csv(os.getenv("CORS_ALLOWED_ORIGINS")) or (frontend_url,)
        smtp_starttls = _bool_from_env(os.getenv("SMTP_STARTTLS"))
        smtp_ssl = _bool_from_env(os.getenv("SMTP_SSL"))
        return cls(
            app_env=app_env,
            frontend_url=frontend_url,
            auth_token_hash_pepper=os.getenv("AUTH_TOKEN_HASH_PEPPER", ""),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "draftcheck_session"),
            session_cookie_secure=secure,
            session_cookie_samesite=_samesite_from_env(os.getenv("SESSION_COOKIE_SAMESITE")),
            cors_allowed_origins=origins,
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=_int_from_env("SMTP_PORT", 587),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_from=os.getenv("SMTP_FROM", ""),
            smtp_from_name=os.getenv("SMTP_FROM_NAME", "LotFile"),
            smtp_starttls=True if smtp_starttls is None else smtp_starttls,
            smtp_ssl=False if smtp_ssl is None else smtp_ssl,
            smtp_timeout_seconds=_int_from_env("SMTP_TIMEOUT_SECONDS", 10),
            llm_provider=os.getenv("LLM_PROVIDER", "mock"),
            llm_model=os.getenv("LLM_MODEL", ""),
            llm_timeout_seconds=_int_from_env("LLM_TIMEOUT_SECONDS", 30),
            llm_max_output_tokens=_int_from_env("LLM_MAX_OUTPUT_TOKENS", 700),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openrouter_site_url=os.getenv("OPENROUTER_SITE_URL", ""),
            openrouter_app_name=os.getenv("OPENROUTER_APP_NAME", "LotFile"),
        )


def get_settings() -> Settings:
    return Settings.from_env()

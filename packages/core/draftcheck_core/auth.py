from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from secrets import compare_digest

from draftcheck_core.config import Settings, get_settings


@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    actor_id: str
    role: str = "api_client"


@dataclass(frozen=True)
class _ApiKeySpec:
    tenant_id: str
    key: str


_current_auth_context: ContextVar[AuthContext | None] = ContextVar(
    "draftcheck_auth_context",
    default=None,
)


def check_api_auth_ready(settings: Settings | None = None) -> dict[str, str]:
    resolved = settings or get_settings()
    keys = _configured_key_specs(resolved)
    if resolved.api_auth_enabled:
        if not keys:
            return {
                "status": "error",
                "detail": "API_AUTH_ENABLED=true but API_AUTH_KEYS is empty.",
            }
        if resolved.require_durable_database:
            production_issue = _production_key_readiness_issue(keys)
            if production_issue:
                return {"status": "error", "detail": production_issue}
        return {"status": "ok", "detail": "API key authentication enabled"}
    if resolved.require_durable_database:
        return {
            "status": "error",
            "detail": (
                "REQUIRE_DURABLE_DATABASE=true but API_AUTH_ENABLED=false; "
                "enable API auth before public deployment."
            ),
        }
    return {"status": "disabled", "detail": "API_AUTH_ENABLED=false"}


def api_key_is_valid(token: str, settings: Settings | None = None) -> bool:
    return authenticate_api_key(token, settings) is not None


def authenticate_api_key(token: str, settings: Settings | None = None) -> AuthContext | None:
    if not token:
        return None
    for key_spec in _configured_key_specs(settings or get_settings()):
        if compare_digest(token, key_spec.key):
            return AuthContext(
                tenant_id=key_spec.tenant_id,
                actor_id=key_spec.tenant_id,
            )
    return None


def get_current_auth_context() -> AuthContext | None:
    return _current_auth_context.get()


def set_current_auth_context(context: AuthContext | None) -> Token[AuthContext | None]:
    return _current_auth_context.set(context)


def reset_current_auth_context(token: Token[AuthContext | None]) -> None:
    _current_auth_context.reset(token)


def _configured_key_specs(settings: Settings) -> tuple[_ApiKeySpec, ...]:
    specs: list[_ApiKeySpec] = []
    for raw_key in settings.api_auth_keys:
        entry = raw_key.strip()
        if not entry:
            continue
        tenant_id, separator, key = entry.partition(":")
        if separator:
            key = key.strip()
            if not key:
                continue
            tenant_id = tenant_id.strip() or "default"
        else:
            tenant_id = "default"
            key = entry
        specs.append(_ApiKeySpec(tenant_id=tenant_id, key=key))
    return tuple(specs)


def _production_key_readiness_issue(keys: tuple[_ApiKeySpec, ...]) -> str | None:
    if any(spec.tenant_id == "default" for spec in keys):
        return "Production API_AUTH_KEYS must use tenant-scoped entries in tenant-id:key format."
    if any(len(spec.key) < 32 for spec in keys):
        return "Production API_AUTH_KEYS values must be at least 32 characters long."
    return None

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic
from typing import Deque

from fastapi import Request

from draftcheck_core.auth import authenticate_api_key
from draftcheck_core.config import Settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    limit: int
    window_seconds: float
    bucket: str


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: float,
        now: float | None = None,
    ) -> RateLimitDecision:
        current = monotonic() if now is None else now
        hits = self._hits[key]
        cutoff = current - window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, int(round(hits[0] + window_seconds - current)))
            return RateLimitDecision(
                allowed=False,
                retry_after_seconds=retry_after,
                limit=limit,
                window_seconds=window_seconds,
                bucket=key,
            )
        hits.append(current)
        return RateLimitDecision(
            allowed=True,
            retry_after_seconds=0,
            limit=limit,
            window_seconds=window_seconds,
            bucket=key,
        )


def request_rate_limit(request: Request, settings: Settings) -> tuple[str, int] | None:
    if not settings.rate_limit_enabled or request.method.upper() != "POST":
        return None

    path = request.url.path
    if _is_upload_path(path):
        return "upload", settings.rate_limit_upload_requests
    if _is_chat_path(path):
        return "chat", settings.rate_limit_chat_requests
    return None


def check_rate_limit_ready(settings: Settings) -> dict[str, str]:
    durable_deployment = settings.require_durable_database or settings.require_durable_object_storage
    if not settings.rate_limit_enabled:
        if durable_deployment:
            return {
                "status": "error",
                "detail": "Durable deployments must enable rate limiting for upload and chat endpoints.",
            }
        return {"status": "disabled", "detail": "rate limiting disabled"}

    if settings.rate_limit_window_seconds <= 0:
        return {
            "status": "error",
            "detail": "RATE_LIMIT_WINDOW_SECONDS must be greater than 0 when rate limiting is enabled.",
        }
    if durable_deployment and settings.rate_limit_chat_requests <= 0:
        return {
            "status": "error",
            "detail": "Durable deployments require RATE_LIMIT_CHAT_REQUESTS to be greater than 0.",
        }
    if durable_deployment and settings.rate_limit_upload_requests <= 0:
        return {
            "status": "error",
            "detail": "Durable deployments require RATE_LIMIT_UPLOAD_REQUESTS to be greater than 0.",
        }
    return {"status": "ok", "detail": "rate limiting enabled for upload and chat endpoints"}


def rate_limit_key(request: Request, bucket: str, settings: Settings) -> str:
    if settings.api_auth_enabled:
        auth_context = authenticate_api_key(_request_api_token(request), settings)
        if auth_context:
            return f"{bucket}:tenant:{auth_context.tenant_id}"
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else "unknown")
    return f"{bucket}:ip:{client_host}"


def _request_api_token(request: Request) -> str:
    api_key = request.headers.get("x-api-key", "").strip()
    if api_key:
        return api_key
    authorization = request.headers.get("authorization", "").strip()
    scheme, separator, token = authorization.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


def _is_upload_path(path: str) -> bool:
    return path.endswith("/documents/upload") and "/projects/" in path


def _is_chat_path(path: str) -> bool:
    if path.endswith(("/chat", "/ask", "/ask-source", "/ask-source-library")):
        return True
    return False

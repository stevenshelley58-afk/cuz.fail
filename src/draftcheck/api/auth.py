"""V3 auth router: magic-link auth, plus a dev-only password login (off in production)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from threading import Lock
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from draftcheck.config import Settings, get_settings
from draftcheck.domain.identity import (
    ActiveSession,
    DevLogEmailSender,
    EmailSender,
    IdentityRole,
    InMemoryIdentityStore,
    MissingEmailSender,
    SESSION_TTL,
    SmtpEmailSender,
)
from draftcheck.domain.identity.sqlalchemy_store import SqlAlchemyIdentityStore


router = APIRouter(tags=["auth"])

IdentityStore = InMemoryIdentityStore | SqlAlchemyIdentityStore

_identity_store: IdentityStore | None = None
_dev_email_sender = DevLogEmailSender()


class MagicLinkRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    org_slug: str | None = Field(default=None, max_length=80)


class MagicLinkRequestedResponse(BaseModel):
    status: str
    expires_at: datetime


class MagicLinkVerifyRequest(BaseModel):
    token: str = Field(min_length=32)


class DevLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: str
    org_id: str
    email: str
    role: str
    status: str


class SessionResponse(BaseModel):
    id: str
    org_id: str
    user: UserResponse
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class VerifyMagicLinkResponse(BaseModel):
    session: SessionResponse


class LogoutResponse(BaseModel):
    status: str


def get_identity_store(settings: Annotated[Settings, Depends(get_settings)]) -> IdentityStore:
    global _identity_store
    if _identity_store is None:
        token_hash_pepper = settings.auth_token_hash_pepper or None
        database_url = os.getenv("DATABASE_URL")
        if database_url and os.getenv("DRAFTCHECK_AUTH_STORE", "auto") != "memory":
            _identity_store = SqlAlchemyIdentityStore.from_database_url(
                database_url,
                token_hash_pepper=token_hash_pepper,
            )
        else:
            _identity_store = InMemoryIdentityStore(
                token_hash_pepper=token_hash_pepper,
            )
    return _identity_store


def get_email_sender(settings: Annotated[Settings, Depends(get_settings)]) -> EmailSender:
    if settings.smtp_host:
        return SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_address=settings.smtp_from,
            from_name=settings.smtp_from_name,
            use_starttls=settings.smtp_starttls,
            use_ssl=settings.smtp_ssl,
            timeout_seconds=settings.smtp_timeout_seconds,
        )
    if settings.app_env.strip().lower() == "production":
        return MissingEmailSender()
    return _dev_email_sender


def _client_host(request: Request) -> str | None:
    return request.client.host if request.client else None


def _assert_allowed_origin(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin is required for this auth request",
        )
    normalized_origin = origin.rstrip("/")
    if normalized_origin not in settings.cors_allowed_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin is not allowed for this auth request",
        )


def require_allowed_origin(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    _assert_allowed_origin(request, settings)


def _session_response(active_session: ActiveSession) -> SessionResponse:
    return SessionResponse(
        id=str(active_session.session.id),
        org_id=str(active_session.org.id),
        user=UserResponse(
            id=str(active_session.user.id),
            org_id=str(active_session.user.org_id),
            email=active_session.user.email,
            role=active_session.user.role.value,
            status=active_session.user.status,
        ),
        created_at=active_session.session.created_at,
        last_seen_at=active_session.session.last_seen_at,
        expires_at=active_session.session.expires_at,
    )


def _set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
    )


def get_current_session(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
) -> ActiveSession:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No active session")
    active_session = store.get_session(token)
    if active_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No active session")
    return active_session


@router.post(
    "/auth/magic-link/request",
    response_model=MagicLinkRequestedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
def request_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> MagicLinkRequestedResponse:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("/auth/magic-link/verify", response_model=VerifyMagicLinkResponse, include_in_schema=False)
def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
) -> VerifyMagicLinkResponse:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("/auth/dev-login", response_model=VerifyMagicLinkResponse, include_in_schema=False)
def dev_login(
    payload: DevLoginRequest,
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
) -> VerifyMagicLinkResponse:
    _assert_allowed_origin(request, settings)

    expected_username = os.getenv("DEV_LOGIN_USERNAME", "jemma").strip().lower()
    expected_password = os.getenv("DEV_LOGIN_PASSWORD", "jemma123")
    if payload.username.strip().lower() != expected_username or payload.password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    org = store.get_or_create_org()
    user = store.get_or_create_user(
        org=org,
        email=f"{expected_username}@dev.local",
        role=IdentityRole.OWNER,
    )
    session_issue = store.create_session(
        user=user,
        org=org,
        ip_address=_client_host(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, settings, session_issue.token)
    return VerifyMagicLinkResponse(
        session=_session_response(
            ActiveSession(session=session_issue.session, user=session_issue.user, org=session_issue.org)
        )
    )


# In-process per-IP limiter for guest-session creation (abuse valve; resets on
# process restart, which is acceptable for now — noted in the PR).
_GUEST_CREATE_LIMIT_PER_HOUR = 20
_guest_create_window: dict[str, list[datetime]] = {}
_guest_create_lock = Lock()


def _guest_create_allowed(ip: str | None) -> bool:
    key = ip or "unknown"
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=1)
    with _guest_create_lock:
        window = [t for t in _guest_create_window.get(key, []) if t > cutoff]
        if len(window) >= _GUEST_CREATE_LIMIT_PER_HOUR:
            _guest_create_window[key] = window
            return False
        window.append(now)
        _guest_create_window[key] = window
        return True


@router.post("/auth/guest", response_model=VerifyMagicLinkResponse, include_in_schema=False)
def guest_login(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
) -> VerifyMagicLinkResponse:
    _assert_allowed_origin(request, settings)

    # Idempotent: an existing valid session (guest or real) is returned as-is,
    # so cookie-holders cannot farm fresh budgets and signed-in users are safe.
    existing_token = request.cookies.get(settings.session_cookie_name)
    if existing_token:
        existing = store.get_session(existing_token)
        if existing is not None:
            return VerifyMagicLinkResponse(session=_session_response(existing))

    if not settings.guest_mode_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not _guest_create_allowed(_client_host(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="guest_session_rate_limited",
        )

    # Fresh org per guest: projects are org-scoped, so each guest is isolated.
    guest_id = uuid4().hex[:12]
    org = store.get_or_create_org(slug=f"guest-{guest_id}", name="Guest")
    user = store.get_or_create_user(
        org=org,
        email=f"guest-{guest_id}@guest.lotfile.app",
        role=IdentityRole.GUEST,
    )
    session_issue = store.create_session(
        user=user,
        org=org,
        ip_address=_client_host(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, settings, session_issue.token)
    return VerifyMagicLinkResponse(
        session=_session_response(
            ActiveSession(session=session_issue.session, user=session_issue.user, org=session_issue.org)
        )
    )


@router.get("/auth/session", response_model=SessionResponse)
def get_session(
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> SessionResponse:
    return _session_response(active_session)


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
) -> LogoutResponse:
    _assert_allowed_origin(request, settings)
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        store.revoke_session(token)
    _clear_session_cookie(response, settings)
    return LogoutResponse(status="logged_out")

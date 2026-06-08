"""V3 magic-link auth router."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from draftcheck.config import Settings, get_settings
from draftcheck.domain.identity import (
    ActiveSession,
    DevLogEmailSender,
    EmailSender,
    InMemoryIdentityStore,
    InvalidIdentityInputError,
    MagicLinkTokenConsumedError,
    MagicLinkTokenExpiredError,
    MagicLinkTokenNotFoundError,
    SESSION_TTL,
    require_reviewer,
)


router = APIRouter(tags=["auth"])

_identity_store: InMemoryIdentityStore | None = None
_email_sender = DevLogEmailSender()


class MagicLinkRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    org_slug: str | None = Field(default=None, max_length=80)


class MagicLinkRequestedResponse(BaseModel):
    status: str
    expires_at: datetime


class MagicLinkVerifyRequest(BaseModel):
    token: str = Field(min_length=32)


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


def get_identity_store(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryIdentityStore:
    global _identity_store
    if _identity_store is None:
        _identity_store = InMemoryIdentityStore(
            token_hash_pepper=settings.auth_token_hash_pepper or None,
        )
    return _identity_store


def get_email_sender() -> EmailSender:
    return _email_sender


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


def _magic_link_url(settings: Settings, token: str) -> str:
    query = urlencode({"token": token})
    return f"{settings.frontend_url}/auth/magic-link/verify?{query}"


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


def require_reviewer_session(
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> ActiveSession:
    try:
        require_reviewer(active_session.user.role)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return active_session


@router.post(
    "/auth/magic-link/request",
    response_model=MagicLinkRequestedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> MagicLinkRequestedResponse:
    _assert_allowed_origin(request, settings)
    try:
        issue = store.request_magic_link(
            email=payload.email,
            org_slug=payload.org_slug,
            now=None,
            requested_ip=_client_host(request),
            user_agent=request.headers.get("user-agent"),
        )
    except InvalidIdentityInputError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    email_sender.send_magic_link(
        issue.user.email,
        _magic_link_url(settings, issue.token),
        issue.record.expires_at,
    )
    return MagicLinkRequestedResponse(status="accepted", expires_at=issue.record.expires_at)


@router.post("/auth/magic-link/verify", response_model=VerifyMagicLinkResponse)
def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[InMemoryIdentityStore, Depends(get_identity_store)],
) -> VerifyMagicLinkResponse:
    _assert_allowed_origin(request, settings)
    try:
        user, org, _record = store.consume_magic_link(payload.token)
    except MagicLinkTokenExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Magic link expired") from exc
    except MagicLinkTokenConsumedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Magic link already used") from exc
    except MagicLinkTokenNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid magic link") from exc

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

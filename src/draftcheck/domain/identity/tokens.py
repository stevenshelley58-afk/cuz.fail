"""Random token issuance and hashing for V3 identity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets


TOKEN_BYTES = 32
MAGIC_LINK_TTL = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)


@dataclass(frozen=True)
class IssuedToken:
    token: str
    token_hash: str
    expires_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def generate_raw_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str, *, pepper: str | None = None) -> str:
    if not token:
        raise ValueError("token must not be empty")
    encoded = token.encode("utf-8")
    if pepper:
        return hmac.new(pepper.encode("utf-8"), encoded, hashlib.sha256).hexdigest()
    return hashlib.sha256(encoded).hexdigest()


def token_hash_matches(token: str, expected_hash: str, *, pepper: str | None = None) -> bool:
    return hmac.compare_digest(hash_token(token, pepper=pepper), expected_hash)


def issue_token(
    ttl: timedelta,
    *,
    now: datetime | None = None,
    pepper: str | None = None,
) -> IssuedToken:
    issued_at = ensure_utc(now or utc_now())
    token = generate_raw_token()
    return IssuedToken(
        token=token,
        token_hash=hash_token(token, pepper=pepper),
        expires_at=issued_at + ttl,
    )


def issue_magic_link_token(*, now: datetime | None = None, pepper: str | None = None) -> IssuedToken:
    return issue_token(MAGIC_LINK_TTL, now=now, pepper=pepper)


def issue_session_token(*, now: datetime | None = None, pepper: str | None = None) -> IssuedToken:
    return issue_token(SESSION_TTL, now=now, pepper=pepper)


def is_expired(expires_at: datetime, *, now: datetime | None = None) -> bool:
    return ensure_utc(expires_at) <= ensure_utc(now or utc_now())

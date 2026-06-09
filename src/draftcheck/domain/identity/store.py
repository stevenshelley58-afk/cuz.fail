"""Minimal in-memory identity store for the PR4 auth contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from uuid import UUID, uuid4

from draftcheck.domain.identity.roles import IdentityRole
from draftcheck.domain.identity.tokens import (
    MAGIC_LINK_TTL,
    SESSION_TTL,
    ensure_utc,
    hash_token,
    is_expired,
    issue_magic_link_token,
    issue_session_token,
    utc_now,
)


DEFAULT_ORG_NAME = "DraftCheck WA"
DEFAULT_ORG_SLUG = "draftcheck"


class IdentityError(Exception):
    """Base identity error."""


class InvalidIdentityInputError(IdentityError):
    """Input cannot support an identity operation."""


class MagicLinkTokenNotFoundError(IdentityError):
    """Magic-link token is unknown."""


class MagicLinkTokenExpiredError(IdentityError):
    """Magic-link token is expired."""


class MagicLinkTokenConsumedError(IdentityError):
    """Magic-link token was already consumed."""


@dataclass
class OrgIdentity:
    id: UUID
    name: str
    slug: str
    status: str = "active"
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class UserIdentity:
    id: UUID
    org_id: UUID
    email: str
    role: IdentityRole
    status: str = "active"
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class MagicLinkRecord:
    id: UUID
    org_id: UUID
    user_id: UUID
    email: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    requested_ip: str | None = None
    user_agent: str | None = None


@dataclass
class IdentitySession:
    id: UUID
    org_id: UUID
    user_id: UUID
    token_hash: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class MagicLinkIssue:
    token: str
    record: MagicLinkRecord
    user: UserIdentity
    org: OrgIdentity


@dataclass(frozen=True)
class SessionIssue:
    token: str
    session: IdentitySession
    user: UserIdentity
    org: OrgIdentity


@dataclass(frozen=True)
class ActiveSession:
    session: IdentitySession
    user: UserIdentity
    org: OrgIdentity


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise InvalidIdentityInputError("valid email is required")
    return normalized


def normalize_org_slug(slug: str | None) -> str:
    normalized = (slug or DEFAULT_ORG_SLUG).strip().lower()
    if not normalized:
        raise InvalidIdentityInputError("org slug is required")
    return normalized


class InMemoryIdentityStore:
    """Small test/dev identity store.

    It stores only token hashes. Raw magic-link and session tokens are returned
    to the caller exactly once so callers can send a link or set a cookie.
    """

    def __init__(self, *, token_hash_pepper: str | None = None) -> None:
        self._token_hash_pepper = token_hash_pepper
        self._lock = RLock()
        self.orgs_by_slug: dict[str, OrgIdentity] = {}
        self.users_by_id: dict[UUID, UserIdentity] = {}
        self.users_by_org_email: dict[tuple[UUID, str], UserIdentity] = {}
        self.magic_links_by_hash: dict[str, MagicLinkRecord] = {}
        self.sessions_by_hash: dict[str, IdentitySession] = {}

    def get_or_create_org(
        self,
        *,
        slug: str | None = None,
        name: str = DEFAULT_ORG_NAME,
        now: datetime | None = None,
    ) -> OrgIdentity:
        normalized_slug = normalize_org_slug(slug)
        created_at = ensure_utc(now or utc_now())
        with self._lock:
            org = self.orgs_by_slug.get(normalized_slug)
            if org is not None:
                return org
            org = OrgIdentity(
                id=uuid4(),
                name=name.strip() or DEFAULT_ORG_NAME,
                slug=normalized_slug,
                created_at=created_at,
            )
            self.orgs_by_slug[normalized_slug] = org
            return org

    def get_or_create_user(
        self,
        *,
        org: OrgIdentity,
        email: str,
        role: IdentityRole = IdentityRole.OWNER,
        now: datetime | None = None,
    ) -> UserIdentity:
        normalized_email = normalize_email(email)
        key = (org.id, normalized_email)
        created_at = ensure_utc(now or utc_now())
        with self._lock:
            user = self.users_by_org_email.get(key)
            if user is not None:
                return user
            user = UserIdentity(
                id=uuid4(),
                org_id=org.id,
                email=normalized_email,
                role=role,
                created_at=created_at,
            )
            self.users_by_id[user.id] = user
            self.users_by_org_email[key] = user
            return user

    def request_magic_link(
        self,
        *,
        email: str,
        org_slug: str | None = None,
        org_name: str = DEFAULT_ORG_NAME,
        now: datetime | None = None,
        requested_ip: str | None = None,
        user_agent: str | None = None,
    ) -> MagicLinkIssue:
        issued_at = ensure_utc(now or utc_now())
        normalized_slug = normalize_org_slug(org_slug)
        normalized_email = normalize_email(email)
        with self._lock:
            org = self.orgs_by_slug.get(normalized_slug)
            if org is None:
                raise InvalidIdentityInputError("user is not provisioned for magic-link login")
            user = self.users_by_org_email.get((org.id, normalized_email))
            if user is None:
                raise InvalidIdentityInputError("user is not provisioned for magic-link login")
            issued = issue_magic_link_token(now=issued_at, pepper=self._token_hash_pepper)
            record = MagicLinkRecord(
                id=uuid4(),
                org_id=org.id,
                user_id=user.id,
                email=user.email,
                token_hash=issued.token_hash,
                created_at=issued_at,
                expires_at=issued.expires_at,
                requested_ip=requested_ip,
                user_agent=user_agent,
            )
            self.magic_links_by_hash[record.token_hash] = record
            return MagicLinkIssue(token=issued.token, record=record, user=user, org=org)

    def consume_magic_link(
        self,
        token: str,
        *,
        now: datetime | None = None,
    ) -> tuple[UserIdentity, OrgIdentity, MagicLinkRecord]:
        consumed_at = ensure_utc(now or utc_now())
        token_hash = hash_token(token, pepper=self._token_hash_pepper)
        with self._lock:
            record = self.magic_links_by_hash.get(token_hash)
            if record is None:
                raise MagicLinkTokenNotFoundError("magic-link token not found")
            if record.consumed_at is not None:
                raise MagicLinkTokenConsumedError("magic-link token already consumed")
            if is_expired(record.expires_at, now=consumed_at):
                raise MagicLinkTokenExpiredError("magic-link token expired")
            user = self.users_by_id[record.user_id]
            org = next(org for org in self.orgs_by_slug.values() if org.id == record.org_id)
            record.consumed_at = consumed_at
            return user, org, record

    def create_session(
        self,
        *,
        user: UserIdentity,
        org: OrgIdentity,
        now: datetime | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SessionIssue:
        created_at = ensure_utc(now or utc_now())
        issued = issue_session_token(now=created_at, pepper=self._token_hash_pepper)
        session = IdentitySession(
            id=uuid4(),
            org_id=org.id,
            user_id=user.id,
            token_hash=issued.token_hash,
            created_at=created_at,
            last_seen_at=created_at,
            expires_at=issued.expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        with self._lock:
            self.sessions_by_hash[session.token_hash] = session
        return SessionIssue(token=issued.token, session=session, user=user, org=org)

    def get_session(
        self,
        token: str,
        *,
        now: datetime | None = None,
        slide_expiry: bool = True,
    ) -> ActiveSession | None:
        checked_at = ensure_utc(now or utc_now())
        token_hash = hash_token(token, pepper=self._token_hash_pepper)
        with self._lock:
            session = self.sessions_by_hash.get(token_hash)
            if session is None or session.revoked_at is not None:
                return None
            if is_expired(session.expires_at, now=checked_at):
                return None
            if slide_expiry:
                session.last_seen_at = checked_at
                session.expires_at = checked_at + SESSION_TTL
            user = self.users_by_id[session.user_id]
            org = next(org for org in self.orgs_by_slug.values() if org.id == session.org_id)
            return ActiveSession(session=session, user=user, org=org)

    def revoke_session(self, token: str, *, now: datetime | None = None) -> bool:
        revoked_at = ensure_utc(now or utc_now())
        token_hash = hash_token(token, pepper=self._token_hash_pepper)
        with self._lock:
            session = self.sessions_by_hash.get(token_hash)
            if session is None:
                return False
            session.revoked_at = revoked_at
            return True


__all__ = [
    "MAGIC_LINK_TTL",
    "SESSION_TTL",
    "ActiveSession",
    "DEFAULT_ORG_NAME",
    "DEFAULT_ORG_SLUG",
    "IdentityError",
    "IdentitySession",
    "InMemoryIdentityStore",
    "InvalidIdentityInputError",
    "MagicLinkIssue",
    "MagicLinkRecord",
    "MagicLinkTokenConsumedError",
    "MagicLinkTokenExpiredError",
    "MagicLinkTokenNotFoundError",
    "OrgIdentity",
    "SessionIssue",
    "UserIdentity",
    "normalize_email",
    "normalize_org_slug",
]

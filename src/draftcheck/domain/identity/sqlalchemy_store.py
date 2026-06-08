"""PostgreSQL-backed identity store for the V3 auth contract."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck.db.engine import create_session_factory
from draftcheck.db.models import (
    MagicLinkToken as DbMagicLinkToken,
    Org as DbOrg,
    Session as DbSession,
    User as DbUser,
    UserStatus,
)
from draftcheck.domain.identity.roles import IdentityRole
from draftcheck.domain.identity.store import (
    DEFAULT_ORG_NAME,
    ActiveSession,
    IdentitySession,
    InvalidIdentityInputError,
    MagicLinkIssue,
    MagicLinkRecord,
    MagicLinkTokenConsumedError,
    MagicLinkTokenExpiredError,
    MagicLinkTokenNotFoundError,
    OrgIdentity,
    SessionIssue,
    UserIdentity,
    normalize_email,
    normalize_org_slug,
)
from draftcheck.domain.identity.tokens import (
    SESSION_TTL,
    ensure_utc,
    hash_token,
    is_expired,
    issue_magic_link_token,
    issue_session_token,
    utc_now,
)


class SqlAlchemyIdentityStore:
    """Durable identity store with the same public methods as InMemoryIdentityStore."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        token_hash_pepper: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._token_hash_pepper = token_hash_pepper

    @classmethod
    def from_database_url(
        cls,
        database_url: str,
        *,
        token_hash_pepper: str | None = None,
    ) -> SqlAlchemyIdentityStore:
        return cls(
            create_session_factory(database_url),
            token_hash_pepper=token_hash_pepper,
        )

    def get_or_create_org(
        self,
        *,
        slug: str | None = None,
        name: str = DEFAULT_ORG_NAME,
        now: datetime | None = None,
    ) -> OrgIdentity:
        normalized_slug = normalize_org_slug(slug)
        created_at = ensure_utc(now or utc_now())
        with self._session_factory() as session:
            with session.begin():
                db_org = session.scalar(select(DbOrg).where(DbOrg.slug == normalized_slug))
                if db_org is None:
                    db_org = DbOrg(
                        id=uuid4(),
                        name=name.strip() or DEFAULT_ORG_NAME,
                        slug=normalized_slug,
                        created_at=created_at,
                        updated_at=created_at,
                    )
                    session.add(db_org)
                    session.flush()
                return _org_identity(db_org)

    def get_or_create_user(
        self,
        *,
        org: OrgIdentity,
        email: str,
        role: IdentityRole = IdentityRole.REVIEWER,
        now: datetime | None = None,
    ) -> UserIdentity:
        normalized_email = normalize_email(email)
        created_at = ensure_utc(now or utc_now())
        with self._session_factory() as session:
            with session.begin():
                db_user = session.scalar(
                    select(DbUser).where(
                        DbUser.org_id == org.id,
                        DbUser.email == normalized_email,
                    )
                )
                if db_user is None:
                    db_user = DbUser(
                        id=uuid4(),
                        org_id=org.id,
                        email=normalized_email,
                        role=role,
                        status=UserStatus.ACTIVE,
                        created_at=created_at,
                        updated_at=created_at,
                    )
                    session.add(db_user)
                    session.flush()
                return _user_identity(db_user)

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
        with self._session_factory() as session:
            with session.begin():
                db_org = session.scalar(select(DbOrg).where(DbOrg.slug == normalized_slug))
                if db_org is None:
                    raise InvalidIdentityInputError("user is not provisioned for magic-link login")
                db_user = session.scalar(
                    select(DbUser).where(
                        DbUser.org_id == db_org.id,
                        DbUser.email == normalized_email,
                    )
                )
                if db_user is None or _user_status(db_user) != "active":
                    raise InvalidIdentityInputError("user is not provisioned for magic-link login")

                issued = issue_magic_link_token(now=issued_at, pepper=self._token_hash_pepper)
                db_record = DbMagicLinkToken(
                    id=uuid4(),
                    org_id=db_org.id,
                    user_id=db_user.id,
                    email=db_user.email,
                    token_hash=issued.token_hash,
                    requested_ip=requested_ip,
                    user_agent=user_agent,
                    created_at=issued_at,
                    expires_at=issued.expires_at,
                )
                session.add(db_record)
                session.flush()
                return MagicLinkIssue(
                    token=issued.token,
                    record=_magic_link_record(db_record),
                    user=_user_identity(db_user),
                    org=_org_identity(db_org),
                )

    def consume_magic_link(
        self,
        token: str,
        *,
        now: datetime | None = None,
    ) -> tuple[UserIdentity, OrgIdentity, MagicLinkRecord]:
        consumed_at = ensure_utc(now or utc_now())
        token_hash = hash_token(token, pepper=self._token_hash_pepper)
        with self._session_factory() as session:
            with session.begin():
                db_record = session.scalar(
                    select(DbMagicLinkToken).where(DbMagicLinkToken.token_hash == token_hash)
                )
                if db_record is None:
                    raise MagicLinkTokenNotFoundError("magic-link token not found")
                if db_record.consumed_at is not None:
                    raise MagicLinkTokenConsumedError("magic-link token already consumed")
                if is_expired(db_record.expires_at, now=consumed_at):
                    raise MagicLinkTokenExpiredError("magic-link token expired")

                db_user = session.get(DbUser, db_record.user_id)
                db_org = session.get(DbOrg, db_record.org_id)
                if db_user is None or db_org is None:
                    raise MagicLinkTokenNotFoundError("magic-link token identity not found")
                db_record.consumed_at = consumed_at
                session.flush()
                return (
                    _user_identity(db_user),
                    _org_identity(db_org),
                    _magic_link_record(db_record),
                )

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
        with self._session_factory() as session:
            with session.begin():
                db_session = DbSession(
                    id=uuid4(),
                    org_id=org.id,
                    user_id=user.id,
                    token_hash=issued.token_hash,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    created_at=created_at,
                    last_seen_at=created_at,
                    expires_at=issued.expires_at,
                )
                session.add(db_session)
                session.flush()
                return SessionIssue(
                    token=issued.token,
                    session=_identity_session(db_session),
                    user=user,
                    org=org,
                )

    def get_session(
        self,
        token: str,
        *,
        now: datetime | None = None,
        slide_expiry: bool = True,
    ) -> ActiveSession | None:
        checked_at = ensure_utc(now or utc_now())
        token_hash = hash_token(token, pepper=self._token_hash_pepper)
        with self._session_factory() as session:
            with session.begin():
                db_session = session.scalar(
                    select(DbSession).where(DbSession.token_hash == token_hash)
                )
                if db_session is None or db_session.revoked_at is not None:
                    return None
                if is_expired(db_session.expires_at, now=checked_at):
                    return None
                db_user = session.get(DbUser, db_session.user_id)
                db_org = session.get(DbOrg, db_session.org_id)
                if db_user is None or db_org is None:
                    return None
                if slide_expiry:
                    db_session.last_seen_at = checked_at
                    db_session.expires_at = checked_at + SESSION_TTL
                    session.flush()
                return ActiveSession(
                    session=_identity_session(db_session),
                    user=_user_identity(db_user),
                    org=_org_identity(db_org),
                )

    def revoke_session(self, token: str, *, now: datetime | None = None) -> bool:
        revoked_at = ensure_utc(now or utc_now())
        token_hash = hash_token(token, pepper=self._token_hash_pepper)
        with self._session_factory() as session:
            with session.begin():
                db_session = session.scalar(
                    select(DbSession).where(DbSession.token_hash == token_hash)
                )
                if db_session is None:
                    return False
                db_session.revoked_at = revoked_at
                session.flush()
                return True


def _org_identity(db_org: DbOrg) -> OrgIdentity:
    return OrgIdentity(
        id=db_org.id,
        name=db_org.name,
        slug=db_org.slug,
        status=db_org.status,
        created_at=ensure_utc(db_org.created_at),
    )


def _user_identity(db_user: DbUser) -> UserIdentity:
    return UserIdentity(
        id=db_user.id,
        org_id=db_user.org_id,
        email=db_user.email,
        role=db_user.role,
        status=_user_status(db_user),
        created_at=ensure_utc(db_user.created_at),
    )


def _user_status(db_user: DbUser) -> str:
    return db_user.status.value if isinstance(db_user.status, UserStatus) else str(db_user.status)


def _magic_link_record(db_record: DbMagicLinkToken) -> MagicLinkRecord:
    if db_record.user_id is None:
        raise MagicLinkTokenNotFoundError("magic-link token identity not found")
    return MagicLinkRecord(
        id=db_record.id,
        org_id=db_record.org_id,
        user_id=db_record.user_id,
        email=db_record.email,
        token_hash=db_record.token_hash,
        created_at=ensure_utc(db_record.created_at),
        expires_at=ensure_utc(db_record.expires_at),
        consumed_at=ensure_utc(db_record.consumed_at) if db_record.consumed_at else None,
        requested_ip=db_record.requested_ip,
        user_agent=db_record.user_agent,
    )


def _identity_session(db_session: DbSession) -> IdentitySession:
    return IdentitySession(
        id=db_session.id,
        org_id=db_session.org_id,
        user_id=db_session.user_id,
        token_hash=db_session.token_hash,
        created_at=ensure_utc(db_session.created_at),
        last_seen_at=ensure_utc(db_session.last_seen_at),
        expires_at=ensure_utc(db_session.expires_at),
        revoked_at=ensure_utc(db_session.revoked_at) if db_session.revoked_at else None,
        ip_address=db_session.ip_address,
        user_agent=db_session.user_agent,
    )

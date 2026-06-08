"""Declarative V3 schema models.

Alembic owns schema creation for V3. This module intentionally defines metadata
only and must not create, migrate, or bind tables at import time.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

from draftcheck.domain.identity.roles import IdentityRole

try:
    from pgvector.sqlalchemy import Vector as _PgVector
except ImportError:  # pragma: no cover - exercised only outside the locked env

    class _FallbackPgVector(UserDefinedType):
        cache_ok = True

        def __init__(self, dim: int) -> None:
            self.dim = dim

        def get_col_spec(self, **kw: object) -> str:
            return f"vector({self.dim})"

    PgVector: Any = _FallbackPgVector
else:
    PgVector = _PgVector


GDA2020_SRID = 7844
SOURCE_CHUNK_EMBEDDING_PROVIDER = "api"
SOURCE_CHUNK_EMBEDDING_MODEL = "text-embedding-3-small"
SOURCE_CHUNK_EMBEDDING_DIMENSION = 1536


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base metadata for the new V3 app."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class Geometry(UserDefinedType):
    """Minimal PostGIS geometry type for Alembic metadata without GeoAlchemy."""

    cache_ok = True

    def __init__(self, geometry_type: str, srid: int = GDA2020_SRID) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw: object) -> str:
        return f"geometry({self.geometry_type},{self.srid})"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


role_type = Enum(
    IdentityRole,
    values_callable=lambda roles: [role.value for role in roles],
    native_enum=False,
    create_constraint=True,
    length=16,
    name="identity_role",
)

user_status_type = Enum(
    UserStatus,
    values_callable=lambda statuses: [status.value for status in statuses],
    native_enum=False,
    create_constraint=True,
    length=16,
    name="identity_user_status",
)


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    users: Mapped[list[User]] = relationship(back_populates="org", cascade="all, delete-orphan")
    sessions: Mapped[list[Session]] = relationship(back_populates="org", cascade="all, delete-orphan")
    magic_link_tokens: Mapped[list[MagicLinkToken]] = relationship(
        back_populates="org",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_users_org_email"),
        Index("ix_users_org_role", "org_id", "role"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[IdentityRole] = mapped_column(role_type, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        user_status_type,
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    org: Mapped[Org] = relationship(back_populates="users")
    sessions: Mapped[list[Session]] = relationship(back_populates="user", cascade="all, delete-orphan")
    magic_link_tokens: Mapped[list[MagicLinkToken]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_org_user", "org_id", "user_id"),
        Index("ix_sessions_active_expiry", "expires_at", "revoked_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    org: Mapped[Org] = relationship(back_populates="sessions")
    user: Mapped[User] = relationship(back_populates="sessions")


class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"
    __table_args__ = (
        Index("ix_magic_link_tokens_org_email", "org_id", "email"),
        Index("ix_magic_link_tokens_expiry", "expires_at", "consumed_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    requested_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    org: Mapped[Org] = relationship(back_populates="magic_link_tokens")
    user: Mapped[User | None] = relationship(back_populates="magic_link_tokens")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_org_status", "org_id", "status"),
        Index("ix_projects_created_by", "created_by_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    as_of_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assessment_basis: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Property(Base, TimestampMixin):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("org_id", "project_id", name="uq_properties_org_project"),
        Index("ix_properties_resolution_status", "resolution_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False, default="missing_info")
    address_point_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("address_points.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parcel_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parcels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_crs: Mapped[str] = mapped_column(String(40), nullable=False, default=f"EPSG:{GDA2020_SRID}")
    resolution_metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Proposal(Base, TimestampMixin):
    __tablename__ = "proposals"
    __table_args__ = (
        UniqueConstraint("org_id", "project_id", name="uq_proposals_org_project"),
        Index("ix_proposals_org_type", "org_id", "proposal_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dwelling_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    building_class: Mapped[str | None] = mapped_column(String(40), nullable=True)
    work_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    new_or_existing: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lot_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    primary_street_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Source(Base, TimestampMixin):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("authority", "canonical_url", name="uq_sources_authority_canonical_url"),
        Index("ix_sources_jurisdiction_authority", "jurisdiction", "authority"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(32), nullable=False, default="WA")
    authority: Mapped[str] = mapped_column(String(200), nullable=False)
    local_government: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_type: Mapped[str] = mapped_column(String(80), nullable=False, default="public")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SourceVersion(Base, TimestampMixin):
    __tablename__ = "source_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "sha256", name="uq_source_versions_source_sha256"),
        Index("ix_source_versions_review", "licence_status", "review_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_manifest_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    licence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    licence_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    superseded_by_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SourceChunk(Base, TimestampMixin):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint("source_version_id", "chunk_index", name="uq_source_chunks_version_index"),
        Index("ix_source_chunks_source_version", "source_version_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    section_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_provider: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default=SOURCE_CHUNK_EMBEDDING_PROVIDER,
    )
    embedding_model: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default=SOURCE_CHUNK_EMBEDDING_MODEL,
    )
    embedding_dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=SOURCE_CHUNK_EMBEDDING_DIMENSION,
    )
    embedding: Mapped[list[float]] = mapped_column(
        PgVector(SOURCE_CHUNK_EMBEDDING_DIMENSION),
        nullable=False,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SourceCitation(Base, TimestampMixin):
    __tablename__ = "source_citations"
    __table_args__ = (
        Index("ix_source_citations_chunk", "source_chunk_id"),
        Index("ix_source_citations_version", "source_version_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_chunk_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    citation_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="source_chunk")
    section_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SourceReviewRecord(Base):
    __tablename__ = "source_reviews"
    __table_args__ = (
        Index("ix_source_reviews_org_source", "org_id", "source_id"),
        Index("ix_source_reviews_version", "source_version_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    review_status: Mapped[str] = mapped_column(String(40), nullable=False)
    licence_status: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    decision_metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SourceFetchLog(Base):
    __tablename__ = "source_fetch_log"
    __table_args__ = (
        Index("ix_source_fetch_log_org_source", "org_id", "source_id"),
        Index("ix_source_fetch_log_status", "status", "requested_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fetch_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifacts_sha256", "sha256"),
        Index("ix_artifacts_subject", "subject_type", "subject_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class JobTrace(Base):
    __tablename__ = "job_traces"
    __table_args__ = (
        Index("ix_job_traces_org_status", "org_id", "status"),
        Index("ix_job_traces_source_version", "source_version_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    adapter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    skill_version_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_artifact_ids_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    output_artifact_ids_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    input_artifact_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    output_artifact_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    spend_cap_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spend_cap_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    spend_metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SpendEvent(Base):
    __tablename__ = "spend_events"
    __table_args__ = (
        Index("ix_spend_events_org_created", "org_id", "created_at"),
        Index("ix_spend_events_job_trace", "job_trace_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_trace_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_traces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class SpatialDataset(Base, TimestampMixin):
    __tablename__ = "spatial_datasets"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_spatial_datasets_dataset_version"),
        Index("ix_spatial_datasets_licence_status", "licence_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    licence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    licence_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    source_crs: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(120), nullable=False)
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class LgArea(Base, TimestampMixin):
    __tablename__ = "lg_areas"
    __table_args__ = (
        Index("ix_lg_areas_spatial_dataset", "spatial_dataset_id"),
        Index("ix_lg_areas_name", "name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    lg_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    spatial_dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    geom: Mapped[object] = mapped_column(Geometry("MultiPolygon"), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Parcel(Base, TimestampMixin):
    __tablename__ = "parcels"
    __table_args__ = (
        Index("ix_parcels_spatial_dataset", "spatial_dataset_id"),
        Index("ix_parcels_lot_plan", "lot_plan"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    cadastre_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    lot_plan: Mapped[str | None] = mapped_column(String(160), nullable=True)
    local_government: Mapped[str | None] = mapped_column(String(200), nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    spatial_dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    geom: Mapped[object] = mapped_column(Geometry("MultiPolygon"), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class AddressPoint(Base, TimestampMixin):
    __tablename__ = "address_points"
    __table_args__ = (
        UniqueConstraint("gnaf_pid", name="uq_address_points_gnaf_pid"),
        Index("ix_address_points_parcel", "parcel_id"),
        Index("ix_address_points_spatial_dataset", "spatial_dataset_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    gnaf_pid: Mapped[str] = mapped_column(String(80), nullable=False)
    address_text: Mapped[str] = mapped_column(Text, nullable=False)
    parcel_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parcels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    spatial_dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom: Mapped[object] = mapped_column(Geometry("Point"), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class PlanningFeature(Base, TimestampMixin):
    __tablename__ = "planning_features"
    __table_args__ = (
        Index("ix_planning_features_layer", "layer_type"),
        Index("ix_planning_features_spatial_dataset", "spatial_dataset_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    layer_type: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    spatial_dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    geom: Mapped[object] = mapped_column(Geometry("MultiPolygon"), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class PropertyFact(Base, TimestampMixin):
    __tablename__ = "property_facts"
    __table_args__ = (
        Index("ix_property_facts_org_property", "org_id", "property_id"),
        Index("ix_property_facts_fact_type", "fact_type"),
        Index("ix_property_facts_source_dataset", "source_dataset_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    fact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    method: Mapped[str] = mapped_column(String(80), nullable=False)
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    source_dataset_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spatial_datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    planning_feature_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("planning_features.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parcel_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parcels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")

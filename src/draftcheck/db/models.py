"""Declarative V3 schema models.

Alembic owns schema creation for V3. This module intentionally defines metadata
only and must not create, migrate, or bind tables at import time.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    CheckConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
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


class GuestUsage(Base):
    __tablename__ = "guest_usage"
    __table_args__ = (
        CheckConstraint("feature IN ('address', 'chat')", name="ck_guest_usage_feature"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    feature: Mapped[str] = mapped_column(String(20), primary_key=True)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


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
    lodgement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assessment_basis: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    council_scope: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True,
        comment="Promoted from metadata_json by migration 0007"
    )


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
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_crs: Mapped[str] = mapped_column(String(40), nullable=False, default=f"EPSG:{GDA2020_SRID}")
    resolution_cache_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
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
    secondary_street_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Source(Base, TimestampMixin):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("authority", "canonical_url", name="uq_source_documents_authority_canonical_url"),
        Index("ix_source_documents_jurisdiction_authority", "jurisdiction", "authority"),
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
        # Additive indexes added by Alembic 0010_governance_schema (PR-2).
        Index("ix_source_versions_owner", "owner_user_id"),
        Index("ix_source_versions_review_due", "review_due_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
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

    # Additive columns added by Alembic 0010_governance_schema (PR-2 of the
    # process-control / source-governance feature). The migration is the
    # source of truth for DDL; this class mirrors the column set so the
    # ORM can read and write them. All columns are nullable for backward
    # compatibility with the 83 pre-existing source_versions rows.
    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_required_action: Mapped[str | None] = mapped_column(String(200), nullable=True)


class SourceChunk(Base, TimestampMixin):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint("source_version_id", "chunk_index", name="uq_source_chunks_version_index"),
        Index("ix_source_chunks_source_version", "source_version_id"),
        Index(
            "ix_source_chunks_embedding_metadata_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=text(
                "embedding_provider = 'api' "
                "AND embedding_model = 'text-embedding-3-small' "
                "AND embedding_dimension = 1536",
            ),
        ),
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
        Index("ix_source_reviews_reviewed_by", "reviewed_by_user_id"),
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
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
        ForeignKey("source_documents.id", ondelete="CASCADE"),
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
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=True,
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
        Index("ix_spatial_datasets_approval_status", "approval_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    licence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    licence_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
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
        Index("ix_lg_areas_geom_gist", "geom", postgresql_using="gist"),
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
        Index("ix_parcels_geom_gist", "geom", postgresql_using="gist"),
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
        Index("ix_address_points_geom_gist", "geom", postgresql_using="gist"),
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
        Index("ix_planning_features_geom_gist", "geom", postgresql_using="gist"),
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
        Index("ix_property_facts_spatial_dataset", "spatial_dataset_id"),
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
    spatial_dataset_id: Mapped[UUID | None] = mapped_column(
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


class Clause(Base, TimestampMixin):
    __tablename__ = "clauses"
    __table_args__ = (
        UniqueConstraint("source_version_id", "clause_key", name="uq_clauses_version_key"),
        Index("ix_clauses_source_version_path", "source_version_id", "clause_path"),
        Index("ix_clauses_parent_clause", "parent_clause_id"),
        Index("ix_clauses_disposition", "disposition"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_chunk_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_clause_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    clause_key: Mapped[str] = mapped_column(String(160), nullable=False)
    clause_path: Mapped[str | None] = mapped_column(String(160), nullable=True)
    clause_type: Mapped[str] = mapped_column(String(80), nullable=False, default="clause")
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    section_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    disposition: Mapped[str] = mapped_column(String(40), nullable=False, default="manual_review")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    classification_skill_version_id: Mapped[str | None] = mapped_column(String(160), ForeignKey("skill_versions.id"), nullable=True)


class SkillVersion(Base):
    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("skill_name", "version", name="uq_skill_versions_name_version"),
        Index("ix_skill_versions_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    active_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manifest_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    eval_summary_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class RuleCandidate(Base, TimestampMixin):
    __tablename__ = "rule_candidates"
    __table_args__ = (
        Index("ix_rule_candidates_clause_status", "clause_id", "review_status"),
        Index("ix_rule_candidates_source_version", "source_version_id"),
        Index("ix_rule_candidates_skill_version", "skill_version_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("clauses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_chunk_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    canonical_rule_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(60), nullable=False, default="requirement")
    pathway: Mapped[str] = mapped_column(String(60), nullable=False, default="none")
    # Open-vocab rule decode (2026-06-15): the kind of check, how it can be
    # evaluated, and the structured logic (what it is / what it means / how to
    # query) for non-numeric rules.  See migration 0019.
    check_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    evaluable: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rule_logic_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    operator: Mapped[str | None] = mapped_column(String(40), nullable=True)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    condition_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    extractor_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skill_version_id: Mapped[str | None] = mapped_column(
        String(160),
        ForeignKey("skill_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    extraction_group_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    extraction_pass: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    quote_char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validator_results_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    auto_promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Rule(Base, TimestampMixin):
    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint("source_version_id", "rule_key", name="uq_rules_version_key"),
        Index("ix_rules_lifecycle_status", "lifecycle_status"),
        Index("ix_rules_rule_key", "rule_key"),
        Index("ix_rules_clause", "clause_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    clause_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("clauses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rule_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_key: Mapped[str] = mapped_column(String(160), nullable=False)
    canonical_rule_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(60), nullable=False)
    pathway: Mapped[str] = mapped_column(String(60), nullable=False, default="none")
    lifecycle_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    # Open-vocab rule decode (2026-06-15) — see RuleCandidate / migration 0019.
    check_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    evaluable: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rule_logic_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    operator: Mapped[str | None] = mapped_column(String(40), nullable=True)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    condition_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    extractor_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skill_version_id: Mapped[str | None] = mapped_column(
        String(160),
        ForeignKey("skill_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    superseded_by_rule_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    council_scope: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True,
        comment="Council/LGA this rule applies to; NULL = global (all councils)"
    )
    applicable_zones: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment="Zone codes this rule applies to; NULL = all zones"
    )
    applicable_r_codes: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment="R-codes this rule applies to; NULL = all R-codes"
    )


class RuleClauseLink(Base, TimestampMixin):
    __tablename__ = "rule_clause_links"
    __table_args__ = (
        UniqueConstraint("rule_id", "clause_id", "link_type", name="uq_rule_clause_links_rule_clause_type"),
        Index("ix_rule_clause_links_clause", "clause_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("clauses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    link_type: Mapped[str] = mapped_column(String(60), nullable=False, default="primary")
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class LegalEdge(Base, TimestampMixin):
    __tablename__ = "legal_edges"
    __table_args__ = (
        UniqueConstraint(
            "from_type",
            "from_ref",
            "to_type",
            "to_ref",
            "relation",
            name="uq_legal_edges_from_to_relation",
        ),
        Index("ix_legal_edges_from", "from_type", "from_ref"),
        Index("ix_legal_edges_to", "to_type", "to_ref"),
        Index("ix_legal_edges_relation", "relation"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    from_type: Mapped[str] = mapped_column(String(80), nullable=False)
    from_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    to_type: Mapped[str] = mapped_column(String(80), nullable=False)
    to_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    relation: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class CheckRun(Base):
    __tablename__ = "check_runs"
    __table_args__ = (
        Index("ix_check_runs_org_project", "org_id", "project_id"),
        Index("ix_check_runs_status", "status"),
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
    property_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    proposal_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("proposals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    as_of_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assessment_basis: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    rule_pack_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_version_ids_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class ResolvedRule(Base, TimestampMixin):
    __tablename__ = "resolved_rules"
    __table_args__ = (
        Index("ix_resolved_rules_check_run", "check_run_id"),
        Index("ix_resolved_rules_project_rule", "project_id", "rule_id"),
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
    check_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("check_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rule_key: Mapped[str] = mapped_column(String(160), nullable=False)
    applicability_status: Mapped[str] = mapped_column(String(40), nullable=False)
    pathway: Mapped[str] = mapped_column(String(60), nullable=False, default="none")
    precedence_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assumptions_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    rule_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    selection_trace_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    citations_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)


class CheckResult(Base, TimestampMixin):
    __tablename__ = "check_results"
    __table_args__ = (
        Index("ix_check_results_check_run", "check_run_id"),
        Index("ix_check_results_status", "status"),
        Index("ix_check_results_project_check", "project_id", "check_key"),
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
    check_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("check_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resolved_rule_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("resolved_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    check_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    requirement_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    proposed_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    why_this_applies: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    drawing_evidence_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    decision_trace_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    pathway_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_override_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_org_project", "org_id", "project_id"),
        Index("ix_documents_sha256", "sha256"),
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
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supersedes_document_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    revision_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="uploaded")
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    media_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class DocumentPage(Base, TimestampMixin):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_document_page"),
        Index("ix_document_pages_document", "document_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    rotation_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)
    artifact_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
        Index("ix_document_chunks_document", "document_id"),
        Index("ix_document_chunks_page", "page_id"),
        Index(
            "ix_document_chunks_embedding_metadata_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=text(
                "embedding_provider = 'api' "
                "AND embedding_model = 'text-embedding-3-small' "
                "AND embedding_dimension = 1536",
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    section_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_provider: Mapped[str] = mapped_column(String(120), nullable=False, default=SOURCE_CHUNK_EMBEDDING_PROVIDER)
    embedding_model: Mapped[str] = mapped_column(String(200), nullable=False, default=SOURCE_CHUNK_EMBEDDING_MODEL)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=SOURCE_CHUNK_EMBEDDING_DIMENSION)
    embedding: Mapped[list[float]] = mapped_column(PgVector(SOURCE_CHUNK_EMBEDDING_DIMENSION), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class DocumentFact(Base, TimestampMixin):
    __tablename__ = "document_facts"
    __table_args__ = (
        Index("ix_document_facts_project_kind", "project_id", "fact_kind"),
        Index("ix_document_facts_check_key", "check_key"),
        Index("ix_document_facts_promoted", "promoted_to_measurement", "review_status"),
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
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_chunk_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    artifact_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fact_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    check_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_ref_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    promoted_to_measurement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_review")
    parser_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class RfiItem(Base, TimestampMixin):
    __tablename__ = "rfi_items"
    __table_args__ = (
        Index("ix_rfi_items_project_status", "project_id", "status"),
        Index("ix_rfi_items_check_result", "check_result_id"),
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
    document_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    check_result_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("check_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    item_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    assigned_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class ResponseDraft(Base, TimestampMixin):
    __tablename__ = "response_drafts"
    __table_args__ = (
        Index("ix_response_drafts_project_status", "project_id", "status"),
        Index("ix_response_drafts_rfi_item", "rfi_item_id"),
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
    rfi_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rfi_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_trace_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_traces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    draft_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="rfi_response")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skill_version_id: Mapped[str | None] = mapped_column(
        String(160),
        ForeignKey("skill_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    human_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    edited_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Export(Base):
    __tablename__ = "exports"
    __table_args__ = (
        Index("ix_exports_project_status", "project_id", "status"),
        Index("ix_exports_check_run", "check_run_id"),
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
    check_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("check_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    format: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    sections_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    manifest_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Validation(Base):
    __tablename__ = "validations"
    __table_args__ = (
        Index("ix_validations_export_status", "export_id", "status"),
        Index("ix_validations_check_run_status", "check_run_id", "status"),
        Index("ix_validations_subject", "subject_type", "subject_id"),
        Index("ix_validations_job_trace", "job_trace_id"),
        CheckConstraint(
            "status IN ('passed', 'failed', 'blocked')",
            name="ck_validations_status",
        ),
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
    export_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exports.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    check_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("check_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_trace_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_traces.id", ondelete="SET NULL"),
        nullable=True,
    )
    gate_name: Mapped[str] = mapped_column(String(120), nullable=False)
    validation_type: Mapped[str] = mapped_column(String(80), nullable=False, default="automated_export_gate")
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="blocked")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    manifest_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AgentMemory(Base, TimestampMixin):
    __tablename__ = "agent_memory"
    __table_args__ = (
        UniqueConstraint("org_id", "memory_key", name="uq_agent_memory_org_key"),
        Index("ix_agent_memory_subject", "subject_type", "subject_id"),
        Index("ix_agent_memory_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    memory_key: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    source_job_trace_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_traces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class EvalCase(Base, TimestampMixin):
    __tablename__ = "eval_cases"
    __table_args__ = (
        UniqueConstraint("suite_name", "case_key", name="uq_eval_cases_suite_key"),
        Index("ix_eval_cases_skill_status", "skill_name", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    suite_name: Mapped[str] = mapped_column(String(160), nullable=False)
    case_key: Mapped[str] = mapped_column(String(160), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    input_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    expected_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class EvalRun(Base):
    __tablename__ = "eval_runs"
    __table_args__ = (
        Index("ix_eval_runs_case", "eval_case_id"),
        Index("ix_eval_runs_skill_version", "skill_version_id"),
        Index("ix_eval_runs_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    eval_case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eval_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_version_id: Mapped[str | None] = mapped_column(
        String(160),
        ForeignKey("skill_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_trace_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_traces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    output_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    metrics_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_org_created", "org_id", "created_at"),
        Index("ix_audit_events_subject", "subject_type", "subject_id"),
        Index("ix_audit_events_actor", "actor_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    before_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    after_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class ReviewItem(Base, TimestampMixin):
    __tablename__ = "review_items"
    __table_args__ = (
        Index("ix_review_items_org_status", "org_id", "status"),
        Index("ix_review_items_project_status", "project_id", "status"),
        Index("ix_review_items_subject", "subject_type", "subject_id"),
        # Additive indexes added by Alembic 0010_governance_schema (PR-2).
        # The migration owns the column DDL; the ORM mirrors the schema.
        Index("ix_review_items_severity", "severity"),
        Index("ix_review_items_closure_evidence", "closure_evidence_id"),
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
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)

    # Additive columns added by Alembic 0010_governance_schema (PR-2 of the
    # process-control / source-governance feature). The migration is the
    # source of truth for DDL; this class mirrors the column set so the
    # ORM can read and write them. All columns are nullable for backward
    # compatibility with the 155 pre-existing review_items rows.
    severity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    effectiveness_check_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effectiveness_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_by_finding_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        # use_alter breaks the circular FK with governance_findings
        # (which has linked_capa_id back to review_items). The migration
        # is the source of truth for DDL; this just resolves the cycle
        # at ORM-metadata time so Base.metadata.sorted_tables works.
        ForeignKey("governance_findings.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )


# ---------------------------------------------------------------------------
# Governance schema (PR-2 of process-control implementation map)
# ---------------------------------------------------------------------------
# These classes are the SQLAlchemy metadata for the new governance tables
# added by Alembic migration 0010_governance_schema. They are read-side
# metadata only; the dynamic-table API is forbidden in V3 (see
# tests/test_v3_schema_contract.py for the contract).


class GovernancePipelineStep(Base, TimestampMixin):
    __tablename__ = "governance_pipeline_steps"
    __table_args__ = (
        UniqueConstraint("function_path", name="uq_governance_pipeline_steps_function"),
        Index("ix_governance_pipeline_steps_stage", "stage"),
        Index("ix_governance_pipeline_steps_critical", "is_critical"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    function_path: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_role: Mapped[str] = mapped_column(String(40), nullable=False, default="operator")


class GovernanceRisk(Base, TimestampMixin):
    __tablename__ = "governance_risks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="major")
    default_owner_role: Mapped[str] = mapped_column(String(40), nullable=False, default="operator")


class GovernanceControl(Base, TimestampMixin):
    __tablename__ = "governance_controls"
    __table_args__ = (
        UniqueConstraint("name", name="uq_governance_controls_name"),
        Index("ix_governance_controls_risk", "code"),
        Index("ix_governance_controls_last_tested", "last_tested_at"),
        CheckConstraint(
            "control_type IN ('preventive', 'detective', 'corrective')",
            name="ck_governance_controls_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("governance_risks.code", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    control_type: Mapped[str] = mapped_column(String(40), nullable=False, default="detective")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_function_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    owner_role: Mapped[str] = mapped_column(String(40), nullable=False, default="operator")
    test_frequency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class GovernanceKpi(Base, TimestampMixin):
    __tablename__ = "governance_kpis"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql_template: Mapped[str] = mapped_column(Text, nullable=False)
    warning_threshold: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    breach_threshold: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    review_cadence_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_role: Mapped[str] = mapped_column(String(40), nullable=False, default="operator")


class GovernanceKpiResult(Base):
    __tablename__ = "governance_kpi_results"
    __table_args__ = (
        Index("ix_governance_kpi_results_kpi_period", "kpi_id", text("period_end DESC")),
        Index("ix_governance_kpi_results_status", "status"),
        CheckConstraint(
            "status IN ('green', 'amber', 'red')",
            name="ck_governance_kpi_results_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    kpi_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("governance_kpis.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="green")
    evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
    )


class GovernanceFinding(Base):
    __tablename__ = "governance_findings"
    __table_args__ = (
        Index("ix_governance_findings_status_severity", "status", "severity"),
        Index("ix_governance_findings_org_status", "org_id", "status"),
        Index("ix_governance_findings_proposed_by_job_trace", "proposed_by_job_trace_id"),
        Index("ix_governance_findings_subject", "subject_type", "subject_id"),
        Index("ix_governance_findings_created_at", "created_at"),
        # Partial unique index mirrors the migration:
        # same (subject, risk) cannot be in 'proposed' state twice.
        Index(
            "uq_governance_findings_subject_risk_proposed",
            "subject_type",
            "subject_id",
            "risk_code",
            unique=True,
            postgresql_where=text("status = 'proposed'"),
        ),
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'converted_to_capa', 'superseded')",
            name="ck_governance_findings_status",
        ),
        CheckConstraint(
            "severity IN ('critical', 'major', 'minor')",
            name="ck_governance_findings_severity",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    risk_code: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("governance_risks.code", ondelete="RESTRICT"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="major")
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs_json: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list,
    )
    proposed_remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_by_job_trace_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_traces.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposed_by_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skill_version_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="proposed")
    decision_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_capa_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("review_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
    )


class GovernanceReview(Base):
    __tablename__ = "governance_reviews"
    __table_args__ = (
        Index("ix_governance_reviews_period", "period_start", "period_end"),
        Index("ix_governance_reviews_chair", "chair_user_id"),
        CheckConstraint(
            "review_type IN ('monthly', 'quarterly', 'annual', 'ad_hoc')",
            name="ck_governance_reviews_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    review_type: Mapped[str] = mapped_column(String(40), nullable=False, default="ad_hoc")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    chair_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    decisions_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    open_actions_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_pack_refs_json: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
    )


class TargetManifestEntry(Base, TimestampMixin):
    """Top-down corpus manifest (CORPUS_COMPLETENESS_PLAN Phase 1).

    Also the swarm work queue for acquisition: workers claim rows via
    ``claimed_by`` / ``lease_expires_at`` with FOR UPDATE SKIP LOCKED.
    """

    __tablename__ = "target_manifest"
    __table_args__ = (
        UniqueConstraint(
            "instrument_name",
            "issuing_authority",
            name="uq_target_manifest_instrument_authority",
        ),
        Index("ix_target_manifest_status", "status"),
        Index("ix_target_manifest_category", "category"),
        Index("ix_target_manifest_claim", "status", "lease_expires_at"),
        Index("ix_target_manifest_source_document", "source_document_id"),
        CheckConstraint(
            "status IN ('pending', 'acquired', 'metadata_only', 'blocked', 'out_of_scope')",
            name="ck_target_manifest_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    instrument_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    index_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_version_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    source_document_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class InstrumentAlias(Base, TimestampMixin):
    """Alias → canonical manifest row (CORPUS_COMPLETENESS_PLAN Phase 3)."""

    __tablename__ = "instrument_aliases"
    __table_args__ = (
        UniqueConstraint("alias_text", "match_kind", name="uq_instrument_aliases_alias_kind"),
        Index("ix_instrument_aliases_manifest", "canonical_manifest_id"),
        CheckConstraint(
            "match_kind IN ('exact', 'regex')",
            name="ck_instrument_aliases_match_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    alias_text: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_manifest_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("target_manifest.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="exact")


class AdversarialFinding(Base, TimestampMixin):
    """Adversarial-review findings queue (CORPUS_COMPLETENESS_PLAN Phase 5).

    Attacker pools insert rows; the Defense pool claims ``open`` rows via the
    same lease columns used by ``target_manifest``.
    """

    __tablename__ = "adversarial_findings"
    __table_args__ = (
        Index("ix_adversarial_findings_status_severity", "status", "severity"),
        Index("ix_adversarial_findings_round", "round"),
        Index("ix_adversarial_findings_claim_queue", "status", "lease_expires_at"),
        CheckConstraint(
            "status IN ('open', 'confirmed', 'rejected', 'fixed')",
            name="ck_adversarial_findings_status",
        ),
        CheckConstraint(
            "agent_role IN ('re_extractor', 'prosecutor', 'gap_hunter', 'conflict_prosecutor', 'defense', 'judge')",
            name="ck_adversarial_findings_agent_role",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_role: Mapped[str] = mapped_column(String(40), nullable=False)
    target: Mapped[str] = mapped_column(String(300), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="major")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

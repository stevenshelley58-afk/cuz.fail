"""Create the V3 foundation metadata schema."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_v3_foundation_metadata"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())
UUID = sa.Uuid(as_uuid=True)
NOW = sa.text("now()")
EMPTY_JSON = sa.text("'{}'::jsonb")
EMPTY_ARRAY_JSON = sa.text("'[]'::jsonb")


class Geometry(sa.types.UserDefinedType):
    cache_ok = True

    def __init__(self, geometry_type: str, srid: int = 7844) -> None:
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw: object) -> str:
        return f"geometry({self.geometry_type},{self.srid})"


def _timestamps() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )


def _metadata_json(name: str = "metadata_json") -> sa.Column[Any]:
    return sa.Column(name, JSONB, nullable=False, server_default=EMPTY_JSON)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "orgs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        *_timestamps(),
        sa.UniqueConstraint("slug", name="uq_orgs_slug"),
    )
    op.create_index("ix_orgs_slug", "orgs", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "owner",
                "reviewer",
                name="identity_role",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "disabled",
                name="identity_user_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
            server_default="active",
        ),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "email", name="uq_users_org_email"),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_org_role", "users", ["org_id", "role"])

    op.create_table(
        "sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sessions_org_id", "sessions", ["org_id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_index("ix_sessions_org_user", "sessions", ["org_id", "user_id"])
    op.create_index("ix_sessions_active_expiry", "sessions", ["expires_at", "revoked_at"])

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("requested_ip", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_magic_link_tokens_org_id", "magic_link_tokens", ["org_id"])
    op.create_index("ix_magic_link_tokens_user_id", "magic_link_tokens", ["user_id"])
    op.create_index("ix_magic_link_tokens_token_hash", "magic_link_tokens", ["token_hash"], unique=True)
    op.create_index("ix_magic_link_tokens_org_email", "magic_link_tokens", ["org_id", "email"])
    op.create_index("ix_magic_link_tokens_expiry", "magic_link_tokens", ["expires_at", "consumed_at"])

    op.create_table(
        "projects",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("as_of_date", sa.DateTime(timezone=True)),
        sa.Column("assessment_basis", sa.String(80)),
        _metadata_json(),
        *_timestamps(),
    )
    op.create_index("ix_projects_org_id", "projects", ["org_id"])
    op.create_index("ix_projects_created_by_user_id", "projects", ["created_by_user_id"])
    op.create_index("ix_projects_org_status", "projects", ["org_id", "status"])
    op.create_index("ix_projects_created_by", "projects", ["created_by_user_id"])

    op.create_table(
        "proposals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposal_type", sa.String(80)),
        sa.Column("dwelling_type", sa.String(80)),
        sa.Column("building_class", sa.String(40)),
        sa.Column("work_type", sa.String(80)),
        sa.Column("new_or_existing", sa.String(40)),
        sa.Column("lot_type", sa.String(80)),
        sa.Column("primary_street_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "project_id", name="uq_proposals_org_project"),
    )
    op.create_index("ix_proposals_org_id", "proposals", ["org_id"])
    op.create_index("ix_proposals_project_id", "proposals", ["project_id"])
    op.create_index("ix_proposals_org_type", "proposals", ["org_id", "proposal_type"])

    op.create_table(
        "sources",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("jurisdiction", sa.String(32), nullable=False, server_default="WA"),
        sa.Column("authority", sa.String(200), nullable=False),
        sa.Column("local_government", sa.String(200)),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("access_type", sa.String(80), nullable=False, server_default="public"),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("authority", "canonical_url", name="uq_sources_authority_canonical_url"),
    )
    op.create_index("ix_sources_org_id", "sources", ["org_id"])
    op.create_index("ix_sources_jurisdiction_authority", "sources", ["jurisdiction", "authority"])

    op.create_table(
        "source_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("source_id", UUID, sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_label", sa.String(160)),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_manifest_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("licence", sa.String(200)),
        sa.Column("licence_status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("superseded_by_version_id", UUID, sa.ForeignKey("source_versions.id")),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("source_id", "sha256", name="uq_source_versions_source_sha256"),
    )
    op.create_index("ix_source_versions_source_id", "source_versions", ["source_id"])
    op.create_index("ix_source_versions_sha256", "source_versions", ["sha256"])
    op.create_index("ix_source_versions_superseded_by_version_id", "source_versions", ["superseded_by_version_id"])
    op.create_index("ix_source_versions_review", "source_versions", ["licence_status", "review_status"])

    op.create_table(
        "source_chunks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "source_version_id",
            UUID,
            sa.ForeignKey("source_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(500)),
        sa.Column("section_ref", sa.String(120)),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_provider", sa.String(120), nullable=False, server_default="api"),
        sa.Column("embedding_model", sa.String(200), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="1536"),
        sa.Column("embedding", Vector(1536), nullable=False),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("source_version_id", "chunk_index", name="uq_source_chunks_version_index"),
    )
    op.create_index("ix_source_chunks_source_version_id", "source_chunks", ["source_version_id"])
    op.create_index("ix_source_chunks_source_version", "source_chunks", ["source_version_id"])

    op.create_table(
        "source_citations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "source_chunk_id",
            UUID,
            sa.ForeignKey("source_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_version_id",
            UUID,
            sa.ForeignKey("source_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("citation_kind", sa.String(80), nullable=False, server_default="source_chunk"),
        sa.Column("section_ref", sa.String(120)),
        sa.Column("page_number", sa.Integer()),
        sa.Column("quote", sa.Text()),
        sa.Column("citation_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        *_timestamps(),
    )
    op.create_index("ix_source_citations_source_chunk_id", "source_citations", ["source_chunk_id"])
    op.create_index("ix_source_citations_source_version_id", "source_citations", ["source_version_id"])
    op.create_index("ix_source_citations_chunk", "source_citations", ["source_chunk_id"])
    op.create_index("ix_source_citations_version", "source_citations", ["source_version_id"])

    op.create_table(
        "source_reviews",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", UUID, sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "source_version_id",
            UUID,
            sa.ForeignKey("source_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer_user_id", UUID, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("review_status", sa.String(40), nullable=False),
        sa.Column("licence_status", sa.String(40), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("decision_metadata_json", JSONB, nullable=False, server_default=EMPTY_JSON),
    )
    op.create_index("ix_source_reviews_org_id", "source_reviews", ["org_id"])
    op.create_index("ix_source_reviews_source_id", "source_reviews", ["source_id"])
    op.create_index("ix_source_reviews_source_version_id", "source_reviews", ["source_version_id"])
    op.create_index("ix_source_reviews_reviewer_user_id", "source_reviews", ["reviewer_user_id"])
    op.create_index("ix_source_reviews_org_source", "source_reviews", ["org_id", "source_id"])
    op.create_index("ix_source_reviews_version", "source_reviews", ["source_version_id"])

    op.create_table(
        "source_fetch_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", UUID, sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("requested_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fetch_kind", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        _metadata_json(),
    )
    op.create_index("ix_source_fetch_log_org_id", "source_fetch_log", ["org_id"])
    op.create_index("ix_source_fetch_log_source_id", "source_fetch_log", ["source_id"])
    op.create_index("ix_source_fetch_log_source_version_id", "source_fetch_log", ["source_version_id"])
    op.create_index("ix_source_fetch_log_requested_by_user_id", "source_fetch_log", ["requested_by_user_id"])
    op.create_index("ix_source_fetch_log_org_source", "source_fetch_log", ["org_id", "source_id"])
    op.create_index("ix_source_fetch_log_status", "source_fetch_log", ["status", "requested_at"])

    op.create_table(
        "artifacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="SET NULL")),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", UUID),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("media_type", sa.String(120)),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("parser_name", sa.String(120)),
        sa.Column("parser_version", sa.String(80)),
        _metadata_json(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_artifacts_org_id", "artifacts", ["org_id"])
    op.create_index("ix_artifacts_sha256", "artifacts", ["sha256"])
    op.create_index("ix_artifacts_subject", "artifacts", ["subject_type", "subject_id"])

    op.create_table(
        "job_traces",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.String(160), nullable=False),
        sa.Column("correlation_id", sa.String(120)),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("adapter_name", sa.String(120), nullable=False),
        sa.Column("provider", sa.String(120), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("skill_version_id", sa.String(160), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("input_artifact_ids_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("output_artifact_ids_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("input_artifact_id", UUID, sa.ForeignKey("artifacts.id", ondelete="SET NULL")),
        sa.Column("output_artifact_id", UUID, sa.ForeignKey("artifacts.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("spend_cap_cents", sa.Integer()),
        sa.Column("spend_cap_tokens", sa.Integer()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("cost_usd", sa.Numeric(12, 6)),
        sa.Column("spend_metadata_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_job_traces_org_id", "job_traces", ["org_id"])
    op.create_index("ix_job_traces_job_id", "job_traces", ["job_id"])
    op.create_index("ix_job_traces_correlation_id", "job_traces", ["correlation_id"])
    op.create_index("ix_job_traces_source_version_id", "job_traces", ["source_version_id"])
    op.create_index("ix_job_traces_skill_version_id", "job_traces", ["skill_version_id"])
    op.create_index("ix_job_traces_prompt_hash", "job_traces", ["prompt_hash"])
    op.create_index("ix_job_traces_org_status", "job_traces", ["org_id", "status"])
    op.create_index("ix_job_traces_source_version", "job_traces", ["source_version_id"])

    op.create_table(
        "spend_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_trace_id", UUID, sa.ForeignKey("job_traces.id", ondelete="SET NULL")),
        sa.Column("provider", sa.String(120), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        _metadata_json(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_spend_events_org_id", "spend_events", ["org_id"])
    op.create_index("ix_spend_events_job_trace_id", "spend_events", ["job_trace_id"])
    op.create_index("ix_spend_events_org_created", "spend_events", ["org_id", "created_at"])
    op.create_index("ix_spend_events_job_trace", "spend_events", ["job_trace_id"])

    op.create_table(
        "spatial_datasets",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("dataset_id", sa.String(160), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("provider", sa.String(200), nullable=False),
        sa.Column("licence", sa.String(200)),
        sa.Column("licence_status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("source_crs", sa.String(80), nullable=False),
        sa.Column("version", sa.String(120), nullable=False),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("fetched_at", sa.DateTime(timezone=True)),
        sa.Column("refresh_due", sa.DateTime(timezone=True)),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("dataset_id", "version", name="uq_spatial_datasets_dataset_version"),
    )
    op.create_index("ix_spatial_datasets_source_version_id", "spatial_datasets", ["source_version_id"])
    op.create_index("ix_spatial_datasets_licence_status", "spatial_datasets", ["licence_status"])

    op.create_table(
        "parcels",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("cadastre_id", sa.String(160)),
        sa.Column("lot_plan", sa.String(160)),
        sa.Column("local_government", sa.String(200)),
        sa.Column("area_m2", sa.Float()),
        sa.Column(
            "spatial_dataset_id",
            UUID,
            sa.ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("geom", Geometry("MultiPolygon"), nullable=False),
        _metadata_json(),
        *_timestamps(),
    )
    op.create_index("ix_parcels_cadastre_id", "parcels", ["cadastre_id"])
    op.create_index("ix_parcels_spatial_dataset_id", "parcels", ["spatial_dataset_id"])
    op.create_index("ix_parcels_source_version_id", "parcels", ["source_version_id"])
    op.create_index("ix_parcels_spatial_dataset", "parcels", ["spatial_dataset_id"])
    op.create_index("ix_parcels_lot_plan", "parcels", ["lot_plan"])

    op.create_table(
        "address_points",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("gnaf_pid", sa.String(80), nullable=False),
        sa.Column("address_text", sa.Text(), nullable=False),
        sa.Column("parcel_id", UUID, sa.ForeignKey("parcels.id", ondelete="SET NULL")),
        sa.Column(
            "spatial_dataset_id",
            UUID,
            sa.ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("confidence", sa.Float()),
        sa.Column("geom", Geometry("Point"), nullable=False),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("gnaf_pid", name="uq_address_points_gnaf_pid"),
    )
    op.create_index("ix_address_points_parcel_id", "address_points", ["parcel_id"])
    op.create_index("ix_address_points_spatial_dataset_id", "address_points", ["spatial_dataset_id"])
    op.create_index("ix_address_points_source_version_id", "address_points", ["source_version_id"])
    op.create_index("ix_address_points_parcel", "address_points", ["parcel_id"])
    op.create_index("ix_address_points_spatial_dataset", "address_points", ["spatial_dataset_id"])

    op.create_table(
        "planning_features",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("layer_type", sa.String(80), nullable=False),
        sa.Column("code", sa.String(120)),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column(
            "spatial_dataset_id",
            UUID,
            sa.ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("geom", Geometry("MultiPolygon"), nullable=False),
        _metadata_json(),
        *_timestamps(),
    )
    op.create_index("ix_planning_features_spatial_dataset_id", "planning_features", ["spatial_dataset_id"])
    op.create_index("ix_planning_features_source_version_id", "planning_features", ["source_version_id"])
    op.create_index("ix_planning_features_layer", "planning_features", ["layer_type"])
    op.create_index("ix_planning_features_spatial_dataset", "planning_features", ["spatial_dataset_id"])

    op.create_table(
        "lg_areas",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("lg_code", sa.String(80)),
        sa.Column(
            "spatial_dataset_id",
            UUID,
            sa.ForeignKey("spatial_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("geom", Geometry("MultiPolygon"), nullable=False),
        _metadata_json(),
        *_timestamps(),
    )
    op.create_index("ix_lg_areas_lg_code", "lg_areas", ["lg_code"])
    op.create_index("ix_lg_areas_spatial_dataset_id", "lg_areas", ["spatial_dataset_id"])
    op.create_index("ix_lg_areas_source_version_id", "lg_areas", ["source_version_id"])
    op.create_index("ix_lg_areas_spatial_dataset", "lg_areas", ["spatial_dataset_id"])
    op.create_index("ix_lg_areas_name", "lg_areas", ["name"])

    op.create_table(
        "properties",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("address_text", sa.Text()),
        sa.Column("resolution_status", sa.String(40), nullable=False, server_default="missing_info"),
        sa.Column("address_point_id", UUID, sa.ForeignKey("address_points.id", ondelete="SET NULL")),
        sa.Column("parcel_id", UUID, sa.ForeignKey("parcels.id", ondelete="SET NULL")),
        sa.Column("target_crs", sa.String(40), nullable=False, server_default="EPSG:7844"),
        sa.Column("resolution_metadata_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "project_id", name="uq_properties_org_project"),
    )
    op.create_index("ix_properties_org_id", "properties", ["org_id"])
    op.create_index("ix_properties_project_id", "properties", ["project_id"])
    op.create_index("ix_properties_address_point_id", "properties", ["address_point_id"])
    op.create_index("ix_properties_parcel_id", "properties", ["parcel_id"])
    op.create_index("ix_properties_resolution_status", "properties", ["resolution_status"])

    op.create_table(
        "property_facts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("property_id", UUID, sa.ForeignKey("properties.id", ondelete="CASCADE")),
        sa.Column("fact_type", sa.String(80), nullable=False),
        sa.Column("value_json", JSONB, nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("method", sa.String(80), nullable=False),
        sa.Column("provenance_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("source_dataset_id", UUID, sa.ForeignKey("spatial_datasets.id", ondelete="SET NULL")),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("planning_feature_id", UUID, sa.ForeignKey("planning_features.id", ondelete="SET NULL")),
        sa.Column("parcel_id", UUID, sa.ForeignKey("parcels.id", ondelete="SET NULL")),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("stale_at", sa.DateTime(timezone=True)),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="pending_review"),
        *_timestamps(),
    )
    op.create_index("ix_property_facts_org_id", "property_facts", ["org_id"])
    op.create_index("ix_property_facts_project_id", "property_facts", ["project_id"])
    op.create_index("ix_property_facts_property_id", "property_facts", ["property_id"])
    op.create_index("ix_property_facts_source_dataset_id", "property_facts", ["source_dataset_id"])
    op.create_index("ix_property_facts_source_version_id", "property_facts", ["source_version_id"])
    op.create_index("ix_property_facts_planning_feature_id", "property_facts", ["planning_feature_id"])
    op.create_index("ix_property_facts_parcel_id", "property_facts", ["parcel_id"])
    op.create_index("ix_property_facts_org_property", "property_facts", ["org_id", "property_id"])
    op.create_index("ix_property_facts_fact_type", "property_facts", ["fact_type"])
    op.create_index("ix_property_facts_source_dataset", "property_facts", ["source_dataset_id"])


def downgrade() -> None:
    for table_name in (
        "property_facts",
        "properties",
        "lg_areas",
        "planning_features",
        "address_points",
        "parcels",
        "spatial_datasets",
        "spend_events",
        "job_traces",
        "artifacts",
        "source_fetch_log",
        "source_reviews",
        "source_citations",
        "source_chunks",
        "source_versions",
        "sources",
        "proposals",
        "projects",
        "magic_link_tokens",
        "sessions",
        "users",
        "orgs",
    ):
        op.drop_table(table_name)

"""Complete the V3 target schema.

Revision ID: 0002_v3_complete_target_schema
Revises: 0001_v3_foundation_metadata
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_v3_complete_target_schema"
down_revision: str | None = "0001_v3_foundation_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())
UUID = sa.Uuid(as_uuid=True)
NOW = sa.text("now()")
EMPTY_JSON = sa.text("'{}'::jsonb")
EMPTY_ARRAY_JSON = sa.text("'[]'::jsonb")


def _timestamps() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )


def _metadata_json(name: str = "metadata_json") -> sa.Column[Any]:
    return sa.Column(name, JSONB, nullable=False, server_default=EMPTY_JSON)


def _drop_index_if_exists(index_name: str) -> None:
    op.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))


def _create_search_indexes() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_source_chunks_text_fts
        ON source_chunks
        USING gin (to_tsvector('english', text))
        """,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_source_chunks_embedding_metadata_hnsw
        ON source_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        WHERE embedding_provider = 'api'
          AND embedding_model = 'text-embedding-3-small'
          AND embedding_dimension = 1536
        """,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_text_fts
        ON document_chunks
        USING gin (to_tsvector('english', text))
        """,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_metadata_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        WHERE embedding_provider = 'api'
          AND embedding_model = 'text-embedding-3-small'
          AND embedding_dimension = 1536
        """,
    )


def _create_spatial_indexes() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_lg_areas_geom_gist ON lg_areas USING gist (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_parcels_geom_gist ON parcels USING gist (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_address_points_geom_gist ON address_points USING gist (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_planning_features_geom_gist ON planning_features USING gist (geom)")


def _upgrade_foundation_tables() -> None:
    op.rename_table("sources", "source_documents")
    op.drop_constraint("uq_sources_authority_canonical_url", "source_documents", type_="unique")
    op.create_unique_constraint(
        "uq_source_documents_authority_canonical_url",
        "source_documents",
        ["authority", "canonical_url"],
    )
    op.drop_index("ix_sources_org_id", table_name="source_documents")
    op.drop_index("ix_sources_jurisdiction_authority", table_name="source_documents")
    op.create_index("ix_source_documents_org_id", "source_documents", ["org_id"])
    op.create_index(
        "ix_source_documents_jurisdiction_authority",
        "source_documents",
        ["jurisdiction", "authority"],
    )

    op.add_column("projects", sa.Column("lodgement_date", sa.Date()))
    op.add_column("properties", sa.Column("confidence", sa.Float()))
    op.add_column(
        "properties",
        sa.Column("resolution_cache_json", JSONB, nullable=False, server_default=EMPTY_JSON),
    )
    op.add_column(
        "proposals",
        sa.Column("secondary_street_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("proposals", sa.Column("source", sa.String(80)))
    op.add_column("proposals", sa.Column("confidence", sa.Float()))

    op.drop_index("ix_property_facts_source_dataset", table_name="property_facts")
    op.drop_index("ix_property_facts_source_dataset_id", table_name="property_facts")
    op.alter_column(
        "property_facts",
        "source_dataset_id",
        new_column_name="spatial_dataset_id",
        existing_type=UUID,
        existing_nullable=True,
    )
    op.create_index("ix_property_facts_spatial_dataset_id", "property_facts", ["spatial_dataset_id"])
    op.create_index("ix_property_facts_spatial_dataset", "property_facts", ["spatial_dataset_id"])


def _create_rule_tables() -> None:
    op.create_table(
        "clauses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_chunk_id", UUID, sa.ForeignKey("source_chunks.id", ondelete="SET NULL")),
        sa.Column("parent_clause_id", UUID, sa.ForeignKey("clauses.id", ondelete="SET NULL")),
        sa.Column("clause_key", sa.String(160), nullable=False),
        sa.Column("clause_path", sa.String(160)),
        sa.Column("clause_type", sa.String(80), nullable=False, server_default="clause"),
        sa.Column("title", sa.String(500)),
        sa.Column("section_ref", sa.String(120)),
        sa.Column("disposition", sa.String(40), nullable=False, server_default="manual_review"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text()),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("parser_name", sa.String(120)),
        sa.Column("parser_version", sa.String(80)),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("source_version_id", "clause_key", name="uq_clauses_version_key"),
    )
    op.create_index("ix_clauses_source_version_id", "clauses", ["source_version_id"])
    op.create_index("ix_clauses_source_chunk_id", "clauses", ["source_chunk_id"])
    op.create_index("ix_clauses_parent_clause_id", "clauses", ["parent_clause_id"])
    op.create_index("ix_clauses_source_version_path", "clauses", ["source_version_id", "clause_path"])
    op.create_index("ix_clauses_parent_clause", "clauses", ["parent_clause_id"])
    op.create_index("ix_clauses_disposition", "clauses", ["disposition"])

    op.create_table(
        "skill_versions",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("skill_name", sa.String(160), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("active_from", sa.DateTime(timezone=True)),
        sa.Column("active_to", sa.DateTime(timezone=True)),
        sa.Column("manifest_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("eval_summary_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint("skill_name", "version", name="uq_skill_versions_name_version"),
    )
    op.create_index("ix_skill_versions_content_hash", "skill_versions", ["content_hash"])
    op.create_index("ix_skill_versions_status", "skill_versions", ["status"])

    op.create_table(
        "rule_candidates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="SET NULL")),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clause_id", UUID, sa.ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_chunk_id", UUID, sa.ForeignKey("source_chunks.id", ondelete="SET NULL")),
        sa.Column("rule_key", sa.String(160)),
        sa.Column("rule_type", sa.String(60), nullable=False, server_default="requirement"),
        sa.Column("pathway", sa.String(60), nullable=False, server_default="none"),
        sa.Column("operator", sa.String(40)),
        sa.Column("value_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("unit", sa.String(40)),
        sa.Column("condition_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("extractor_model", sa.String(200)),
        sa.Column("skill_version_id", sa.String(160), sa.ForeignKey("skill_versions.id", ondelete="SET NULL")),
        sa.Column("prompt_hash", sa.String(64)),
        sa.Column("confidence", sa.Float()),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("reviewed_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        _metadata_json(),
        *_timestamps(),
    )
    for name, columns in {
        "ix_rule_candidates_org_id": ["org_id"],
        "ix_rule_candidates_source_version_id": ["source_version_id"],
        "ix_rule_candidates_clause_id": ["clause_id"],
        "ix_rule_candidates_source_chunk_id": ["source_chunk_id"],
        "ix_rule_candidates_skill_version_id": ["skill_version_id"],
        "ix_rule_candidates_prompt_hash": ["prompt_hash"],
        "ix_rule_candidates_reviewed_by_user_id": ["reviewed_by_user_id"],
        "ix_rule_candidates_clause_status": ["clause_id", "review_status"],
        "ix_rule_candidates_source_version": ["source_version_id"],
        "ix_rule_candidates_skill_version": ["skill_version_id"],
    }.items():
        op.create_index(name, "rule_candidates", columns)

    op.create_table(
        "rules",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="SET NULL")),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("clause_id", UUID, sa.ForeignKey("clauses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_id", UUID, sa.ForeignKey("rule_candidates.id", ondelete="SET NULL")),
        sa.Column("rule_key", sa.String(160), nullable=False),
        sa.Column("rule_type", sa.String(60), nullable=False),
        sa.Column("pathway", sa.String(60), nullable=False, server_default="none"),
        sa.Column("lifecycle_status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("operator", sa.String(40)),
        sa.Column("value_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("unit", sa.String(40)),
        sa.Column("condition_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("extractor_model", sa.String(200)),
        sa.Column("skill_version_id", sa.String(160), sa.ForeignKey("skill_versions.id", ondelete="SET NULL")),
        sa.Column("prompt_hash", sa.String(64)),
        sa.Column("approved_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("superseded_by_rule_id", UUID, sa.ForeignKey("rules.id", ondelete="SET NULL")),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("source_version_id", "rule_key", name="uq_rules_version_key"),
    )
    for name, columns in {
        "ix_rules_org_id": ["org_id"],
        "ix_rules_source_version_id": ["source_version_id"],
        "ix_rules_clause_id": ["clause_id"],
        "ix_rules_candidate_id": ["candidate_id"],
        "ix_rules_skill_version_id": ["skill_version_id"],
        "ix_rules_prompt_hash": ["prompt_hash"],
        "ix_rules_approved_by_user_id": ["approved_by_user_id"],
        "ix_rules_superseded_by_rule_id": ["superseded_by_rule_id"],
        "ix_rules_lifecycle_status": ["lifecycle_status"],
        "ix_rules_rule_key": ["rule_key"],
        "ix_rules_clause": ["clause_id"],
    }.items():
        op.create_index(name, "rules", columns)

    op.create_table(
        "rule_clause_links",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("rule_id", UUID, sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clause_id", UUID, sa.ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("link_type", sa.String(60), nullable=False, server_default="primary"),
        sa.Column("quote", sa.Text()),
        sa.Column("confidence", sa.Float()),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("rule_id", "clause_id", "link_type", name="uq_rule_clause_links_rule_clause_type"),
    )
    op.create_index("ix_rule_clause_links_rule_id", "rule_clause_links", ["rule_id"])
    op.create_index("ix_rule_clause_links_clause_id", "rule_clause_links", ["clause_id"])
    op.create_index("ix_rule_clause_links_source_version_id", "rule_clause_links", ["source_version_id"])
    op.create_index("ix_rule_clause_links_clause", "rule_clause_links", ["clause_id"])

    op.create_table(
        "legal_edges",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("from_type", sa.String(80), nullable=False),
        sa.Column("from_ref", sa.String(200), nullable=False),
        sa.Column("to_type", sa.String(80), nullable=False),
        sa.Column("to_ref", sa.String(200), nullable=False),
        sa.Column("relation", sa.String(80), nullable=False),
        sa.Column("evidence_quote", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="pending_review"),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint(
            "from_type",
            "from_ref",
            "to_type",
            "to_ref",
            "relation",
            name="uq_legal_edges_from_to_relation",
        ),
    )
    op.create_index("ix_legal_edges_from", "legal_edges", ["from_type", "from_ref"])
    op.create_index("ix_legal_edges_to", "legal_edges", ["to_type", "to_ref"])
    op.create_index("ix_legal_edges_relation", "legal_edges", ["relation"])


def _create_compliance_tables() -> None:
    op.create_table(
        "check_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", UUID, sa.ForeignKey("properties.id", ondelete="SET NULL")),
        sa.Column("proposal_id", UUID, sa.ForeignKey("proposals.id", ondelete="SET NULL")),
        sa.Column("as_of_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assessment_basis", sa.String(80)),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("rule_pack_hash", sa.String(64)),
        sa.Column("source_version_ids_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("engine_version", sa.String(80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        _metadata_json(),
    )
    for name, columns in {
        "ix_check_runs_org_id": ["org_id"],
        "ix_check_runs_project_id": ["project_id"],
        "ix_check_runs_property_id": ["property_id"],
        "ix_check_runs_proposal_id": ["proposal_id"],
        "ix_check_runs_rule_pack_hash": ["rule_pack_hash"],
        "ix_check_runs_org_project": ["org_id", "project_id"],
        "ix_check_runs_status": ["status"],
    }.items():
        op.create_index(name, "check_runs", columns)

    op.create_table(
        "resolved_rules",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_run_id", UUID, sa.ForeignKey("check_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", UUID, sa.ForeignKey("rules.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rule_key", sa.String(160), nullable=False),
        sa.Column("applicability_status", sa.String(40), nullable=False),
        sa.Column("pathway", sa.String(60), nullable=False, server_default="none"),
        sa.Column("precedence_rank", sa.Integer()),
        sa.Column("assumptions_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("rule_snapshot_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("selection_trace_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("citations_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        *_timestamps(),
    )
    for name, columns in {
        "ix_resolved_rules_org_id": ["org_id"],
        "ix_resolved_rules_project_id": ["project_id"],
        "ix_resolved_rules_check_run_id": ["check_run_id"],
        "ix_resolved_rules_rule_id": ["rule_id"],
        "ix_resolved_rules_check_run": ["check_run_id"],
        "ix_resolved_rules_project_rule": ["project_id", "rule_id"],
    }.items():
        op.create_index(name, "resolved_rules", columns)

    op.create_table(
        "check_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_run_id", UUID, sa.ForeignKey("check_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resolved_rule_id", UUID, sa.ForeignKey("resolved_rules.id", ondelete="SET NULL")),
        sa.Column("check_key", sa.String(160), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("requirement_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("proposed_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("why_this_applies", sa.Text()),
        sa.Column("citations_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("drawing_evidence_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("decision_trace_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("pathway_note", sa.Text()),
        sa.Column("human_review_reason", sa.Text()),
        sa.Column("human_override_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("reviewed_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    for name, columns in {
        "ix_check_results_org_id": ["org_id"],
        "ix_check_results_project_id": ["project_id"],
        "ix_check_results_check_run_id": ["check_run_id"],
        "ix_check_results_resolved_rule_id": ["resolved_rule_id"],
        "ix_check_results_reviewed_by_user_id": ["reviewed_by_user_id"],
        "ix_check_results_check_run": ["check_run_id"],
        "ix_check_results_status": ["status"],
        "ix_check_results_project_check": ["project_id", "check_key"],
    }.items():
        op.create_index(name, "check_results", columns)


def _create_document_tables() -> None:
    op.create_table(
        "documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("supersedes_document_id", UUID, sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("revision_label", sa.String(80)),
        sa.Column("status", sa.String(40), nullable=False, server_default="uploaded"),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("media_type", sa.String(120)),
        sa.Column("size_bytes", sa.BigInteger()),
        _metadata_json(),
        *_timestamps(),
    )
    for name, columns in {
        "ix_documents_org_id": ["org_id"],
        "ix_documents_project_id": ["project_id"],
        "ix_documents_uploaded_by_user_id": ["uploaded_by_user_id"],
        "ix_documents_supersedes_document_id": ["supersedes_document_id"],
        "ix_documents_org_project": ["org_id", "project_id"],
        "ix_documents_sha256": ["sha256"],
    }.items():
        op.create_index(name, "documents", columns)

    op.create_table(
        "document_pages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float()),
        sa.Column("height", sa.Float()),
        sa.Column("rotation_degrees", sa.Float()),
        sa.Column("artifact_id", UUID, sa.ForeignKey("artifacts.id", ondelete="SET NULL")),
        sa.Column("text", sa.Text()),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_pages_document_page"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])
    op.create_index("ix_document_pages_artifact_id", "document_pages", ["artifact_id"])
    op.create_index("ix_document_pages_document", "document_pages", ["document_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID, sa.ForeignKey("document_pages.id", ondelete="CASCADE")),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(500)),
        sa.Column("section_ref", sa.String(120)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_provider", sa.String(120), nullable=False, server_default="api"),
        sa.Column("embedding_model", sa.String(200), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="1536"),
        sa.Column("embedding", Vector(1536), nullable=False),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_page_id", "document_chunks", ["page_id"])
    op.create_index("ix_document_chunks_document", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_page", "document_chunks", ["page_id"])

    op.create_table(
        "document_facts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID, sa.ForeignKey("document_pages.id", ondelete="SET NULL")),
        sa.Column("document_chunk_id", UUID, sa.ForeignKey("document_chunks.id", ondelete="SET NULL")),
        sa.Column("artifact_id", UUID, sa.ForeignKey("artifacts.id", ondelete="SET NULL")),
        sa.Column("fact_kind", sa.String(80), nullable=False),
        sa.Column("check_key", sa.String(160)),
        sa.Column("value_json", JSONB, nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("evidence_ref_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("promoted_to_measurement", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_status", sa.String(40), nullable=False, server_default="pending_review"),
        sa.Column("parser_name", sa.String(120)),
        sa.Column("parser_version", sa.String(80)),
        _metadata_json(),
        *_timestamps(),
    )
    for name, columns in {
        "ix_document_facts_org_id": ["org_id"],
        "ix_document_facts_project_id": ["project_id"],
        "ix_document_facts_document_id": ["document_id"],
        "ix_document_facts_page_id": ["page_id"],
        "ix_document_facts_document_chunk_id": ["document_chunk_id"],
        "ix_document_facts_artifact_id": ["artifact_id"],
        "ix_document_facts_project_kind": ["project_id", "fact_kind"],
        "ix_document_facts_check_key": ["check_key"],
        "ix_document_facts_promoted": ["promoted_to_measurement", "review_status"],
    }.items():
        op.create_index(name, "document_facts", columns)


def _create_output_agent_tables() -> None:
    op.create_table(
        "rfi_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("check_result_id", UUID, sa.ForeignKey("check_results.id", ondelete="SET NULL")),
        sa.Column("item_key", sa.String(160)),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(40), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column("assigned_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("source_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        _metadata_json(),
        *_timestamps(),
    )
    for name, columns in {
        "ix_rfi_items_org_id": ["org_id"],
        "ix_rfi_items_project_id": ["project_id"],
        "ix_rfi_items_document_id": ["document_id"],
        "ix_rfi_items_check_result_id": ["check_result_id"],
        "ix_rfi_items_assigned_user_id": ["assigned_user_id"],
        "ix_rfi_items_project_status": ["project_id", "status"],
        "ix_rfi_items_check_result": ["check_result_id"],
    }.items():
        op.create_index(name, "rfi_items", columns)

    op.create_table(
        "response_drafts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rfi_item_id", UUID, sa.ForeignKey("rfi_items.id", ondelete="SET NULL")),
        sa.Column("job_trace_id", UUID, sa.ForeignKey("job_traces.id", ondelete="SET NULL")),
        sa.Column("draft_kind", sa.String(80), nullable=False, server_default="rfi_response"),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("model", sa.String(200)),
        sa.Column("skill_version_id", sa.String(160), sa.ForeignKey("skill_versions.id", ondelete="SET NULL")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("human_edited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("edited_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        _metadata_json(),
        *_timestamps(),
    )
    for name, columns in {
        "ix_response_drafts_org_id": ["org_id"],
        "ix_response_drafts_project_id": ["project_id"],
        "ix_response_drafts_rfi_item_id": ["rfi_item_id"],
        "ix_response_drafts_job_trace_id": ["job_trace_id"],
        "ix_response_drafts_skill_version_id": ["skill_version_id"],
        "ix_response_drafts_edited_by_user_id": ["edited_by_user_id"],
        "ix_response_drafts_project_status": ["project_id", "status"],
        "ix_response_drafts_rfi_item": ["rfi_item_id"],
    }.items():
        op.create_index(name, "response_drafts", columns)

    op.create_table(
        "exports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_run_id", UUID, sa.ForeignKey("check_runs.id", ondelete="SET NULL")),
        sa.Column("requested_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("format", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("sections_json", JSONB, nullable=False, server_default=EMPTY_ARRAY_JSON),
        sa.Column("manifest_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("storage_path", sa.Text()),
        sa.Column("sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        _metadata_json(),
    )
    for name, columns in {
        "ix_exports_org_id": ["org_id"],
        "ix_exports_project_id": ["project_id"],
        "ix_exports_check_run_id": ["check_run_id"],
        "ix_exports_requested_by_user_id": ["requested_by_user_id"],
        "ix_exports_sha256": ["sha256"],
        "ix_exports_project_status": ["project_id", "status"],
        "ix_exports_check_run": ["check_run_id"],
    }.items():
        op.create_index(name, "exports", columns)

    op.create_table(
        "signoffs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("export_id", UUID, sa.ForeignKey("exports.id", ondelete="SET NULL")),
        sa.Column("check_run_id", UUID, sa.ForeignKey("check_runs.id", ondelete="SET NULL")),
        sa.Column("signer_user_id", UUID, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("signoff_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="signed"),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        _metadata_json(),
    )
    for name, columns in {
        "ix_signoffs_org_id": ["org_id"],
        "ix_signoffs_project_id": ["project_id"],
        "ix_signoffs_export_id": ["export_id"],
        "ix_signoffs_check_run_id": ["check_run_id"],
        "ix_signoffs_signer_user_id": ["signer_user_id"],
        "ix_signoffs_project": ["project_id"],
        "ix_signoffs_export": ["export_id"],
    }.items():
        op.create_index(name, "signoffs", columns)

    op.create_table(
        "agent_memory",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE")),
        sa.Column("memory_key", sa.String(200), nullable=False),
        sa.Column("subject_type", sa.String(80)),
        sa.Column("subject_id", UUID),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("source_job_trace_id", UUID, sa.ForeignKey("job_traces.id", ondelete="SET NULL")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "memory_key", name="uq_agent_memory_org_key"),
    )
    op.create_index("ix_agent_memory_org_id", "agent_memory", ["org_id"])
    op.create_index("ix_agent_memory_source_job_trace_id", "agent_memory", ["source_job_trace_id"])
    op.create_index("ix_agent_memory_subject", "agent_memory", ["subject_type", "subject_id"])
    op.create_index("ix_agent_memory_status", "agent_memory", ["status"])

    op.create_table(
        "eval_cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("suite_name", sa.String(160), nullable=False),
        sa.Column("case_key", sa.String(160), nullable=False),
        sa.Column("skill_name", sa.String(160), nullable=False),
        sa.Column("source_version_id", UUID, sa.ForeignKey("source_versions.id", ondelete="SET NULL")),
        sa.Column("input_json", JSONB, nullable=False),
        sa.Column("expected_json", JSONB, nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        _metadata_json(),
        *_timestamps(),
        sa.UniqueConstraint("suite_name", "case_key", name="uq_eval_cases_suite_key"),
    )
    op.create_index("ix_eval_cases_source_version_id", "eval_cases", ["source_version_id"])
    op.create_index("ix_eval_cases_skill_status", "eval_cases", ["skill_name", "status"])

    op.create_table(
        "eval_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("eval_case_id", UUID, sa.ForeignKey("eval_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_version_id", sa.String(160), sa.ForeignKey("skill_versions.id", ondelete="SET NULL")),
        sa.Column("job_trace_id", UUID, sa.ForeignKey("job_traces.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("score", sa.Numeric(8, 4)),
        sa.Column("output_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("metrics_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_eval_runs_eval_case_id", "eval_runs", ["eval_case_id"])
    op.create_index("ix_eval_runs_skill_version_id", "eval_runs", ["skill_version_id"])
    op.create_index("ix_eval_runs_job_trace_id", "eval_runs", ["job_trace_id"])
    op.create_index("ix_eval_runs_case", "eval_runs", ["eval_case_id"])
    op.create_index("ix_eval_runs_skill_version", "eval_runs", ["skill_version_id"])
    op.create_index("ix_eval_runs_status", "eval_runs", ["status"])

    op.create_table(
        "audit_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="SET NULL")),
        sa.Column("actor_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", UUID),
        sa.Column("request_id", sa.String(120)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("before_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("after_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        _metadata_json(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_audit_events_org_id", "audit_events", ["org_id"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])
    op.create_index("ix_audit_events_org_created", "audit_events", ["org_id", "created_at"])
    op.create_index("ix_audit_events_subject", "audit_events", ["subject_type", "subject_id"])
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_user_id"])

    op.create_table(
        "review_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", UUID),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assigned_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("source_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        _metadata_json(),
        *_timestamps(),
    )
    op.create_index("ix_review_items_org_id", "review_items", ["org_id"])
    op.create_index("ix_review_items_project_id", "review_items", ["project_id"])
    op.create_index("ix_review_items_assigned_user_id", "review_items", ["assigned_user_id"])
    op.create_index("ix_review_items_resolved_by_user_id", "review_items", ["resolved_by_user_id"])
    op.create_index("ix_review_items_org_status", "review_items", ["org_id", "status"])
    op.create_index("ix_review_items_project_status", "review_items", ["project_id", "status"])
    op.create_index("ix_review_items_subject", "review_items", ["subject_type", "subject_id"])


def upgrade() -> None:
    _upgrade_foundation_tables()
    _create_rule_tables()
    _create_compliance_tables()
    _create_document_tables()
    _create_output_agent_tables()
    _create_search_indexes()
    _create_spatial_indexes()


def downgrade() -> None:
    for index_name in (
        "ix_document_chunks_embedding_metadata_hnsw",
        "ix_document_chunks_text_fts",
        "ix_source_chunks_embedding_metadata_hnsw",
        "ix_source_chunks_text_fts",
        "ix_planning_features_geom_gist",
        "ix_address_points_geom_gist",
        "ix_parcels_geom_gist",
        "ix_lg_areas_geom_gist",
    ):
        _drop_index_if_exists(index_name)

    for table_name in (
        "review_items",
        "audit_events",
        "eval_runs",
        "eval_cases",
        "agent_memory",
        "signoffs",
        "exports",
        "response_drafts",
        "rfi_items",
        "document_facts",
        "document_chunks",
        "document_pages",
        "documents",
        "check_results",
        "resolved_rules",
        "check_runs",
        "legal_edges",
        "rule_clause_links",
        "rules",
        "rule_candidates",
        "skill_versions",
        "clauses",
    ):
        op.drop_table(table_name)

    op.drop_index("ix_property_facts_spatial_dataset", table_name="property_facts")
    op.drop_index("ix_property_facts_spatial_dataset_id", table_name="property_facts")
    op.alter_column(
        "property_facts",
        "spatial_dataset_id",
        new_column_name="source_dataset_id",
        existing_type=UUID,
        existing_nullable=True,
    )
    op.create_index("ix_property_facts_source_dataset_id", "property_facts", ["source_dataset_id"])
    op.create_index("ix_property_facts_source_dataset", "property_facts", ["source_dataset_id"])

    op.drop_column("proposals", "confidence")
    op.drop_column("proposals", "source")
    op.drop_column("proposals", "secondary_street_confirmed")
    op.drop_column("properties", "resolution_cache_json")
    op.drop_column("properties", "confidence")
    op.drop_column("projects", "lodgement_date")

    op.drop_index("ix_source_documents_jurisdiction_authority", table_name="source_documents")
    op.drop_index("ix_source_documents_org_id", table_name="source_documents")
    op.drop_constraint("uq_source_documents_authority_canonical_url", "source_documents", type_="unique")
    op.create_unique_constraint(
        "uq_sources_authority_canonical_url",
        "source_documents",
        ["authority", "canonical_url"],
    )
    op.rename_table("source_documents", "sources")
    op.create_index("ix_sources_org_id", "sources", ["org_id"])
    op.create_index("ix_sources_jurisdiction_authority", "sources", ["jurisdiction", "authority"])

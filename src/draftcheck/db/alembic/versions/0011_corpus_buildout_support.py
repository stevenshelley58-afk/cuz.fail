"""Corpus build-out support tables — WP1 of the DB build-out plan.

Adds the three tables required by docs/CORPUS_COMPLETENESS_PLAN.md:

- ``target_manifest`` (Phase 1) — top-down manifest of every instrument the
  corpus must contain; doubles as the swarm work queue for WP3–WP5, hence the
  ``claimed_by`` / ``lease_expires_at`` lease columns.
- ``instrument_aliases`` (Phase 3) — alias table used to resolve extracted
  citations ("the R-Codes", "SPP 7.3") to one canonical manifest row.
- ``adversarial_findings`` (Phase 5) — single findings table written by the
  adversarial agent pools; also a swarm queue (Defense pool claims ``open``
  rows), hence the same lease columns.

Revision ID: 0011_corpus_buildout_support
Revises: 0010_governance_schema
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0011_corpus_buildout_support"
down_revision: str | None = "0010_governance_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())
UUID = sa.Uuid(as_uuid=True)
NOW = sa.text("now()")
EMPTY_JSON = sa.text("'{}'::jsonb")


def upgrade() -> None:
    # 1. target_manifest
    op.create_table(
        "target_manifest",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instrument_name", sa.String(500), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("issuing_authority", sa.String(200), nullable=False, server_default=""),
        sa.Column("index_source_url", sa.Text, nullable=True),
        sa.Column("canonical_url", sa.Text, nullable=True),
        sa.Column("expected_version_hint", sa.String(200), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column(
            "source_document_id",
            UUID,
            sa.ForeignKey("source_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("claimed_by", sa.String(120), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "status IN ('pending', 'acquired', 'metadata_only', 'blocked', 'out_of_scope')",
            name="ck_target_manifest_status",
        ),
    )
    op.create_unique_constraint(
        "uq_target_manifest_instrument_authority",
        "target_manifest",
        ["instrument_name", "issuing_authority"],
    )
    op.create_index("ix_target_manifest_status", "target_manifest", ["status"])
    op.create_index("ix_target_manifest_category", "target_manifest", ["category"])
    op.create_index(
        "ix_target_manifest_claim",
        "target_manifest",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "ix_target_manifest_source_document",
        "target_manifest",
        ["source_document_id"],
    )

    # 2. instrument_aliases
    op.create_table(
        "instrument_aliases",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alias_text", sa.Text, nullable=False),
        sa.Column(
            "canonical_manifest_id",
            UUID,
            sa.ForeignKey("target_manifest.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_kind", sa.String(16), nullable=False, server_default="exact"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "match_kind IN ('exact', 'regex')",
            name="ck_instrument_aliases_match_kind",
        ),
    )
    op.create_unique_constraint(
        "uq_instrument_aliases_alias_kind",
        "instrument_aliases",
        ["alias_text", "match_kind"],
    )
    op.create_index(
        "ix_instrument_aliases_manifest",
        "instrument_aliases",
        ["canonical_manifest_id"],
    )

    # 3. adversarial_findings
    op.create_table(
        "adversarial_findings",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("round", sa.Integer, nullable=False),
        sa.Column("agent_role", sa.String(40), nullable=False),
        sa.Column("target", sa.String(300), nullable=False),
        sa.Column("claim", sa.Text, nullable=False),
        sa.Column("evidence_quote", sa.Text, nullable=True),
        sa.Column("severity", sa.String(40), nullable=False, server_default="major"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column("claimed_by", sa.String(120), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "status IN ('open', 'confirmed', 'rejected', 'fixed')",
            name="ck_adversarial_findings_status",
        ),
        sa.CheckConstraint(
            "agent_role IN ('re_extractor', 'prosecutor', 'gap_hunter', 'conflict_prosecutor', 'defense', 'judge')",
            name="ck_adversarial_findings_agent_role",
        ),
    )
    op.create_index(
        "ix_adversarial_findings_status_severity",
        "adversarial_findings",
        ["status", "severity"],
    )
    op.create_index("ix_adversarial_findings_round", "adversarial_findings", ["round"])
    op.create_index(
        "ix_adversarial_findings_claim_queue",
        "adversarial_findings",
        ["status", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_table("adversarial_findings")
    op.drop_table("instrument_aliases")
    op.drop_table("target_manifest")

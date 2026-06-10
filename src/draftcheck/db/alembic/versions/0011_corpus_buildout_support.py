"""Corpus build-out support tables — WP1 of the DB build-out plan.

Adds the three tables required by docs/CORPUS_COMPLETENESS_PLAN.md:

- ``target_manifest`` (Phase 1) — one row per instrument version the corpus
  must contain; populated from authoritative index scrapes.
- ``instrument_aliases`` (Phase 3) — alias resolution so "the R-Codes",
  "SPP 7.3" and "Residential Design Codes Volume 1" map to one manifest row.
- ``adversarial_findings`` (Phase 5) — findings from the adversarial agent
  rounds (re-extractor, prosecutor, gap hunter, conflict prosecutor, defense).

Alembic owns schema creation for V3 (enforced by
tests/test_v3_schema_contract.py). This revision is the schema authority
for WP1.

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


def upgrade() -> None:
    op.create_table(
        "target_manifest",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instrument_name", sa.String(500), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("issuing_authority", sa.String(200), nullable=False),
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "status IN ('pending', 'acquired', 'metadata_only', 'blocked', 'out_of_scope')",
            name="ck_target_manifest_status",
        ),
        sa.UniqueConstraint(
            "instrument_name",
            "expected_version_hint",
            name="uq_target_manifest_instrument_version",
        ),
    )
    op.create_index("ix_target_manifest_status", "target_manifest", ["status"])
    op.create_index("ix_target_manifest_category", "target_manifest", ["category"])
    op.create_index(
        "ix_target_manifest_source_document",
        "target_manifest",
        ["source_document_id"],
    )

    op.create_table(
        "instrument_aliases",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alias_text", sa.String(500), nullable=False),
        sa.Column(
            "canonical_manifest_id",
            UUID,
            sa.ForeignKey("target_manifest.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_kind", sa.String(20), nullable=False, server_default="exact"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "match_kind IN ('exact', 'regex')",
            name="ck_instrument_aliases_match_kind",
        ),
        sa.UniqueConstraint(
            "alias_text",
            "canonical_manifest_id",
            name="uq_instrument_aliases_alias_manifest",
        ),
    )
    op.create_index(
        "ix_instrument_aliases_manifest",
        "instrument_aliases",
        ["canonical_manifest_id"],
    )

    op.create_table(
        "adversarial_findings",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("round", sa.Integer, nullable=False),
        sa.Column("agent_role", sa.String(40), nullable=False),
        sa.Column("target", sa.Text, nullable=False),
        sa.Column("claim", sa.Text, nullable=False),
        sa.Column("evidence_quote", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="minor"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "agent_role IN ('re_extractor', 'prosecutor', 'gap_hunter', "
            "'conflict_prosecutor', 'defense')",
            name="ck_adversarial_findings_agent_role",
        ),
        sa.CheckConstraint(
            "severity IN ('critical', 'major', 'minor')",
            name="ck_adversarial_findings_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'confirmed', 'rejected', 'fixed')",
            name="ck_adversarial_findings_status",
        ),
    )
    op.create_index("ix_adversarial_findings_status", "adversarial_findings", ["status"])
    op.create_index(
        "ix_adversarial_findings_round_role",
        "adversarial_findings",
        ["round", "agent_role"],
    )


def downgrade() -> None:
    op.drop_index("ix_adversarial_findings_round_role", table_name="adversarial_findings")
    op.drop_index("ix_adversarial_findings_status", table_name="adversarial_findings")
    op.drop_table("adversarial_findings")

    op.drop_index("ix_instrument_aliases_manifest", table_name="instrument_aliases")
    op.drop_table("instrument_aliases")

    op.drop_index("ix_target_manifest_source_document", table_name="target_manifest")
    op.drop_index("ix_target_manifest_category", table_name="target_manifest")
    op.drop_index("ix_target_manifest_status", table_name="target_manifest")
    op.drop_table("target_manifest")

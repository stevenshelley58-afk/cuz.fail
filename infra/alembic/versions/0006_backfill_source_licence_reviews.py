"""Backfill missing source licence reviews.

Revision ID: 0006_backfill_source_licence_reviews
Revises: 0005_source_acceptance_gate
Create Date: 2026-06-06
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0006_backfill_source_licence_reviews"
down_revision = "0005_source_acceptance_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table("source_versions") or not _has_table("source_licence_reviews"):
        return

    rows = bind.execute(
        sa.text(
            """
            select
                sv.id as source_version_id,
                sv.source_document_id as source_document_id,
                sv.parse_status as parse_status,
                sd.title as title,
                sd.authority as authority,
                sd.source_type as source_type,
                sd.canonical_url as canonical_url,
                sd.access_type as access_type
            from source_versions sv
            join source_documents sd on sd.id = sv.source_document_id
            where not exists (
                select 1
                from source_licence_reviews slr
                where slr.source_version_id = sv.id
            )
            """
        )
    ).mappings()

    now = datetime.now(UTC).replace(tzinfo=None)
    for row in rows:
        access_type = str(row["access_type"] or "").lower().strip()
        parse_status = str(row["parse_status"] or "").lower().strip()
        is_metadata_only = parse_status == "metadata_only"
        is_standards = _is_standards_row(row)
        approved = access_type in {"public", "open"} and parse_status in {"ok", "partial"} and not is_standards
        reason = None
        if is_metadata_only or is_standards:
            reason = "metadata-only source cannot support answers"
        elif access_type not in {"public", "open"}:
            reason = f"access_type={row['access_type']} requires review before supporting answers"
        elif parse_status not in {"ok", "partial"}:
            reason = f"parse_status={row['parse_status']} cannot support answers"

        bind.execute(
            sa.text(
                """
                insert into source_licence_reviews (
                    id,
                    source_document_id,
                    source_version_id,
                    licence_url,
                    allowed_use,
                    allowed_storage,
                    allowed_redistribution,
                    allowed_ai_processing,
                    restricted_reason,
                    reviewed_by,
                    reviewed_at,
                    review_status,
                    created_at,
                    updated_at
                )
                values (
                    :id,
                    :source_document_id,
                    :source_version_id,
                    :licence_url,
                    :allowed_use,
                    :allowed_storage,
                    :allowed_redistribution,
                    :allowed_ai_processing,
                    :restricted_reason,
                    :reviewed_by,
                    :reviewed_at,
                    :review_status,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": f"slr_{uuid4().hex}",
                "source_document_id": row["source_document_id"],
                "source_version_id": row["source_version_id"],
                "licence_url": row["canonical_url"],
                "allowed_use": approved,
                "allowed_storage": approved,
                "allowed_redistribution": False,
                "allowed_ai_processing": approved,
                "restricted_reason": reason,
                "reviewed_by": "system-backfill",
                "reviewed_at": now,
                "review_status": "approved" if approved else "restricted",
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    if _has_table("source_licence_reviews"):
        op.execute("delete from source_licence_reviews where reviewed_by = 'system-backfill'")


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _is_standards_row(row: sa.engine.RowMapping) -> bool:
    haystack = " ".join(
        str(row[key] or "")
        for key in ("title", "authority", "source_type", "canonical_url")
    ).lower()
    return "standards australia" in haystack or "standards.org.au" in haystack

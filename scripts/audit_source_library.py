from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from sqlalchemy import func, select, text

from draftcheck_compliance.rule_validation import APPROVED_RULE_STATUSES
from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.models import ReviewQueueItem, RuleRow, SourceChunk, SourceDocument, SourceVersion
from draftcheck_core.source_support import source_version_can_support_citable_retrieval
from draftcheck_retrieval.service import RetrievalService


PROBE_QUERIES = [
    "What is the site cover requirement for R30?",
    "What is the open space requirement for an R30 single house?",
    "What is the outdoor living area requirement for an R30 single house?",
    "How do I demonstrate solar access?",
    "What are the solar access requirements?",
    "What information should be provided for R-Codes Volume 2 design review?",
    "What materials are needed for a development application under R-Codes Volume 2?",
    "How should I orient apartments for natural ventilation?",
    "bushfire prone areas BAL report",
    "NCC condensation buildings",
    "livable housing design handbook",
    "Australian Standard AS 3959 full text requirements",
]


def main() -> None:
    args = _parse_args()
    init_database()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        lines = _build_report(db)

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(output_path))


def _build_report(db) -> list[str]:
    source_count = db.scalar(select(func.count()).select_from(SourceDocument)) or 0
    version_count = db.scalar(select(func.count()).select_from(SourceVersion)) or 0
    active_version_count = db.scalar(
        select(func.count()).select_from(SourceVersion).where(SourceVersion.is_superseded.is_(False))
    ) or 0
    chunk_count = db.scalar(select(func.count()).select_from(SourceChunk)) or 0
    rule_row_count = db.scalar(select(func.count()).select_from(RuleRow)) or 0
    approved_rule_row_count = db.scalar(
        select(func.count()).select_from(RuleRow).where(RuleRow.lifecycle_status.in_(APPROVED_RULE_STATUSES))
    ) or 0
    fts_count = _fts_count(db)
    supported_versions = _citable_supported_versions(db)
    accepted_current_version_count = db.scalar(
        select(func.count())
        .select_from(SourceVersion)
        .where(
            SourceVersion.review_status == "accepted",
            SourceVersion.is_superseded.is_(False),
            SourceVersion.parse_status.in_(("ok", "partial")),
        )
    ) or 0
    open_blocking_review_count = db.scalar(
        select(func.count())
        .select_from(ReviewQueueItem)
        .where(
            ReviewQueueItem.status.in_(("open", "in_progress")),
            ReviewQueueItem.blocking_level == "blocking",
        )
    ) or 0

    lines = [
        "# Source Library Audit",
        "",
        f"Generated: {datetime.now(UTC).replace(microsecond=0).isoformat()}",
        "",
        "## Summary",
        "",
        f"- Source documents: {source_count}",
        f"- Source versions: {version_count} total, {active_version_count} active",
        f"- Stored source chunks: {chunk_count}",
        f"- SQLite FTS citable indexed chunks: {fts_count if fts_count is not None else 'not built'}",
        f"- Rule rows: {rule_row_count} total, {approved_rule_row_count} approved",
        f"- Accepted current source versions: {accepted_current_version_count}",
        f"- Citable retrieval supported source versions: {len(supported_versions)}",
        f"- Open blocking review items: {open_blocking_review_count}",
        "",
        "## Source Types",
        "",
    ]

    for source_type, count in db.execute(
        select(SourceDocument.source_type, func.count())
        .group_by(SourceDocument.source_type)
        .order_by(SourceDocument.source_type)
    ):
        lines.append(f"- {source_type}: {count}")

    metadata_only = db.execute(
        select(SourceDocument.title, SourceDocument.canonical_url)
        .join(SourceVersion, SourceVersion.source_document_id == SourceDocument.id)
        .where(
            SourceVersion.parse_status == "metadata_only",
            SourceVersion.is_superseded.is_(False),
        )
        .order_by(SourceDocument.title)
    ).all()
    lines.extend(["", "## Metadata-Only / Non-Citable Records", ""])
    if metadata_only:
        for title, url in metadata_only:
            lines.append(f"- {title}: {url}")
    else:
        lines.append("- None")

    duplicate_urls = db.execute(
        select(SourceDocument.canonical_url, func.count())
        .where(SourceDocument.canonical_url.is_not(None))
        .group_by(SourceDocument.canonical_url)
        .having(func.count() > 1)
        .order_by(SourceDocument.canonical_url)
    ).all()
    lines.extend(["", "## Duplicate Canonical URLs", ""])
    if duplicate_urls:
        for url, count in duplicate_urls:
            lines.append(f"- {url}: {count}")
    else:
        lines.append("- None detected")

    zero_chunk_versions = db.execute(
        select(SourceDocument.title, SourceVersion.parse_status, SourceDocument.canonical_url)
        .join(SourceVersion, SourceVersion.source_document_id == SourceDocument.id)
        .outerjoin(SourceChunk, SourceChunk.source_version_id == SourceVersion.id)
        .where(SourceVersion.is_superseded.is_(False))
        .group_by(SourceDocument.id, SourceVersion.id)
        .having(func.count(SourceChunk.id) == 0)
        .order_by(SourceDocument.title)
    ).all()
    lines.extend(["", "## Versions Without Citable Chunks", ""])
    if zero_chunk_versions:
        for title, status, url in zero_chunk_versions:
            lines.append(f"- {title} ({status}): {url}")
    else:
        lines.append("- None detected")

    lines.extend(["", "## Citable Retrieval Gate", ""])
    if supported_versions:
        for title, version_label, version_id in supported_versions:
            label = f" ({version_label})" if version_label else ""
            lines.append(f"- {title}{label}: {version_id}")
    else:
        lines.append("- No source version currently passes the runtime citable retrieval gate.")
        if chunk_count:
            lines.append(
                "- Stored chunks alone are not enough: source review, licence review, blocking review items, "
                "approved rule rows, and no-orphan audits must also pass."
            )

    service = RetrievalService(db)
    lines.extend(["", "## Probe Questions", ""])
    for query in PROBE_QUERIES:
        started = perf_counter()
        answer = service.ask(query)
        elapsed_ms = (perf_counter() - started) * 1000
        top = answer.citations[0].source_title if answer.citations else "none"
        lines.append(
            f"- {query}: status={answer.status}, citations={len(answer.citations)}, "
            f"elapsed_ms={elapsed_ms:.1f}, top_source={top}"
        )

    lines.extend(
        [
            "",
            "## Required Human Review",
            "",
            "- Discovery output still requires licence, access, currency, and supersession review before any source is treated as submission support.",
            "- Paid/proprietary Australian Standards full text is intentionally not stored; Standards questions requiring full text must use licensed access and human review.",
            "- Local council coverage is still thin unless more official council source anchors are added and imported.",
            "- All generated regulatory answers remain assistive and require human signoff before export or submission use.",
        ]
    )
    return lines


def _citable_supported_versions(db) -> list[tuple[str, str | None, str]]:
    rows = db.execute(
        select(SourceVersion.id, SourceDocument.title, SourceVersion.version_label)
        .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
        .where(SourceVersion.is_superseded.is_(False))
        .order_by(SourceDocument.title, SourceVersion.id)
    ).all()
    return [
        (title, version_label, version_id)
        for version_id, title, version_label in rows
        if source_version_can_support_citable_retrieval(db, version_id)
    ]


def _fts_count(db) -> int | None:
    if db.get_bind().dialect.name != "sqlite":
        return None
    exists = db.execute(
        text("select 1 from sqlite_master where type = 'table' and name = 'source_chunk_fts' limit 1")
    ).scalar()
    if not exists:
        return None
    return db.execute(text("select count(*) from source_chunk_fts")).scalar_one()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the local DraftCheck source library DB.")
    parser.add_argument("--output", default="docs/SOURCE_LIBRARY_AUDIT.md")
    return parser.parse_args()


if __name__ == "__main__":
    main()

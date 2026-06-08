from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.models import SourceDocument, SourceVersion
from draftcheck_core.source_governance import SourceGovernanceService
from draftcheck_core.source_support import ACCEPTABLE_SOURCE_PARSE_STATUSES


@dataclass(frozen=True)
class ExtractionTarget:
    source_document_id: str
    source_version_id: str
    title: str
    version_label: str | None


@dataclass(frozen=True)
class ExtractionSummary:
    target: ExtractionTarget
    clauses_scanned: int
    dispositions_created: int
    candidates_created: int
    candidates_existing: int
    gate_status: str
    can_support_retrieval: bool
    blocking_reasons: tuple[str, ...]


def main() -> None:
    args = _parse_args()
    init_database()
    with SessionLocal() as db:
        targets = select_targets(
            db,
            source_version_id=args.source_version_id,
            source_title_contains=args.source_title_contains,
            include_pending=args.include_pending,
            limit=args.limit,
            all_sources=args.all,
        )
        if not targets:
            print("No matching source versions found.")
            return

        summaries = extract_targets(db, targets, enqueue_review_items=args.enqueue_review_items)
        if args.commit:
            db.commit()
            mode = "committed"
        else:
            db.rollback()
            mode = "dry-run rolled back"

    print(f"Rule extraction {mode}; targets={len(summaries)}")
    for summary in summaries:
        label = f" ({summary.target.version_label})" if summary.target.version_label else ""
        blockers = "; ".join(summary.blocking_reasons[:3]) or "none"
        print(
            f"- {summary.target.title}{label}: clauses={summary.clauses_scanned}, "
            f"dispositions_created={summary.dispositions_created}, "
            f"candidates_created={summary.candidates_created}, "
            f"candidates_existing={summary.candidates_existing}, "
            f"gate={summary.gate_status}, citable={str(summary.can_support_retrieval).lower()}, "
            f"blockers={blockers}"
        )


def select_targets(
    db: Session,
    *,
    source_version_id: str | None = None,
    source_title_contains: str | None = None,
    include_pending: bool = False,
    limit: int | None = None,
    all_sources: bool = False,
) -> list[ExtractionTarget]:
    if not (source_version_id or source_title_contains or all_sources):
        raise SystemExit("Select a source with --source-version-id, --source-title-contains, or --all.")

    stmt = (
        select(SourceDocument.id, SourceVersion.id, SourceDocument.title, SourceVersion.version_label)
        .join(SourceVersion, SourceVersion.source_document_id == SourceDocument.id)
        .where(
            SourceVersion.is_superseded.is_(False),
            SourceVersion.parse_status.in_(ACCEPTABLE_SOURCE_PARSE_STATUSES),
        )
        .order_by(SourceDocument.title, SourceVersion.id)
    )
    if source_version_id:
        stmt = stmt.where(SourceVersion.id == source_version_id)
    if source_title_contains:
        stmt = stmt.where(SourceDocument.title.ilike(f"%{source_title_contains}%"))
    if not include_pending:
        stmt = stmt.where(SourceVersion.review_status == "accepted")
    if limit:
        stmt = stmt.limit(limit)

    return [
        ExtractionTarget(
            source_document_id=source_id,
            source_version_id=version_id,
            title=title,
            version_label=version_label,
        )
        for source_id, version_id, title, version_label in db.execute(stmt).all()
    ]


def extract_targets(
    db: Session,
    targets: list[ExtractionTarget],
    *,
    enqueue_review_items: bool = False,
) -> list[ExtractionSummary]:
    rule_service = RuleGovernanceService(db)
    governance_service = SourceGovernanceService(db)
    summaries: list[ExtractionSummary] = []
    for target in targets:
        extraction = rule_service.extract_source_version_rules(
            target.source_version_id,
            source_document_id=target.source_document_id,
        )
        gate = governance_service.acceptance_gate(
            target.source_document_id,
            target.source_version_id,
            enqueue_review_items=enqueue_review_items,
        )
        summaries.append(
            ExtractionSummary(
                target=target,
                clauses_scanned=extraction.clauses_scanned,
                dispositions_created=extraction.dispositions_created,
                candidates_created=extraction.candidates_created,
                candidates_existing=extraction.candidates_existing,
                gate_status=gate.status,
                can_support_retrieval=gate.can_support_retrieval,
                blocking_reasons=tuple(gate.blocking_reasons),
            )
        )
    return summaries


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic rule extraction for selected source versions."
    )
    parser.add_argument("--source-version-id")
    parser.add_argument("--source-title-contains")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--all", action="store_true", help="Select all current parseable accepted source versions.")
    parser.add_argument("--include-pending", action="store_true", help="Include pending-review source versions.")
    parser.add_argument("--enqueue-review-items", action="store_true")
    parser.add_argument("--commit", action="store_true", help="Persist extraction candidates and dispositions.")
    args = parser.parse_args()
    if args.enqueue_review_items and not args.commit:
        parser.error("--enqueue-review-items requires --commit")
    return args


if __name__ == "__main__":
    main()

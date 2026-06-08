from __future__ import annotations

import argparse

from sqlalchemy import select

from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.models import SourceDocument, SourceVersion
from draftcheck_core.source_governance import SourceGovernanceService


def main() -> None:
    args = _parse_args()
    init_database()
    with SessionLocal() as db:
        source_id, version_id, title = _resolve_source_version(
            db,
            source_version_id=args.source_version_id,
            source_title_contains=args.source_title_contains,
        )
        result = SourceGovernanceService(db).reconcile_source_version_review_queue(
            source_id,
            version_id,
            reviewed_by=args.reviewed_by,
        )
        db.commit()

    print(f"Reconciled review queue for {title}")
    print(f"source_version_id={result.source_version_id}")
    print(f"resolved={len(result.resolved_item_ids)}")
    print(f"still_open={len(result.still_open_item_ids)}")
    print(f"gate={result.gate.status}")
    print(f"can_support_retrieval={str(result.gate.can_support_retrieval).lower()}")
    if result.resolved_item_ids:
        print("resolved_item_ids=" + ",".join(result.resolved_item_ids))


def _resolve_source_version(
    db,
    *,
    source_version_id: str | None,
    source_title_contains: str | None,
) -> tuple[str, str, str]:
    if not source_version_id and not source_title_contains:
        raise SystemExit("Select a source with --source-version-id or --source-title-contains.")
    stmt = (
        select(SourceDocument.id, SourceVersion.id, SourceDocument.title)
        .join(SourceVersion, SourceVersion.source_document_id == SourceDocument.id)
        .where(SourceVersion.is_superseded.is_(False))
        .order_by(SourceDocument.title, SourceVersion.id)
    )
    if source_version_id:
        stmt = stmt.where(SourceVersion.id == source_version_id)
    if source_title_contains:
        stmt = stmt.where(SourceDocument.title.ilike(f"%{source_title_contains}%"))
    rows = db.execute(stmt).all()
    if not rows:
        raise SystemExit("No matching source version found.")
    if len(rows) > 1:
        raise SystemExit("Multiple source versions matched; use --source-version-id.")
    return rows[0]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile stale source-version review queue blockers.")
    parser.add_argument("--source-version-id")
    parser.add_argument("--source-title-contains")
    parser.add_argument("--reviewed-by", default="system-reconcile")
    return parser.parse_args()


if __name__ == "__main__":
    main()

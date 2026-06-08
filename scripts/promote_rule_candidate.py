from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy.orm import Session

from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.database import SessionLocal, init_database
from draftcheck_core.models import RuleExtractionCandidate, SourceDocument, SourceVersion
from draftcheck_core.source_governance import SourceGovernanceService
from draftcheck_shared.schemas import RuleCandidatePromotionRequest, SourceReviewQueueReconciliationRead


@dataclass(frozen=True)
class PromotionSummary:
    candidate_id: str
    rule_row_id: str
    source_document_id: str
    source_title: str
    source_version_id: str
    rule_key: str
    candidate_status: str
    rule_lifecycle_status: str


def main() -> None:
    args = _parse_args()
    init_database()
    with SessionLocal() as db:
        summaries, reconciliations = promote_candidates(
            db,
            candidate_ids=args.candidate_id,
            reviewed_by=args.reviewed_by,
            notes=args.notes,
            reconcile_source=args.reconcile_source,
        )
        if args.commit:
            db.commit()
            mode = "committed"
        else:
            db.rollback()
            mode = "dry-run rolled back"

    print(f"Rule candidate promotion {mode}; candidates={len(summaries)}")
    for summary in summaries:
        print(
            f"- candidate={summary.candidate_id}, rule_row={summary.rule_row_id}, "
            f"source_version={summary.source_version_id}, rule_key={summary.rule_key}, "
            f"candidate_status={summary.candidate_status}, "
            f"rule_lifecycle={summary.rule_lifecycle_status}, source={summary.source_title}"
        )
    for reconciliation in reconciliations:
        print(
            f"- reconciled source_version={reconciliation.source_version_id}, "
            f"resolved={len(reconciliation.resolved_item_ids)}, "
            f"still_open={len(reconciliation.still_open_item_ids)}, "
            f"gate={reconciliation.gate.status}, "
            f"can_support_retrieval={str(reconciliation.gate.can_support_retrieval).lower()}"
        )


def promote_candidates(
    db: Session,
    *,
    candidate_ids: list[str],
    reviewed_by: str = "rule-reviewer",
    notes: str = "",
    reconcile_source: bool = False,
) -> tuple[list[PromotionSummary], list[SourceReviewQueueReconciliationRead]]:
    if not candidate_ids:
        raise ValueError("At least one candidate id is required.")

    rule_service = RuleGovernanceService(db)
    source_service = SourceGovernanceService(db)
    summaries: list[PromotionSummary] = []
    source_versions_to_reconcile: dict[str, tuple[str, str]] = {}

    for candidate_id in candidate_ids:
        candidate = db.get(RuleExtractionCandidate, candidate_id)
        if not candidate:
            raise KeyError("Rule extraction candidate not found")
        source, version = _candidate_source(db, candidate)
        promoted = rule_service.promote_rule_candidate(
            candidate.id,
            RuleCandidatePromotionRequest(reviewed_by=reviewed_by, notes=notes),
        )
        candidate_after = db.get(RuleExtractionCandidate, candidate.id)
        if not candidate_after:
            raise KeyError("Rule extraction candidate not found after promotion")
        summaries.append(
            PromotionSummary(
                candidate_id=candidate.id,
                rule_row_id=promoted.id,
                source_document_id=source.id,
                source_title=source.title,
                source_version_id=version.id,
                rule_key=promoted.rule_key,
                candidate_status=candidate_after.status,
                rule_lifecycle_status=promoted.lifecycle_status,
            )
        )
        source_versions_to_reconcile[version.id] = (source.id, version.id)

    reconciliations: list[SourceReviewQueueReconciliationRead] = []
    if reconcile_source:
        for source_id, version_id in source_versions_to_reconcile.values():
            reconciliations.append(
                source_service.reconcile_source_version_review_queue(
                    source_id,
                    version_id,
                    reviewed_by=reviewed_by,
                )
            )

    return summaries, reconciliations


def _candidate_source(db: Session, candidate: RuleExtractionCandidate) -> tuple[SourceDocument, SourceVersion]:
    version = db.get(SourceVersion, candidate.source_version_id)
    if not version:
        raise ValueError("Rule extraction candidate source version was not found")
    source = db.get(SourceDocument, version.source_document_id)
    if not source:
        raise ValueError("Rule extraction candidate source document was not found")
    return source, version


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote deterministic rule extraction candidates into pending review RuleRows."
    )
    parser.add_argument(
        "--candidate-id",
        action="append",
        required=True,
        help="RuleExtractionCandidate id to promote. Pass more than once for multiple candidates.",
    )
    parser.add_argument("--reviewed-by", default="rule-reviewer")
    parser.add_argument("--notes", default="")
    parser.add_argument("--reconcile-source", action="store_true")
    parser.add_argument("--commit", action="store_true", help="Persist promotions; otherwise roll back after printing.")
    return parser.parse_args()


if __name__ == "__main__":
    main()

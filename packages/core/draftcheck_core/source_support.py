from __future__ import annotations

from typing import Any

from sqlalchemy import exists, not_, select
from sqlalchemy.orm import Session

from draftcheck_core.models import ReviewQueueItem, SourceLicenceReview, SourceVersion


ACCEPTABLE_SOURCE_PARSE_STATUSES = {"ok", "partial"}
SOURCE_SUPPORT_BLOCKING_QUEUES = {
    "source_review",
    "rule_review",
    "licence_review",
    "eval_failure_review",
}
CITABLE_RETRIEVAL_BLOCKING_QUEUES = {
    "source_review",
    "rule_review",
    "licence_review",
    "eval_failure_review",
}
OPEN_REVIEW_STATUSES = {"open", "in_progress"}


def source_version_runtime_support_conditions() -> tuple[Any, ...]:
    blocking_review_exists = exists(
        select(1).where(
            ReviewQueueItem.source_version_id == SourceVersion.id,
            ReviewQueueItem.queue.in_(SOURCE_SUPPORT_BLOCKING_QUEUES),
            ReviewQueueItem.status.in_(OPEN_REVIEW_STATUSES),
            ReviewQueueItem.blocking_level == "blocking",
        )
    )
    return (
        SourceVersion.review_status == "accepted",
        SourceVersion.is_superseded.is_(False),
        SourceVersion.parse_status.in_(ACCEPTABLE_SOURCE_PARSE_STATUSES),
        SourceLicenceReview.review_status == "approved",
        SourceLicenceReview.allowed_storage.is_(True),
        SourceLicenceReview.allowed_ai_processing.is_(True),
        not_(blocking_review_exists),
    )


def source_version_citable_retrieval_conditions() -> tuple[Any, ...]:
    blocking_review_exists = exists(
        select(1).where(
            ReviewQueueItem.source_version_id == SourceVersion.id,
            ReviewQueueItem.queue.in_(CITABLE_RETRIEVAL_BLOCKING_QUEUES),
            ReviewQueueItem.status.in_(OPEN_REVIEW_STATUSES),
            ReviewQueueItem.blocking_level == "blocking",
        )
    )
    return (
        SourceVersion.review_status == "accepted",
        SourceVersion.is_superseded.is_(False),
        SourceVersion.parse_status.in_(ACCEPTABLE_SOURCE_PARSE_STATUSES),
        SourceLicenceReview.review_status == "approved",
        SourceLicenceReview.allowed_storage.is_(True),
        SourceLicenceReview.allowed_ai_processing.is_(True),
        not_(blocking_review_exists),
    )


def source_version_can_support_regulatory_output(db: Session, source_version_id: str) -> bool:
    static_gate_passes = (
        db.scalar(
            select(SourceVersion.id)
            .join(SourceLicenceReview, SourceLicenceReview.source_version_id == SourceVersion.id)
            .where(SourceVersion.id == source_version_id, *source_version_runtime_support_conditions())
            .limit(1)
        )
        is not None
    )
    if not static_gate_passes:
        return False
    return _source_version_rule_acceptance_audits_pass(db, source_version_id)


def source_version_can_support_citable_retrieval(db: Session, source_version_id: str) -> bool:
    static_gate_passes = (
        db.scalar(
            select(SourceVersion.id)
            .join(SourceLicenceReview, SourceLicenceReview.source_version_id == SourceVersion.id)
            .where(SourceVersion.id == source_version_id, *source_version_citable_retrieval_conditions())
            .limit(1)
        )
        is not None
    )
    if not static_gate_passes:
        return False
    return _source_version_rule_acceptance_audits_pass(db, source_version_id)


def _source_version_rule_acceptance_audits_pass(db: Session, source_version_id: str) -> bool:
    from draftcheck_compliance.rule_audits import RuleAuditService
    from draftcheck_compliance.rules import RuleGovernanceService

    coverage = RuleGovernanceService(db).coverage_audit(source_version_id=source_version_id, summary_only=True)
    if coverage.gap_count:
        return False
    no_orphan = RuleAuditService(db).no_orphan_audit(source_version_id=source_version_id, summary_only=True)
    return no_orphan.blocking_count == 0

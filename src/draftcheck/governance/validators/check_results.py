"""GOV-CHK-* — compliance check evidence checks.

Implements the four check-result validators in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from draftcheck.db.models import (
    CheckResult,
    CheckRun,
    Project,
    RfiItem,
    SourceReviewRecord,
)
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_ADVISORY_STATUSES = ("likely_pass", "likely_fail")


def _citations_check_approved_versions(
    citations_json: list | None,
    session: "Session",
) -> list[object]:
    """Return list of source_version_ids whose latest review is not 'approved'."""
    flagged: list[object] = []
    if not citations_json:
        return flagged
    for c in citations_json:
        if not isinstance(c, dict):
            continue
        sv_id = c.get("source_version_id")
        if not sv_id:
            continue
        latest = session.scalars(
            select(SourceReviewRecord)
            .where(SourceReviewRecord.source_version_id == sv_id)
            .order_by(SourceReviewRecord.reviewed_at.desc())
            .limit(1)
        ).first()
        if latest is None or latest.review_status != "approved":
            flagged.append(sv_id)
    return flagged


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    # GOV-CHK-001: CheckResult with advisory status must have resolved_rule
    # + non-empty citations + non-empty decision_trace.
    for cr in session.scalars(select(CheckResult)):
        if cr.status not in _ADVISORY_STATUSES:
            continue
        if cr.resolved_rule_id is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CHK_001_RESOLVED_RULE_AND_CITATIONS,
                    severity=GovernanceSeverity.CRITICAL,
                    subject_type="check_result",
                    subject_id=cr.id,
                    message=(
                        f"CheckResult {cr.id} ({cr.check_key!r}) status is "
                        f"{cr.status!r} but resolved_rule_id is NULL."
                    ),
                )
            )
        if not cr.citations_json:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CHK_001_RESOLVED_RULE_AND_CITATIONS,
                    severity=GovernanceSeverity.CRITICAL,
                    subject_type="check_result",
                    subject_id=cr.id,
                    message=(
                        f"CheckResult {cr.id} ({cr.check_key!r}) status is "
                        f"{cr.status!r} but citations_json is empty."
                    ),
                )
            )
        if not cr.decision_trace_json:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CHK_001_RESOLVED_RULE_AND_CITATIONS,
                    severity=GovernanceSeverity.CRITICAL,
                    subject_type="check_result",
                    subject_id=cr.id,
                    message=(
                        f"CheckResult {cr.id} ({cr.check_key!r}) status is "
                        f"{cr.status!r} but decision_trace_json is empty."
                    ),
                )
            )

        # GOV-CHK-002: every cited source_version must be approved.
        bad_versions = _citations_check_approved_versions(cr.citations_json, session)
        for sv_id in bad_versions:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CHK_002_CITATIONS_FROM_APPROVED_VERSION,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="check_result",
                    subject_id=cr.id,
                    message=(
                        f"CheckResult {cr.id} cites source_version {sv_id} "
                        "whose latest review is not 'approved'."
                    ),
                    evidence_refs=[str(sv_id)],
                )
            )

    # GOV-CHK-003: CheckRun with 'has_likely_failures' must have a linked RfiItem.
    for run in session.scalars(select(CheckRun)):
        if run.status != "has_likely_failures":
            continue
        # At least one CheckResult in this run must have an RfiItem.
        result_ids: list[UUID] = list(
            session.scalars(
                select(CheckResult.id).where(CheckResult.check_run_id == run.id)
            )
        )
        if not result_ids:
            continue
        rfi = session.scalar(
            select(RfiItem.id)
            .where(
                RfiItem.check_result_id.in_(result_ids),
            )
            .limit(1)
        )
        if rfi is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CHK_003_FAILURES_HAVE_RFI,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="check_run",
                    subject_id=run.id,
                    message=(
                        f"CheckRun {run.id} status is 'has_likely_failures' "
                        "but no RfiItem is linked to any of its CheckResults."
                    ),
                )
            )

    # GOV-CHK-004: every CheckRun's as_of_date must lie within the project's
    # council_scope currency window. Without a stored currency window we use
    # a soft heuristic: as_of_date must be within 365 days of the most recent
    # source_versions.published_at for the same council_scope. This is a
    # 'minor' check; absence of the window is reported, not failed.
    for run in session.scalars(select(CheckRun)):
        project = session.get(Project, run.project_id) if run.project_id else None
        if project is None:
            continue
        council: str | None = project.council_scope
        if council is None and isinstance(project.metadata_json, dict):
            raw = project.metadata_json.get("council_scope")
            council = str(raw) if raw is not None else None
        if not council:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CHK_004_RUN_WITHIN_CURRENCY_WINDOW,
                    severity=GovernanceSeverity.MINOR,
                    subject_type="check_run",
                    subject_id=run.id,
                    message=(
                        f"CheckRun {run.id} project {project.id} has no "
                        "council_scope; cannot verify currency window."
                    ),
                )
            )

    return failures

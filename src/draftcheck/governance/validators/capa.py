"""GOV-CAPA-* — CAPA / ReviewItem checks.

Implements the three CAPA-validators in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from draftcheck.db.models import GovernanceFinding, ReviewItem
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_RESOLVED_STATUSES = ("resolved", "closed")
_TERMINAL_STATUSES = ("resolved", "closed", "rejected")


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    for ri in session.scalars(select(ReviewItem)):
        # GOV-CAPA-001: a resolved/closed CAPA must have closure evidence
        # + effectiveness_check_due_date.
        if ri.status in _RESOLVED_STATUSES:
            missing = []
            if ri.closure_evidence_id is None:
                missing.append("closure_evidence_id")
            if ri.effectiveness_check_due_date is None:
                missing.append("effectiveness_check_due_date")
            if missing:
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.CAPA_001_CLOSED_HAS_EVIDENCE_AND_DATE,
                        severity=GovernanceSeverity.CRITICAL,
                        subject_type="review_item",
                        subject_id=ri.id,
                        message=(
                            f"ReviewItem {ri.id} status is {ri.status!r} but is "
                            f"missing: {', '.join(missing)}."
                        ),
                    )
                )

        # GOV-CAPA-002: effectiveness check overdue.
        if (
            ri.status in _RESOLVED_STATUSES
            and ri.effectiveness_result is None
            and ri.effectiveness_check_due_date is not None
        ):
            d = ri.effectiveness_check_due_date
            if isinstance(d, datetime):
                due = d.date()
            else:
                due = d
            if due < datetime.now(UTC).date():
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.CAPA_002_EFFECTIVENESS_CHECK_OVERDUE,
                        severity=GovernanceSeverity.MAJOR,
                        subject_type="review_item",
                        subject_id=ri.id,
                        message=(
                            f"ReviewItem {ri.id} effectiveness_check_due_date "
                            f"{due} is in the past and effectiveness_result is empty."
                        ),
                    )
                )

        # GOV-CAPA-003: if a CAPA references a finding, that finding must
        # be in 'converted_to_capa' state.
        if ri.proposed_by_finding_id is not None:
            finding = session.get(GovernanceFinding, ri.proposed_by_finding_id)
            if finding is None or finding.status != "converted_to_capa":
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.CAPA_003_FINDING_LINK_INTEGRITY,
                        severity=GovernanceSeverity.MINOR,
                        subject_type="review_item",
                        subject_id=ri.id,
                        message=(
                            f"ReviewItem {ri.id} references proposed_by_finding_id "
                            f"{ri.proposed_by_finding_id} but the finding is not "
                            "in 'converted_to_capa' state."
                        ),
                    )
                )

    return failures

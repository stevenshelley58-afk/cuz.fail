"""GOV-FIND-* — AI proposed-finding queue checks.

Implements the three finding-validators in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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


_PROPOSED_STALE_DAYS = 14


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    threshold = datetime.now(UTC) - timedelta(days=_PROPOSED_STALE_DAYS)

    for f in session.scalars(select(GovernanceFinding)):
        # GOV-FIND-001: proposed finding older than 14 days is stale.
        if f.status == "proposed" and f.created_at < threshold:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.FIND_001_PROPOSED_NOT_STALE,
                    severity=GovernanceSeverity.CRITICAL,
                    subject_type="governance_finding",
                    subject_id=f.id,
                    message=(
                        f"GovernanceFinding {f.id} has been 'proposed' since "
                        f"{f.created_at} (> {_PROPOSED_STALE_DAYS} days). "
                        "Per GOV-FIND-001 it is overdue for reviewer sign-off."
                    ),
                )
            )

        # GOV-FIND-002: accepted requires decision_user_id, decision_reason,
        # decision_evidence_id, and (transitively) a linked_capa_id.
        if f.status == "accepted":
            missing = []
            if f.decision_user_id is None:
                missing.append("decision_user_id")
            if not f.decision_reason:
                missing.append("decision_reason")
            if f.decision_evidence_id is None:
                missing.append("decision_evidence_id")
            if f.linked_capa_id is None:
                missing.append("linked_capa_id")
            if missing:
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.FIND_002_ACCEPTED_HAS_DECISION_FIELDS,
                        severity=GovernanceSeverity.CRITICAL,
                        subject_type="governance_finding",
                        subject_id=f.id,
                        message=(
                            f"GovernanceFinding {f.id} is 'accepted' but is "
                            f"missing: {', '.join(missing)}."
                        ),
                    )
                )

        # GOV-FIND-003: converted_to_capa must link to a CAPA with the
        # required CAPA fields populated.
        if f.status == "converted_to_capa":
            capa = session.get(ReviewItem, f.linked_capa_id) if f.linked_capa_id else None
            if capa is None:
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.FIND_003_CONVERTED_CAPA_LINKED,
                        severity=GovernanceSeverity.CRITICAL,
                        subject_type="governance_finding",
                        subject_id=f.id,
                        message=(
                            f"GovernanceFinding {f.id} is 'converted_to_capa' "
                            "but linked_capa_id does not resolve to a ReviewItem."
                        ),
                    )
                )
            else:
                missing = []
                if not capa.severity:
                    missing.append("severity")
                if capa.assigned_user_id is None:
                    missing.append("owner_user_id")
                if capa.due_at is None:
                    missing.append("due_at")
                if missing:
                    failures.append(
                        GovernanceFailure(
                            code=GovernanceFailureCode.FIND_003_CONVERTED_CAPA_LINKED,
                            severity=GovernanceSeverity.CRITICAL,
                            subject_type="governance_finding",
                            subject_id=f.id,
                            message=(
                                f"GovernanceFinding {f.id} -> CAPA {capa.id} "
                                f"is missing: {', '.join(missing)}."
                            ),
                            evidence_refs=[str(capa.id)],
                        )
                    )

    return failures

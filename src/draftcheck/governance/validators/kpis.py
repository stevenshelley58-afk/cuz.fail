"""GOV-KPI-* — KPI registry checks.

Implements the one KPI-validator in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from draftcheck.db.models import GovernanceKpi, GovernanceKpiResult
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    for kpi in session.scalars(select(GovernanceKpi)):
        if kpi.review_cadence_days is None:
            continue
        # Find the most recent result for this KPI.
        latest = session.scalar(
            select(func.max(GovernanceKpiResult.computed_at)).where(
                GovernanceKpiResult.kpi_id == kpi.id
            )
        )
        if latest is None:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.KPI_001_RESULT_FRESH,
                    severity=GovernanceSeverity.MINOR,
                    subject_type="governance_kpi",
                    subject_id=kpi.id,
                    message=(
                        f"GovernanceKpi {kpi.id} (code={kpi.code!r}) has "
                        f"review_cadence_days={kpi.review_cadence_days} but "
                        "has no results yet."
                    ),
                )
            )
            continue
        threshold = datetime.now(UTC) - timedelta(days=kpi.review_cadence_days)
        if latest < threshold:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.KPI_001_RESULT_FRESH,
                    severity=GovernanceSeverity.MINOR,
                    subject_type="governance_kpi",
                    subject_id=kpi.id,
                    message=(
                        f"GovernanceKpi {kpi.id} (code={kpi.code!r}) latest "
                        f"result is from {latest}; older than the "
                        f"{kpi.review_cadence_days}-day cadence."
                    ),
                )
            )

    return failures

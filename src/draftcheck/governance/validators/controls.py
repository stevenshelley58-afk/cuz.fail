"""GOV-CTRL-* — control registry checks.

Implements the two control-validators in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from draftcheck.db.models import GovernanceControl, GovernanceRisk
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    # GOV-CTRL-002: every control referenced by a risk must have an owner_role.
    # The check is on the control itself, not the risk; the failure is
    # reported against the control row.
    risks = {r.code: r for r in session.scalars(select(GovernanceRisk))}

    controls = list(session.scalars(select(GovernanceControl)))
    for c in controls:
        if c.owner_role is None or c.owner_role == "":
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CTRL_002_OWNER_ROLE_SET,
                    severity=GovernanceSeverity.CRITICAL,
                    subject_type="governance_control",
                    subject_id=c.id,
                    message=(
                        f"GovernanceControl {c.id} (code={c.code!r}, name={c.name!r}) "
                        "has no owner_role."
                    ),
                )
            )
        # Sanity: code must reference an existing risk.
        if c.code not in risks:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.CTRL_002_OWNER_ROLE_SET,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="governance_control",
                    subject_id=c.id,
                    message=(
                        f"GovernanceControl {c.id} (code={c.code!r}) "
                        "references an unknown risk."
                    ),
                )
            )

        # GOV-CTRL-001: test_frequency_days + last_tested_at.
        if c.test_frequency_days is not None:
            if c.last_tested_at is None:
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.CTRL_001_TESTED_WITHIN_FREQUENCY,
                        severity=GovernanceSeverity.MAJOR,
                        subject_type="governance_control",
                        subject_id=c.id,
                        message=(
                            f"GovernanceControl {c.id} (code={c.code!r}) has "
                            f"test_frequency_days={c.test_frequency_days} but "
                            "has never been tested (last_tested_at is NULL)."
                        ),
                    )
                )
            else:
                threshold = datetime.now(UTC) - timedelta(days=c.test_frequency_days)
                if c.last_tested_at < threshold:
                    failures.append(
                        GovernanceFailure(
                            code=GovernanceFailureCode.CTRL_001_TESTED_WITHIN_FREQUENCY,
                            severity=GovernanceSeverity.MAJOR,
                            subject_type="governance_control",
                            subject_id=c.id,
                            message=(
                                f"GovernanceControl {c.id} (code={c.code!r}) "
                                f"last_tested_at={c.last_tested_at} is older than "
                                f"the {c.test_frequency_days}-day test frequency."
                            ),
                        )
                    )

    return failures

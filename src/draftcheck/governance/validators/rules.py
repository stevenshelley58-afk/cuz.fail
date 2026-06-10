"""GOV-RULE-* — rule extraction traceability checks.

Implements the four rule-validators in
docs/process-control/implementation-map.md §6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from draftcheck.db.models import (
    Rule,
    RuleClauseLink,
)
from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
)


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Operators supported by the compliance engine.
# Mirrors src/draftcheck/checks/engine.py:_OPERATORS.
_VALID_OPERATORS = frozenset({"gte", "lte", "gt", "lt", "eq"})


def _overlaps_list(a: list | None, b: list | None) -> bool:
    """Two applicability lists overlap if any element is shared, or one is None.

    The convention in models.py is that ``NULL`` means "applies to all".
    Two NULL-applicable rules on the same rule_key DO conflict.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return True  # one is global, the other is scoped -> conflict
    sa, sb = set(a), set(b)
    return bool(sa & sb)


def _scopes_overlap(a: Rule, b: Rule) -> bool:
    if (a.council_scope is None) != (b.council_scope is None):
        # one is global, one is scoped
        return True
    if a.council_scope is not None and b.council_scope is not None:
        if a.council_scope != b.council_scope:
            return False
    if not _overlaps_list(a.applicable_zones, b.applicable_zones):
        return False
    if not _overlaps_list(a.applicable_r_codes, b.applicable_r_codes):
        return False
    return True


def validate(session: "Session") -> list[GovernanceFailure]:
    failures: list[GovernanceFailure] = []

    rules = list(session.scalars(select(Rule)))

    # GOV-RULE-001/002/003: per-rule checks.
    for r in rules:
        if r.lifecycle_status == "approved":
            if not (r.quote and r.clause_id and r.source_version_id):
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.RULE_001_HAS_QUOTE_AND_CLAUSE,
                        severity=GovernanceSeverity.CRITICAL,
                        subject_type="rule",
                        subject_id=r.id,
                        message=(
                            f"Rule {r.id} ({r.rule_key!r}) is approved but is missing "
                            "one of: quote, clause_id, source_version_id."
                        ),
                    )
                )
            # GOV-RULE-002: at least one RuleClauseLink with link_type='primary'.
            has_primary = any(
                link.link_type == "primary" and link.clause_id == r.clause_id
                for link in r.clause_links
            ) if hasattr(r, "clause_links") else False
            # Fallback query if relationship is not loaded.
            if not has_primary:
                cnt = session.scalar(
                    select(RuleClauseLink.id)
                    .where(
                        RuleClauseLink.rule_id == r.id,
                        RuleClauseLink.link_type == "primary",
                    )
                    .limit(1)
                )
                has_primary = cnt is not None
            if not has_primary:
                failures.append(
                    GovernanceFailure(
                        code=GovernanceFailureCode.RULE_002_HAS_PRIMARY_LINK,
                        severity=GovernanceSeverity.CRITICAL,
                        subject_type="rule",
                        subject_id=r.id,
                        message=(
                            f"Rule {r.id} ({r.rule_key!r}) has no primary RuleClauseLink."
                        ),
                    )
                )

        # GOV-RULE-003: operator must be in the compliance engine's allowed set.
        if r.operator is not None and r.operator not in _VALID_OPERATORS:
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.RULE_003_OPERATOR_VALID,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="rule",
                    subject_id=r.id,
                    message=(
                        f"Rule {r.id} ({r.rule_key!r}) operator is "
                        f"{r.operator!r}; expected one of {sorted(_VALID_OPERATORS)}."
                    ),
                )
            )

    # GOV-RULE-004: no two approved rules share rule_key + overlapping scopes.
    approved = [r for r in rules if r.lifecycle_status == "approved" and r.rule_key]
    for i, a in enumerate(approved):
        for b in approved[i + 1 :]:
            if a.rule_key != b.rule_key:
                continue
            if not _scopes_overlap(a, b):
                continue
            failures.append(
                GovernanceFailure(
                    code=GovernanceFailureCode.RULE_004_NO_CONFLICTING_APPROVED_RULES,
                    severity=GovernanceSeverity.MAJOR,
                    subject_type="rule",
                    subject_id=a.id,
                    message=(
                        f"Rule {a.id} and {b.id} both approved for rule_key "
                        f"{a.rule_key!r} with overlapping scope."
                    ),
                    evidence_refs=[str(b.id)],
                )
            )

    return failures

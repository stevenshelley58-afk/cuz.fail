"""Governance validation primitives.

PR-3 of the process-control / source-governance feature
(docs/process-control/implementation-map.md §6).

The audit script and the /api/v1/governance/audit-report endpoint
both use these primitives to compute a list of ``GovernanceFailure``
records. The primitives are pure functions that take a SQLAlchemy
``Session`` and return a ``list[GovernanceFailure]``; they never
mutate the database.

This module is intentionally framework-light. No FastAPI, no
background-job hooks, no LLM calls. The CI audit script
(scripts/governance_audit.py, PR-5) and the API endpoint (PR-4)
both call into here.
"""

from draftcheck.governance.types import (
    GovernanceFailure,
    GovernanceFailureCode,
    GovernanceSeverity,
    run_all_validators,
)

__all__ = [
    "GovernanceFailure",
    "GovernanceFailureCode",
    "GovernanceSeverity",
    "run_all_validators",
]

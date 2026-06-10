"""Eval runner for LotFile v3.

Runs EvalCase fixtures against the current skill version and records
EvalRun results.  The eval gate (§7 of MASTER_REBUILD_PLAN.md) blocks
skill activation when the pass-rate drops below threshold.

Gate chain: LLM proposes -> validators check -> evals gate -> deterministic
engine decides.  This module implements the "evals gate" step.

Phase 5 wires procrastinate enqueueing; for now these are plain functions
called from tests and the /admin/evals API endpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck.db.models import EvalCase, EvalRun


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ScoreFn = Callable[[dict[str, Any], dict[str, Any]], Decimal]
"""A scoring function: (expected_json, output_json) -> score in [0, 1]."""


# ---------------------------------------------------------------------------
# Built-in scoring functions
# ---------------------------------------------------------------------------


def exact_match_score(expected: dict[str, Any], output: dict[str, Any]) -> Decimal:
    """1.0 if the output JSON matches expected exactly, else 0.0."""
    return Decimal("1.0") if output == expected else Decimal("0.0")


def key_match_score(expected: dict[str, Any], output: dict[str, Any]) -> Decimal:
    """Fraction of expected keys whose values match in output."""
    if not expected:
        return Decimal("1.0")
    hits = sum(1 for k, v in expected.items() if output.get(k) == v)
    return Decimal(str(round(hits / len(expected), 4)))


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------


def run_eval_case(
    eval_case_id: UUID,
    skill_version_id: str,
    run_fn: Callable[[dict[str, Any]], dict[str, Any]],
    session: Session,
    score_fn: ScoreFn = exact_match_score,
    job_trace_id: UUID | None = None,
) -> EvalRun:
    """Execute one EvalCase and persist an EvalRun.

    Parameters
    ----------
    eval_case_id:
        Primary key of the EvalCase row to test.
    skill_version_id:
        skill_versions.id that produced the output (recorded for trend analysis).
    run_fn:
        Callable that accepts input_json and returns output_json.  The caller
        supplies this so the runner stays decoupled from the LLM layer.
    session:
        Active SQLAlchemy session (caller manages transaction).
    score_fn:
        Scoring function; defaults to exact_match_score.
    job_trace_id:
        Optional job_trace_id to link the EvalRun to its job trace.

    Returns
    -------
    EvalRun
        The persisted (flushed but not committed) EvalRun row.
    """
    case = session.get(EvalCase, eval_case_id)
    if case is None:
        raise ValueError(f"EvalCase {eval_case_id} not found")

    started_at = datetime.now(UTC)
    error: str | None = None
    output_json: dict[str, Any] = {}
    status = "failed"
    score: Decimal | None = None

    try:
        output_json = run_fn(case.input_json)
        score = score_fn(case.expected_json, output_json)
        status = "passed" if score >= Decimal("1.0") else "failed"
    except Exception as exc:
        error = str(exc)
        status = "error"

    finished_at = datetime.now(UTC)

    run = EvalRun(
        id=uuid4(),
        eval_case_id=eval_case_id,
        skill_version_id=skill_version_id,
        job_trace_id=job_trace_id,
        status=status,
        score=score,
        output_json=output_json,
        metrics_json={
            "score_fn": score_fn.__name__,
            "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        },
        started_at=started_at,
        finished_at=finished_at,
        error=error,
    )
    session.add(run)
    session.flush()
    return run


def run_eval_suite(
    suite_name: str,
    skill_version_id: str,
    run_fn: Callable[[dict[str, Any]], dict[str, Any]],
    session: Session,
    score_fn: ScoreFn = exact_match_score,
    pass_threshold: Decimal = Decimal("0.8"),
) -> dict[str, Any]:
    """Run all active EvalCase rows for a suite and return a summary.

    Parameters
    ----------
    suite_name:
        Value of EvalCase.suite_name to filter on.
    skill_version_id:
        Recorded on every EvalRun for trend analysis.
    run_fn:
        Callable accepting input_json, returning output_json.
    session:
        Active SQLAlchemy session.
    score_fn:
        Scoring function applied to each case.
    pass_threshold:
        Minimum pass-rate (fraction of cases with status='passed') required
        for the gate to allow skill activation.

    Returns
    -------
    dict with keys:
        suite_name, skill_version_id, total, passed, failed, errored,
        pass_rate, gate_passed, run_ids
    """
    stmt = (
        select(EvalCase)
        .where(EvalCase.suite_name == suite_name, EvalCase.status == "active")
        .order_by(EvalCase.case_key)
    )
    cases: list[EvalCase] = list(session.scalars(stmt))
    if not cases:
        return {
            "suite_name": suite_name,
            "skill_version_id": skill_version_id,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errored": 0,
            "pass_rate": Decimal("1.0"),
            "gate_passed": True,
            "run_ids": [],
        }

    runs: list[EvalRun] = []
    for case in cases:
        run = run_eval_case(
            eval_case_id=case.id,
            skill_version_id=skill_version_id,
            run_fn=run_fn,
            session=session,
            score_fn=score_fn,
        )
        runs.append(run)

    total = len(runs)
    passed = sum(1 for r in runs if r.status == "passed")
    failed = sum(1 for r in runs if r.status == "failed")
    errored = sum(1 for r in runs if r.status == "error")
    pass_rate = Decimal(str(round(passed / total, 4))) if total else Decimal("1.0")
    gate_passed = pass_rate >= pass_threshold

    return {
        "suite_name": suite_name,
        "skill_version_id": skill_version_id,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "pass_rate": pass_rate,
        "gate_passed": gate_passed,
        "run_ids": [r.id for r in runs],
    }


# ── Convenience class wrappers for callers that expect OOP interface ──────────

from dataclasses import dataclass as _dc  # noqa: E402


@_dc
class EvalSuiteResult:
    suite_name: str
    total: int
    passed: int
    failed: int
    errors: int
    pass_rate: Decimal
    gate_passed: bool
    run_ids: list


class EvalRunner:
    """Thin OOP wrapper around the module-level run_eval_* functions."""

    def __init__(self, run_fn: Callable[[dict[str, Any]], dict[str, Any]], session: Session):
        self._run_fn = run_fn
        self._session = session

    def run_suite(
        self,
        suite_name: str,
        skill_version_id: str = "manual",
        score_fn: ScoreFn = exact_match_score,
        pass_threshold: Decimal = Decimal("0.8"),
    ) -> EvalSuiteResult:
        result = run_eval_suite(
            suite_name=suite_name,
            skill_version_id=skill_version_id,
            run_fn=self._run_fn,
            session=self._session,
            score_fn=score_fn,
            pass_threshold=pass_threshold,
        )
        return EvalSuiteResult(
            suite_name=result["suite_name"],
            total=result["total"],
            passed=result["passed"],
            failed=result["failed"],
            errors=result["errored"],
            pass_rate=result["pass_rate"],
            gate_passed=result["gate_passed"],
            run_ids=result["run_ids"],
        )

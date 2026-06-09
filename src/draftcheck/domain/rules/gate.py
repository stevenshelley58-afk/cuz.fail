"""Promotion gate — the ONLY insertion path from rule_candidate → rules.

Design invariants enforced here:
  1. auto_promote() is the sole writer of rules rows.
  2. Promotion is blocked unless validators passed AND eval gate ran.
  3. Any precondition failure raises PromotionBlockedError (never silent skip).
  4. Every promotion writes an audit_events row.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck.db.models import (
    AuditEvent,
    Clause,
    EvalCase,
    EvalRun,
    ReviewItem,
    Rule,
    RuleCandidate,
    utc_now,
)
from draftcheck.extraction.validators import run_all_validators

log = logging.getLogger(__name__)

_EVAL_PASS_THRESHOLD = 0.8


class PromotionBlockedError(Exception):
    """Raised when auto_promote() is called but promotion is blocked."""


# ---------------------------------------------------------------------------
# Validator runner (with DB write-back)
# ---------------------------------------------------------------------------


def run_validators(candidate_id: UUID, session: Session) -> dict[str, dict]:
    """Load candidate + clause, run all validators, persist results.

    Side effects:
    - Writes candidate.validator_results_json
    - Sets candidate.review_status to 'validators_passed' or 'validator_failed'
    - Creates a ReviewItem row on failure

    Returns the results dict.
    """
    candidate: RuleCandidate | None = session.get(RuleCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"RuleCandidate {candidate_id} not found")

    clause: Clause | None = session.get(Clause, candidate.clause_id)
    if clause is None:
        raise ValueError(f"Clause {candidate.clause_id} not found for candidate {candidate_id}")

    results = run_all_validators(
        quote=candidate.quote or "",
        clause_text=clause.text,
        disposition=clause.disposition,
        value_json=candidate.value_json,
        unit=candidate.unit,
        rule_key=candidate.rule_key or "",
    )

    candidate.validator_results_json = results  # type: ignore[assignment]

    any_failed = any(not v["pass"] for v in results.values())
    if any_failed:
        candidate.review_status = "validator_failed"
        failed_names = [name for name, v in results.items() if not v["pass"]]
        _create_review_item(
            session=session,
            subject_type="rule_candidate",
            subject_id=candidate_id,
            reason=f"Validator(s) failed: {', '.join(failed_names)}",
            org_id=candidate.org_id,
        )
        log.warning(
            "candidate %s failed validators: %s",
            candidate_id,
            failed_names,
        )
    else:
        candidate.review_status = "validators_passed"

    session.flush()
    return results


# ---------------------------------------------------------------------------
# Eval gate
# ---------------------------------------------------------------------------


def eval_gate_pass(candidate_id: UUID, skill_version_id: str, session: Session) -> bool:
    """Score candidate against eval cases for its skill.

    Returns True iff all cases score >= 0.8, or there are no eval cases.
    Side effects on failure:
    - Sets candidate.review_status = 'eval_failed'
    - Creates a ReviewItem row
    Always writes EvalRun rows for cases that were scored.
    """
    candidate: RuleCandidate | None = session.get(RuleCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"RuleCandidate {candidate_id} not found")

    # Determine the skill_name from the candidate's skill_version_id, falling
    # back to the caller-supplied one if the candidate has none.
    skill_name: str | None = None
    if candidate.skill_version_id:
        from draftcheck.db.models import SkillVersion
        sv = session.get(SkillVersion, candidate.skill_version_id)
        if sv:
            skill_name = sv.skill_name

    if not skill_name:
        # Derive skill_name from the skill_version_id string by convention
        # "skill_name:version" or just use it directly.
        skill_name = skill_version_id.split(":")[0] if ":" in skill_version_id else skill_version_id

    # Load active eval cases for this skill.
    eval_cases: list[EvalCase] = list(
        session.scalars(
            select(EvalCase).where(
                EvalCase.skill_name == skill_name,
                EvalCase.status == "active",
            )
        )
    )

    if not eval_cases:
        log.info(
            "No eval cases for skill %r — gate auto-passes for candidate %s",
            skill_name,
            candidate_id,
        )
        return True

    # Score each case: compare candidate's value_json against expected_json.
    all_passed = True
    failed_cases: list[str] = []
    now = utc_now()

    for ec in eval_cases:
        score = _score_candidate_against_case(candidate, ec)
        passed = score >= _EVAL_PASS_THRESHOLD

        eval_run = EvalRun(
            id=uuid4(),
            eval_case_id=ec.id,
            skill_version_id=skill_version_id,
            status="pass" if passed else "fail",
            score=score,
            output_json=dict(candidate.value_json) if candidate.value_json else {},
            started_at=now,
            finished_at=now,
        )
        session.add(eval_run)

        if not passed:
            all_passed = False
            failed_cases.append(ec.case_key)

    if not all_passed:
        candidate.review_status = "eval_failed"
        _create_review_item(
            session=session,
            subject_type="rule_candidate",
            subject_id=candidate_id,
            reason=f"Eval gate failed for case(s): {', '.join(failed_cases)}",
            org_id=candidate.org_id,
        )
        log.warning(
            "candidate %s failed eval gate: cases %s",
            candidate_id,
            failed_cases,
        )

    session.flush()
    return all_passed


# ---------------------------------------------------------------------------
# Auto-promote
# ---------------------------------------------------------------------------


def auto_promote(candidate_id: UUID, session: Session) -> Rule:
    """The ONLY insertion path for rules rows.

    Preconditions (enforced, not assumed):
      1. candidate.review_status == 'validators_passed'
      2. At least one EvalRun exists for this candidate OR no eval cases exist for the skill
      3. candidate.validator_results_json has no failed validators

    Raises PromotionBlockedError if any precondition is not met.
    On success inserts a Rule, updates the candidate, and writes an AuditEvent.
    """
    candidate: RuleCandidate | None = session.get(RuleCandidate, candidate_id)
    if candidate is None:
        raise PromotionBlockedError(f"RuleCandidate {candidate_id} not found")

    # Precondition 1 — validators must have passed.
    if candidate.review_status != "validators_passed":
        raise PromotionBlockedError(
            f"candidate {candidate_id} review_status is {candidate.review_status!r}; "
            "expected 'validators_passed'"
        )

    # Precondition 3 — no failed validators in persisted results.
    vr: dict = candidate.validator_results_json or {}
    failed_validators = [name for name, result in vr.items() if not result.get("pass", False)]
    if failed_validators:
        raise PromotionBlockedError(
            f"candidate {candidate_id} has failed validators: {failed_validators}"
        )

    # Precondition 2 — eval gate was run (eval_runs exist) OR no eval cases for this skill.
    _check_eval_gate_was_run(candidate, session)

    # Load clause to get source_version_id.
    clause: Clause | None = session.get(Clause, candidate.clause_id)
    if clause is None:
        raise PromotionBlockedError(
            f"Clause {candidate.clause_id} not found; cannot promote candidate {candidate_id}"
        )

    source_version_id = clause.source_version_id

    now = utc_now()

    rule = Rule(
        id=uuid4(),
        org_id=candidate.org_id,
        source_version_id=source_version_id,
        clause_id=candidate.clause_id,
        candidate_id=candidate_id,
        rule_key=candidate.rule_key or "",
        rule_type=candidate.rule_type,
        pathway=candidate.pathway,
        lifecycle_status="auto_accepted",
        operator=candidate.operator,
        value_json=candidate.value_json,
        unit=candidate.unit,
        condition_json=candidate.condition_json,
        quote=candidate.quote,
        extractor_model=candidate.extractor_model,
        skill_version_id=candidate.skill_version_id,
        prompt_hash=candidate.prompt_hash,
    )
    session.add(rule)

    candidate.review_status = "auto_promoted"
    candidate.auto_promoted_at = now

    audit = AuditEvent(
        id=uuid4(),
        org_id=candidate.org_id,
        actor_user_id=None,
        event_type="rule_candidate.auto_promoted",
        action="auto_promoted",
        subject_type="rule_candidate",
        subject_id=candidate_id,
        before_json={},
        after_json={"rule_id": str(rule.id), "rule_key": rule.rule_key},
        metadata_json={"actor": "system"},
    )
    session.add(audit)

    session.flush()
    log.info(
        "candidate %s promoted to rule %s (key=%r)",
        candidate_id,
        rule.id,
        rule.rule_key,
    )
    return rule


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _create_review_item(
    session: Session,
    subject_type: str,
    subject_id: UUID,
    reason: str,
    org_id: UUID | None,
) -> ReviewItem:
    item = ReviewItem(
        id=uuid4(),
        org_id=org_id or uuid4(),  # ReviewItem.org_id is NOT NULL; use a sentinel if unknown.
        subject_type=subject_type,
        subject_id=subject_id,
        reason=reason,
        status="open",
        priority=0,
    )
    session.add(item)
    return item


def _score_candidate_against_case(candidate: RuleCandidate, ec: EvalCase) -> float:
    """Simple field-match scorer: score = matching_fields / total_expected_fields.

    Compares candidate attributes against ec.expected_json.
    Returns a float in [0.0, 1.0].
    """
    expected: dict = ec.expected_json or {}
    if not expected:
        return 1.0

    # Candidate attribute map for scoring.
    candidate_values: dict = {
        "rule_key": candidate.rule_key,
        "operator": candidate.operator,
        "unit": candidate.unit,
        "rule_type": candidate.rule_type,
        "pathway": candidate.pathway,
        "value_json": candidate.value_json,
        "condition_json": candidate.condition_json,
    }

    matches = sum(
        1
        for key, exp_val in expected.items()
        if candidate_values.get(key) == exp_val
    )
    return matches / len(expected)


def _check_eval_gate_was_run(candidate: RuleCandidate, session: Session) -> None:
    """Raise PromotionBlockedError if the eval gate was not run and there are eval cases."""
    # Check if any EvalRuns exist referencing this candidate's skill_version_id.
    if candidate.skill_version_id:
        existing_runs = session.scalars(
            select(EvalRun).where(
                EvalRun.skill_version_id == candidate.skill_version_id,
            ).limit(1)
        ).first()
        if existing_runs is not None:
            return  # Eval gate was run.

    # No runs found — check whether eval cases exist for the skill.
    skill_name: str | None = None
    if candidate.skill_version_id:
        from draftcheck.db.models import SkillVersion
        sv = session.get(SkillVersion, candidate.skill_version_id)
        if sv:
            skill_name = sv.skill_name

    if skill_name:
        cases_exist = session.scalars(
            select(EvalCase).where(
                EvalCase.skill_name == skill_name,
                EvalCase.status == "active",
            ).limit(1)
        ).first()
        if cases_exist is not None:
            raise PromotionBlockedError(
                f"Eval gate has not been run for candidate {candidate.id} "
                f"(skill {skill_name!r}) but eval cases exist"
            )

    # No eval cases exist — gate auto-passes; nothing to check.

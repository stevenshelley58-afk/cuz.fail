"""Extraction job functions for Stage 3.

These are plain async functions.  Procrastinate enqueueing is wired in Phase 5;
for now they are called directly from tests and the API layer.

Adjudication logic (run_extraction_group):
  - 3/3 agree on (rule_key, operator, value_json, unit) → auto-promote first candidate.
  - 2/3 agree → challenge round on the dissenter → if its re-run concedes, auto-promote.
  - Otherwise → all candidates remain pending_review.

"Agree" is defined as identical (rule_key, operator, str(value_json), unit) tuples.

Auto-promotion writes lifecycle_status='pending_review' on the promoted Rule;
it does NOT write lifecycle_status='approved'.  Approval is always an operator action.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from draftcheck.ai.substrate import ModelAdapter, ModelRequest
from draftcheck.db.models import Rule, RuleCandidate


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_NUMERIC_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([a-zA-Z%]*)")
_NORMATIVE_RE = re.compile(
    r"\b(must|shall|required|maximum|minimum|not exceed|not less than"
    r"|no more than|at least|shall not|must not|prohibited|permitted)\b",
    re.IGNORECASE,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _stub_extract(prompt: str, clause_text: str, pass_number: int) -> dict[str, Any]:
    """Deterministic extraction stub for Stage 3 (no LLM call).

    Parses the first numeric value found in the clause text and returns a
    plausible extraction dict.  Phase 6 replaces this with real LLM parsing.
    """
    numbers = _NUMERIC_RE.findall(clause_text)
    operator = "lte"
    value = None
    unit = None

    # Derive operator from normative context
    lower = clause_text.lower()
    if any(w in lower for w in ("must not exceed", "not exceed", "maximum", "no more than")):
        operator = "lte"
    elif any(w in lower for w in ("must be at least", "not less than", "minimum", "at least")):
        operator = "gte"
    elif "must be" in lower or "shall be" in lower:
        operator = "eq"

    if numbers:
        raw_value, raw_unit = numbers[0]
        value = float(raw_value) if "." in raw_value else int(raw_value)
        unit = raw_unit.strip() or None

    # Derive a simple rule_key from the first normative word + value
    rule_key_parts = []
    m = _NORMATIVE_RE.search(clause_text)
    if m:
        rule_key_parts.append(m.group(1).lower().replace(" ", "_"))
    if value is not None:
        rule_key_parts.append(str(value))
    rule_key = "_".join(rule_key_parts) or f"extracted_rule_pass{pass_number}"

    rule_type = "requirement"
    confidence = 0.55 + pass_number * 0.05  # 0.60 / 0.65 / 0.70 per pass

    return {
        "rule_key": rule_key,
        "operator": operator,
        "value_json": {"value": value} if value is not None else {},
        "unit": unit,
        "condition_json": {},
        "quote": clause_text[:300],
        "rule_type": rule_type,
        "confidence": round(confidence, 4),
    }


def _agreement_key(candidate: RuleCandidate) -> tuple[str | None, str | None, str, str | None]:
    return (
        candidate.rule_key,
        candidate.operator,
        str(candidate.value_json),
        candidate.unit,
    )


def _apply_extraction(candidate: RuleCandidate, extraction: dict[str, Any]) -> None:
    candidate.rule_key = extraction.get("rule_key")
    candidate.operator = extraction.get("operator")
    candidate.value_json = extraction.get("value_json", {})
    candidate.unit = extraction.get("unit")
    candidate.condition_json = extraction.get("condition_json", {})
    candidate.quote = extraction.get("quote", candidate.quote)
    candidate.rule_type = extraction.get("rule_type", "requirement")
    candidate.confidence = extraction.get("confidence")


# ---------------------------------------------------------------------------
# Public job functions
# ---------------------------------------------------------------------------


async def run_extraction_pass(
    candidate_id: UUID,
    clause_text: str,
    skill_version_id: str,
    adapter: ModelAdapter,
    session: Session,
) -> dict[str, Any]:
    """Run one extraction pass for a single RuleCandidate.

    Calls the adapter (which records a job trace), writes extraction fields onto
    the candidate row, and returns the raw extraction output dict.
    Does NOT run validators — caller is responsible.
    """
    candidate = session.get(RuleCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"candidate {candidate_id} not found")

    pass_number = candidate.extraction_pass or 1
    prompt = (
        f"extract_rules skill v={skill_version_id} pass={pass_number}\n"
        f"clause_id={candidate.clause_id}\n"
        f"text={clause_text[:2000]}"
    )

    response = adapter.complete(
        ModelRequest(
            job_id=f"extract_{candidate_id.hex}_p{pass_number}",
            job_type="extract_rules",
            skill_version_id=skill_version_id,
            prompt=prompt,
            max_output_tokens=256,
        )
    )

    # Stub extraction (Stage 3).  Phase 6 parses response.text from real LLM.
    extraction = _stub_extract(prompt, clause_text, pass_number)

    _apply_extraction(candidate, extraction)
    candidate.extractor_model = adapter.model if hasattr(adapter, "model") else "deterministic-substrate-v0"
    candidate.prompt_hash = response.trace_id  # reuse trace_id as a proxy hash for now
    candidate.review_status = "pending_review"
    session.flush()

    return extraction


async def run_extraction_group(
    group_id: UUID,
    adapter: ModelAdapter,
    session: Session,
    gate_fn: Any = None,
) -> list[UUID]:
    """Run all 3 extraction passes for a group, then adjudicate.

    Returns list of promoted Rule IDs (may be empty if no auto-promotion occurred).

    Adjudication:
      - 3/3 agree → auto-promote first candidate, return its promoted rule_id.
      - 2/3 agree → challenge the dissenting candidate with a re-run.
        If dissenter concedes (result agrees with majority) → auto-promote.
        Otherwise → all pending_review, return [].
      - <2/3 agree → all pending_review, return [].

    gate_fn: optional callable(candidate_id, skill_version_id, session) → bool.
      If provided, called before promoting a candidate.  If it returns False,
      the candidate is not promoted and remains pending_review.
    """
    from sqlalchemy import select

    stmt = (
        select(RuleCandidate)
        .where(
            RuleCandidate.extraction_group_id == group_id,
            RuleCandidate.extraction_pass.in_([1, 2, 3]),
        )
        .order_by(RuleCandidate.extraction_pass)
    )
    candidates = list(session.scalars(stmt))
    if not candidates:
        raise ValueError(f"no candidates found for group {group_id}")

    # Fetch the clause text once.
    first = candidates[0]
    from draftcheck.db.models import Clause

    clause = session.get(Clause, first.clause_id)
    clause_text = clause.text if clause else ""
    skill_version_id = first.skill_version_id or "extract_rules-v0"

    # Run all passes.
    for candidate in candidates:
        await run_extraction_pass(
            candidate_id=candidate.id,
            clause_text=clause_text,
            skill_version_id=skill_version_id,
            adapter=adapter,
            session=session,
        )
        # Re-load after flush.
        session.refresh(candidate)

    # Adjudication.
    keys = [_agreement_key(c) for c in candidates]
    counts: Counter[tuple] = Counter(keys)
    majority_key, majority_count = counts.most_common(1)[0]

    if majority_count == 3:
        # 3/3 agree.
        winner = candidates[0]
        return _maybe_promote(winner, skill_version_id, adapter, session, gate_fn)

    if majority_count == 2:
        # 2/3 agree — find dissenter and challenge.
        dissenters = [c for c in candidates if _agreement_key(c) != majority_key]
        if dissenters:
            dissenter = dissenters[0]
            await run_extraction_pass(
                candidate_id=dissenter.id,
                clause_text=clause_text,
                skill_version_id=skill_version_id,
                adapter=adapter,
                session=session,
            )
            session.refresh(dissenter)
            if _agreement_key(dissenter) == majority_key:
                # Dissenter conceded — promote the majority winner.
                majority_candidates = [c for c in candidates if _agreement_key(c) == majority_key]
                winner = majority_candidates[0]
                return _maybe_promote(winner, skill_version_id, adapter, session, gate_fn)

    # No consensus — leave all as pending_review.
    return []


def _maybe_promote(
    candidate: RuleCandidate,
    skill_version_id: str,
    adapter: ModelAdapter,
    session: Session,
    gate_fn: Any,
) -> list[UUID]:
    """Promote a candidate to a Rule row if gate_fn allows.

    Returns list with the new Rule UUID, or [] if gate blocked it.
    """
    if gate_fn is not None:
        try:
            allowed = gate_fn(candidate.id, skill_version_id, session)
        except Exception:
            allowed = False
        if not allowed:
            return []

    rule = Rule(
        id=uuid4(),
        org_id=candidate.org_id,
        source_version_id=candidate.source_version_id,
        clause_id=candidate.clause_id,
        candidate_id=candidate.id,
        rule_key=candidate.rule_key or f"auto_{candidate.id.hex[:8]}",
        rule_type=candidate.rule_type,
        pathway=candidate.pathway,
        lifecycle_status="pending_review",  # NEVER 'approved' — operator must approve
        operator=candidate.operator,
        value_json=candidate.value_json,
        unit=candidate.unit,
        condition_json=candidate.condition_json,
        quote=candidate.quote,
        extractor_model=candidate.extractor_model,
        skill_version_id=candidate.skill_version_id,
        prompt_hash=candidate.prompt_hash,
        metadata_json={"auto_promoted": True},
    )
    session.add(rule)

    candidate.review_status = "auto_promoted"
    candidate.auto_promoted_at = _utc_now()
    session.flush()

    return [rule.id]

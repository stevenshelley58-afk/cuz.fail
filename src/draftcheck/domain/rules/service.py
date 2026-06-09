"""Rules domain services for Stage 3.

Design invariants (must all hold):
  1. Disposition values: "rule_bearing", "definition", "procedural",
     "informational", "not_applicable", "manual_review".
  2. Only rule_bearing clauses get extraction enqueued.
  3. Every model call goes through the adapter (ModelRequest → adapter.complete()
     → in-memory JobTrace written by the adapter).  No raw LLM calls here.
  4. approve_rule, reject_candidate, and reject_rule require the actor to have
     role=owner (the only operator-level role in V3).
  5. Every lifecycle transition writes an AuditEvent row.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck.ai.substrate import ModelAdapter, ModelRequest
from draftcheck.db.models import AuditEvent, Clause, Rule, RuleCandidate, User


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_DISPOSITIONS = frozenset(
    {
        "rule_bearing",
        "definition",       # plan vocabulary (was "definitional")
        "procedural",
        "informational",
        "not_applicable",
        "manual_review",
    }
)

# Words that strongly indicate normative (rule-bearing) content.
_NORMATIVE_RE = re.compile(
    r"\b(must|shall|required|maximum|minimum|not exceed|not less than"
    r"|no more than|at least|shall not|must not|prohibited|permitted)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_from_text(text: str) -> str:
    """Deterministic stub classification based on normative word detection."""
    if _NORMATIVE_RE.search(text):
        return "rule_bearing"
    lower = text.lower()
    if any(w in lower for w in ("means", "definition", "defined as", "refers to")):
        return "definition"
    if any(w in lower for w in ("procedure", "process", "step", "application", "lodgement")):
        return "procedural"
    return "informational"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_operator(actor_id: UUID, session: Session) -> User:
    """Load the actor user and verify they are an operator-level role (owner).

    Raises PermissionError if the actor is not found or lacks operator access.
    """
    user = session.get(User, actor_id)
    if user is None:
        raise PermissionError(f"actor {actor_id} not found")
    # In V3 IdentityRole only has OWNER; owner == operator.
    if str(user.role) != "owner":
        raise PermissionError(
            f"actor {actor_id} has role '{user.role}'; operator (owner) required"
        )
    return user


# ---------------------------------------------------------------------------
# Clause classification
# ---------------------------------------------------------------------------


def classify_clause(
    clause_id: UUID,
    skill_version_id: str,
    adapter: ModelAdapter,
    session: Session,
) -> str:
    """Run classify_clauses skill on a clause.

    Updates clause.disposition and clause.classification_skill_version_id.
    Writes a job_trace via adapter (the LocalDeterministicModelAdapter records
    its own in-memory trace; Phase 6 will persist to job_traces table).
    Returns disposition string.
    """
    clause = session.get(Clause, clause_id)
    if clause is None:
        raise ValueError(f"clause {clause_id} not found")

    prompt = (
        f"classify_clauses skill v={skill_version_id}\n"
        f"clause_key={clause.clause_key}\n"
        f"text={clause.text[:2000]}"
    )
    response = adapter.complete(
        ModelRequest(
            job_id=f"classify_{clause_id.hex}",
            job_type="classify_clauses",
            skill_version_id=skill_version_id,
            prompt=prompt,
            max_output_tokens=32,
        )
    )

    # Deterministic classification from clause text (stub for Stage 3).
    # Phase 6 will parse the real LLM response instead.
    disposition = _classify_from_text(clause.text)

    clause.disposition = disposition
    clause.classification_skill_version_id = skill_version_id
    session.flush()

    # Suppress unused variable — trace_id is available if callers want it.
    _ = response.trace_id
    return disposition


# ---------------------------------------------------------------------------
# Extraction group enqueueing
# ---------------------------------------------------------------------------


def enqueue_extraction_group(
    clause_id: UUID,
    skill_version_id: str,
    session: Session,
) -> UUID:
    """Create 3 RuleCandidate rows for extraction passes 1, 2, 3.

    Invariant: only call for rule_bearing clauses.  This function checks and
    raises ValueError if the clause is not rule_bearing.

    Returns the shared extraction_group_id UUID.
    """
    clause = session.get(Clause, clause_id)
    if clause is None:
        raise ValueError(f"clause {clause_id} not found")
    if clause.disposition != "rule_bearing":
        raise ValueError(
            f"clause {clause_id} has disposition '{clause.disposition}'; "
            "only rule_bearing clauses can be enqueued for extraction"
        )

    group_id = uuid4()

    for pass_number in (1, 2, 3):
        candidate = RuleCandidate(
            id=uuid4(),
            source_version_id=clause.source_version_id,
            clause_id=clause_id,
            source_chunk_id=clause.source_chunk_id,
            review_status="pending_extraction",
            extraction_group_id=group_id,
            extraction_pass=pass_number,
            skill_version_id=skill_version_id,
            quote=clause.quote or clause.text[:500],
            rule_type="requirement",
            pathway="none",
            value_json={},
            condition_json={},
        )
        session.add(candidate)

    session.flush()
    return group_id


# ---------------------------------------------------------------------------
# Rule read operations
# ---------------------------------------------------------------------------


def get_rule(rule_id: UUID, session: Session) -> Rule | None:
    return session.get(Rule, rule_id)


def list_rules(
    session: Session,
    lifecycle_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Rule]:
    stmt = select(Rule)
    if lifecycle_status is not None:
        stmt = stmt.where(Rule.lifecycle_status == lifecycle_status)
    stmt = stmt.order_by(Rule.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt))


def get_candidate(candidate_id: UUID, session: Session) -> RuleCandidate | None:
    return session.get(RuleCandidate, candidate_id)


def list_candidates(
    session: Session,
    clause_id: UUID | None = None,
    review_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RuleCandidate]:
    stmt = select(RuleCandidate)
    if clause_id is not None:
        stmt = stmt.where(RuleCandidate.clause_id == clause_id)
    if review_status is not None:
        stmt = stmt.where(RuleCandidate.review_status == review_status)
    stmt = stmt.order_by(RuleCandidate.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt))


# ---------------------------------------------------------------------------
# Operator-only mutation operations
# ---------------------------------------------------------------------------


def reject_candidate(
    candidate_id: UUID,
    actor_id: UUID,
    session: Session,
) -> RuleCandidate:
    """Set review_status='rejected' on a RuleCandidate.

    Invariant: actor must have role=owner (operator).
    Writes an AuditEvent row.
    """
    actor = _require_operator(actor_id, session)

    candidate = session.get(RuleCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"candidate {candidate_id} not found")

    before_status = candidate.review_status
    candidate.review_status = "rejected"
    candidate.reviewed_by_user_id = actor_id
    candidate.reviewed_at = _utc_now()

    audit = AuditEvent(
        id=uuid4(),
        org_id=actor.org_id,
        actor_user_id=actor_id,
        event_type="rule_candidate.rejected",
        action="reject",
        subject_type="rule_candidate",
        subject_id=candidate_id,
        before_json={"review_status": before_status},
        after_json={"review_status": "rejected"},
        metadata_json={},
    )
    session.add(audit)
    session.flush()
    return candidate


def reject_rule(
    rule_id: UUID,
    actor_id: UUID,
    reason: str,
    session: Session,
) -> Rule:
    """Set lifecycle_status='rejected' on a Rule.

    Invariant: actor must have role=owner (operator).
    Writes an AuditEvent row.
    Never sets lifecycle_status='approved' — that path does not exist in this service.
    """
    actor = _require_operator(actor_id, session)

    rule = session.get(Rule, rule_id)
    if rule is None:
        raise ValueError(f"rule {rule_id} not found")
    if not reason or not reason.strip():
        raise ValueError("reason is required when rejecting a rule")

    before_status = rule.lifecycle_status
    rule.lifecycle_status = "rejected"
    rule.metadata_json = {**rule.metadata_json, "rejection_reason": reason.strip()}

    audit = AuditEvent(
        id=uuid4(),
        org_id=actor.org_id,
        actor_user_id=actor_id,
        event_type="rule.rejected",
        action="reject",
        subject_type="rule",
        subject_id=rule_id,
        before_json={"lifecycle_status": before_status},
        after_json={"lifecycle_status": "rejected", "reason": reason.strip()},
        metadata_json={},
    )
    session.add(audit)
    session.flush()
    return rule


def approve_rule(
    rule_id: UUID,
    actor_id: UUID,
    reason: str,
    session: Session,
) -> Rule:
    """Set lifecycle_status='approved' on a Rule.

    Invariant: actor must have role=owner (operator).
    Writes an AuditEvent row.  Idempotent if already approved.
    """
    actor = _require_operator(actor_id, session)

    rule = session.get(Rule, rule_id)
    if rule is None:
        raise ValueError(f"rule {rule_id} not found")

    if rule.lifecycle_status == "approved":
        return rule  # idempotent

    before_status = rule.lifecycle_status
    rule.lifecycle_status = "approved"

    audit = AuditEvent(
        id=uuid4(),
        org_id=actor.org_id,
        actor_user_id=actor_id,
        event_type="rule.approved",
        action="approve",
        subject_type="rule",
        subject_id=rule_id,
        before_json={"lifecycle_status": before_status},
        after_json={"lifecycle_status": "approved", "reason": (reason or "").strip()},
        metadata_json={},
    )
    session.add(audit)
    session.flush()
    return rule

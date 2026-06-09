"""Deterministic compliance engine for DraftCheck WA.

The engine loads approved rules, looks up measured PropertyFacts, and
produces advisory results.  It never hardcodes thresholds — every
threshold value and citation comes from an approved Rule row.

Output statuses:
  likely_pass       — measured value satisfies the rule's operator/threshold
  likely_fail       — measured value violates the rule's operator/threshold
  needs_more_info   — no PropertyFact available for the measurement
  unsupported       — no approved rule covers this check key for this project
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from draftcheck.checks.registry import TIER1_CHECKS
from draftcheck.db.models import (
    CheckResult,
    CheckRun,
    Project,
    PropertyFact,
    ResolvedRule,
    Rule,
)

logger = logging.getLogger(__name__)

ENGINE_VERSION = "1.0.0"

# Operators supported by Rule.operator
_OPERATORS: dict[str, Any] = {
    "lte": lambda measured, threshold: float(measured) <= float(threshold),
    "gte": lambda measured, threshold: float(measured) >= float(threshold),
    "lt":  lambda measured, threshold: float(measured) <  float(threshold),
    "gt":  lambda measured, threshold: float(measured) >  float(threshold),
    "eq":  lambda measured, threshold: float(measured) == float(threshold),
}


@dataclass
class CheckResultItem:
    """Advisory result for a single Tier-1 check."""

    check_key: str
    status: str  # likely_pass | likely_fail | needs_more_info | unsupported
    threshold_value: float | None
    threshold_unit: str | None
    measured_value: float | None
    rule_id: str | None
    rule_quote: str | None
    citation: str | None
    note: str | None = None


@dataclass
class CheckRunResult:
    """Container returned by ComplianceEngine.run_check."""

    check_run_id: str
    project_id: str
    org_id: str
    status: str
    results: list[CheckResultItem] = field(default_factory=list)


def _extract_numeric(value_json: dict[str, object] | None) -> float | None:
    """Pull a numeric value from a PropertyFact value_json dict."""
    if value_json is None:
        return None
    raw = value_json.get("value")
    if raw is None:
        return None
    try:
        return float(str(raw))
    except (TypeError, ValueError):
        return None


def _rule_pack_hash(rules: list[Rule]) -> str:
    """Stable hash of the rule ids in this pack for audit tracing."""
    ids = sorted(str(r.id) for r in rules)
    return hashlib.sha256("|".join(ids).encode()).hexdigest()


class ComplianceEngine:
    """Run Tier-1 deterministic compliance checks against approved rules.

    Usage::

        engine = ComplianceEngine()
        result = engine.run_check(project_id="...", org_id="...", session=db)
    """

    def run_check(
        self,
        project_id: str,
        org_id: str,
        session: Session,
    ) -> CheckRunResult:
        """Execute all Tier-1 checks and return a CheckRunResult.

        The caller is responsible for committing/rolling back the session.
        """
        # ------------------------------------------------------------------
        # 1. Verify project exists
        # ------------------------------------------------------------------
        project: Project | None = session.get(Project, UUID(project_id))
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        # ------------------------------------------------------------------
        # 2. Load approved rules scoped to this project's council
        # ------------------------------------------------------------------
        council_scope: str | None = None
        if isinstance(project.metadata_json, dict):
            raw = project.metadata_json.get("council_scope")
            council_scope = str(raw) if raw is not None else None

        rules: list[Rule] = (
            session.query(Rule)
            .filter(Rule.lifecycle_status == "approved")
            .all()
        )

        # Build lookup: rule_key -> Rule (last approved wins on key collision)
        rule_by_key: dict[str, Rule] = {}
        for _r in rules:
            if _r.rule_key:
                rule_by_key[_r.rule_key] = _r

        # ------------------------------------------------------------------
        # 3. Load PropertyFacts for this project
        # ------------------------------------------------------------------
        facts: list[PropertyFact] = (
            session.query(PropertyFact)
            .filter(
                PropertyFact.project_id == UUID(project_id),
                PropertyFact.promoted_to_measurement == True,  # noqa: E712
                PropertyFact.review_status == "confirmed",
            )
            .all()
        )
        # Build lookup: fact_type -> PropertyFact (most-recent wins)
        fact_by_type: dict[str, PropertyFact] = {}
        for fact in sorted(facts, key=lambda f: f.created_at):
            fact_by_type[fact.fact_type] = fact

        # ------------------------------------------------------------------
        # 4. Create the CheckRun record
        # ------------------------------------------------------------------
        pack_hash = _rule_pack_hash(rules) if rules else None
        source_version_ids = list(
            {str(r.source_version_id) for r in rules if r.source_version_id}
        )

        check_run = CheckRun(
            org_id=UUID(org_id),
            project_id=UUID(project_id),
            as_of_date=datetime.now(UTC),
            status="running",
            rule_pack_hash=pack_hash,
            source_version_ids_json=source_version_ids,
            engine_version=ENGINE_VERSION,
            started_at=datetime.now(UTC),
        )
        session.add(check_run)
        session.flush()  # obtain check_run.id

        # ------------------------------------------------------------------
        # 5. Evaluate each Tier-1 check key
        # ------------------------------------------------------------------
        results: list[CheckResultItem] = []
        any_fail = False
        any_missing = False

        for check_def in TIER1_CHECKS:
            check_key = check_def.key
            # Find matching rule
            rule: Rule | None = rule_by_key.get(check_key)

            if rule is None:
                # No approved rule covers this check for this context
                item = CheckResultItem(
                    check_key=check_key,
                    status="unsupported",
                    threshold_value=None,
                    threshold_unit=None,
                    measured_value=None,
                    rule_id=None,
                    rule_quote=None,
                    citation=None,
                    note="No approved rule found for this check key",
                )
                results.append(item)
                continue

            # Extract threshold from rule.value_json
            threshold_raw = rule.value_json.get("value") if isinstance(rule.value_json, dict) else None
            threshold_value: float | None = None
            if threshold_raw is not None:
                try:
                    threshold_value = float(str(threshold_raw))
                except (TypeError, ValueError):
                    threshold_value = None

            # Find the PropertyFact for this check
            fact_keys = list(check_def.fact_keys)
            measured_value: float | None = None
            matched_fact: PropertyFact | None = None
            for fk in fact_keys:
                if fk in fact_by_type:
                    matched_fact = fact_by_type[fk]
                    measured_value = _extract_numeric(
                        matched_fact.value_json
                        if isinstance(matched_fact.value_json, dict)
                        else {"value": matched_fact.value_json}
                    )
                    break

            # Build citation string from rule
            citation = _build_citation(rule)

            # Assumption-backed facts must not produce definitive pass/fail.
            if matched_fact and matched_fact.method == "assumption":
                item = CheckResultItem(
                    check_key=check_key,
                    status="needs_more_info",
                    threshold_value=threshold_value,
                    threshold_unit=rule.unit,
                    measured_value=measured_value,
                    rule_id=str(rule.id),
                    rule_quote=rule.quote,
                    citation=citation,
                    note="Fact sourced from assumption; confirmation required before compliance use",
                )
                results.append(item)
                any_missing = True
                continue

            if measured_value is None:
                status = "needs_more_info"
                note = f"No measurement provided (expected fact_type in: {fact_keys})"
                any_missing = True
            elif threshold_value is None:
                status = "needs_more_info"
                note = "Rule threshold value is missing or non-numeric"
                any_missing = True
            else:
                operator = rule.operator or "lte"
                op_fn = _OPERATORS.get(operator)
                if op_fn is None:
                    status = "needs_more_info"
                    note = f"Unknown operator '{operator}' in rule"
                    any_missing = True
                else:
                    try:
                        passes = op_fn(measured_value, threshold_value)
                    except Exception as exc:
                        logger.warning("Operator evaluation error for %s: %s", check_key, exc)
                        status = "needs_more_info"
                        note = f"Evaluation error: {exc}"
                        any_missing = True
                    else:
                        status = "likely_pass" if passes else "likely_fail"
                        note = None
                        if not passes:
                            any_fail = True

            item = CheckResultItem(
                check_key=check_key,
                status=status,
                threshold_value=threshold_value,
                threshold_unit=rule.unit,
                measured_value=measured_value,
                rule_id=str(rule.id),
                rule_quote=rule.quote,
                citation=citation,
                note=note,
            )
            results.append(item)

            # ------------------------------------------------------------------
            # 6. Persist ResolvedRule + CheckResult rows
            # ------------------------------------------------------------------
            resolved_rule = ResolvedRule(
                org_id=UUID(org_id),
                project_id=UUID(project_id),
                check_run_id=check_run.id,
                rule_id=rule.id,
                rule_key=check_key,
                applicability_status="applicable",
                pathway=rule.pathway or "none",
                rule_snapshot_json={
                    "rule_key": rule.rule_key,
                    "operator": rule.operator,
                    "value_json": rule.value_json,
                    "unit": rule.unit,
                    "quote": rule.quote,
                    "lifecycle_status": rule.lifecycle_status,
                    "source_version_id": str(rule.source_version_id),
                },
                selection_trace_json={
                    "engine_version": ENGINE_VERSION,
                    "matched_on": "rule_key",
                    "council_scope": council_scope,
                },
                citations_json=[citation] if citation else [],
            )
            session.add(resolved_rule)
            session.flush()

            check_result = CheckResult(
                org_id=UUID(org_id),
                project_id=UUID(project_id),
                check_run_id=check_run.id,
                resolved_rule_id=resolved_rule.id,
                check_key=check_key,
                status=status,
                requirement_json={
                    "threshold_value": threshold_value,
                    "threshold_unit": rule.unit,
                    "operator": rule.operator,
                    "rule_id": str(rule.id),
                },
                proposed_json={
                    "measured_value": measured_value,
                    "fact_keys_checked": fact_keys,
                },
                why_this_applies=rule.quote,
                citations_json=[citation] if citation else [],
                decision_trace_json={
                    "engine_version": ENGINE_VERSION,
                    "operator": rule.operator,
                    "threshold": threshold_value,
                    "measured": measured_value,
                    "result": status,
                    "note": note,
                },
                pathway_note=rule.pathway if rule.pathway != "none" else None,
            )
            session.add(check_result)

        # ------------------------------------------------------------------
        # 7. Update CheckRun status
        # ------------------------------------------------------------------
        overall_status: str
        if any_fail:
            overall_status = "has_likely_failures"
        elif any_missing:
            overall_status = "incomplete"
        else:
            overall_status = "likely_compliant"

        check_run.status = overall_status
        check_run.completed_at = datetime.now(UTC)
        session.flush()

        return CheckRunResult(
            check_run_id=str(check_run.id),
            project_id=project_id,
            org_id=org_id,
            status=overall_status,
            results=results,
        )


def _build_citation(rule: Rule) -> str | None:
    """Construct a short citation string from the rule's source version."""
    parts: list[str] = []
    if rule.rule_key:
        parts.append(rule.rule_key)
    if rule.source_version_id:
        parts.append(f"source_version:{rule.source_version_id}")
    return " | ".join(parts) if parts else None

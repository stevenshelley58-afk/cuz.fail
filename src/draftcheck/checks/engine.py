"""Deterministic compliance engine for LotFile.

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

from draftcheck.checks.registry import ALL_CHECKS
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

# Spelling variants written by extractors (WP6 percent atoms, legacy seeds).
_OPERATOR_ALIASES: dict[str, str] = {
    "pct_lte": "lte",
    "pct_gte": "gte",
    "<=": "lte",
    ">=": "gte",
    "<": "lt",
    ">": "gt",
    "==": "eq",
    "=": "eq",
}


def _normalize_operator(operator: str | None) -> str:
    op = (operator or "lte").strip()
    return _OPERATOR_ALIASES.get(op, op)


# Maps each Tier-1 check key to the extractor base rule keys that satisfy it,
# in preference order. WP6 rules carry value_json.base_rule_key (rule_key is
# suffixed with density/dwelling codes, e.g. "site_area.R40.grouped_dwelling").
_CHECK_TO_BASE_RULE_KEYS: dict[str, tuple[str, ...]] = {
    "setback_front": ("primary_street_setback", "front_setback"),
    "setback_rear": ("rear_setback",),
    "setback_side_primary": ("side_setback",),
    "setback_side_secondary": ("secondary_street_setback", "side_setback"),
    "site_cover": ("site_cover",),
    "open_space": ("open_space",),
    "garage_width": ("garage_width",),
    "garage_dominance": ("garage_dominance",),
    "boundary_wall_length": ("boundary_wall_length", "boundary_wall"),
}


def _base_rule_key(rule: Rule) -> str:
    if isinstance(rule.value_json, dict):
        base = rule.value_json.get("base_rule_key")
        if base:
            return str(base)
    return (rule.rule_key or "").split(".", 1)[0]


def _dwelling_type(rule: Rule) -> str:
    cond = rule.condition_json if isinstance(rule.condition_json, dict) else {}
    return str(cond.get("dwelling_type") or "any")


def _select_rule(
    rules: list[Rule],
    check_key: str,
    r_codes: list[str],
) -> Rule | None:
    """Pick the best approved rule for a check key.

    Ranking: a usable numeric threshold dominates, then an R-code-specific
    match beats a global rule, then dwelling-type-agnostic beats specific,
    then base-key preference order, then newest.
    """
    base_keys = _CHECK_TO_BASE_RULE_KEYS.get(check_key, ())
    accepted = (check_key, *base_keys)
    best: Rule | None = None
    best_rank: tuple = ()
    for rule in rules:
        base = _base_rule_key(rule)
        # Open-vocab derived checks key on canonical_rule_key (filled by
        # wp6_apply_clustering.py); the seed checks key on rule_key / base key.
        canonical = getattr(rule, "canonical_rule_key", None)
        if (
            rule.rule_key != check_key
            and base not in accepted
            and canonical != check_key
        ):
            continue
        raw = rule.value_json.get("value") if isinstance(rule.value_json, dict) else None
        try:
            has_threshold = raw is not None and float(str(raw)) == float(str(raw))
        except (TypeError, ValueError):
            has_threshold = False
        specific = bool(
            rule.applicable_r_codes
            and r_codes
            and set(r_codes) & set(rule.applicable_r_codes)
        )
        # A check's headline threshold should come from a base/standard rule, not
        # an exception modifier.  Open-vocab clustering can pull "<key>.exception_*"
        # rows into a canonical cluster; deprioritise them so the engine reports
        # the base rule's threshold (exceptions still inform legal_edges).
        is_standard = (rule.rule_type or "standard") != "exception"
        rank = (
            1 if has_threshold else 0,
            1 if is_standard else 0,
            2 if specific else (1 if not rule.applicable_r_codes else 0),
            1 if _dwelling_type(rule) == "any" else 0,
            len(accepted) - accepted.index(base if base in accepted else check_key),
            rule.created_at or datetime.min.replace(tzinfo=UTC),
        )
        if rank > best_rank:
            best, best_rank = rule, rank
    return best


@dataclass
class CheckResultItem:
    """Advisory result for a single check.

    Numeric checks carry threshold/measured values.  Non-numeric (categorical,
    presence, conditional, qualitative/performance) rules carry the decoded
    ``what_it_means`` / ``how_to_query`` so the panel can show what the rule
    requires and how it would be verified.
    """

    check_key: str
    status: str  # likely_pass | likely_fail | needs_more_info | unsupported | needs_assessment
    threshold_value: float | None
    threshold_unit: str | None
    measured_value: float | None
    rule_id: str | None
    rule_quote: str | None
    citation: str | None
    note: str | None = None
    check_type: str | None = None  # numeric_threshold | categorical | boolean_presence | ...
    what_it_means: str | None = None
    how_to_query: str | None = None


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


def _extract_text_value(value_json: dict[str, object] | None) -> str | None:
    """Pull a stable display string from a PropertyFact value_json dict."""
    if not isinstance(value_json, dict):
        return None
    for key in ("value", "name", "label", "code", "council", "council_scope"):
        raw = value_json.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def _project_council_scope(project: Project) -> str | None:
    council_scope: str | None = project.council_scope
    if council_scope is None and isinstance(project.metadata_json, dict):
        raw = project.metadata_json.get("council_scope")
        council_scope = str(raw) if raw is not None else None
    return council_scope


def _resolve_council_scope(project: Project, fact_by_type: dict[str, PropertyFact]) -> tuple[str | None, str]:
    """Resolve council from confirmed facts first, then legacy project fields."""
    council_fact = fact_by_type.get("council")
    council_from_fact = _extract_text_value(
        council_fact.value_json if council_fact is not None and isinstance(council_fact.value_json, dict) else None
    )
    if council_from_fact:
        return council_from_fact, "property_fact:council"
    project_scope = _project_council_scope(project)
    if project_scope:
        return project_scope, "project.council_scope"
    return None, "missing"


def _missing_reason(
    *,
    rule: Rule | None,
    measured_value: float | None,
    threshold_value: float | None,
    operator: str | None = None,
    matched_fact: PropertyFact | None = None,
) -> str | None:
    if rule is None:
        return "missing_rule"
    if matched_fact and matched_fact.method == "assumption":
        return "assumption_fact_unconfirmed"
    if measured_value is None:
        return "missing_measurement_fact"
    if threshold_value is None:
        return "missing_rule_threshold"
    if operator is not None and operator not in _OPERATORS:
        return "unknown_rule_operator"
    return None


def _drawing_evidence(fact: PropertyFact | None) -> dict[str, object]:
    """Return provenance for the drawing/property fact used by a check."""
    if fact is None:
        return {}
    value = fact.value_json if isinstance(fact.value_json, dict) else {}
    provenance = fact.provenance_json if isinstance(fact.provenance_json, dict) else {}
    evidence: dict[str, object] = {
        "property_fact_id": str(fact.id),
        "fact_type": fact.fact_type,
        "method": fact.method,
        "confidence": fact.confidence,
        "value_json": value,
        "provenance_json": provenance,
    }
    for key in ("document_fact_id", "source_document_id", "source_fact_id"):
        raw = value.get(key) or provenance.get(key)
        if raw is not None:
            evidence[key] = str(raw)
    return evidence


def _get_applicable_rules(
    session: Session,
    *,
    council_scope: str | None = None,
    zone_codes: list[str] | None = None,
    r_codes: list[str] | None = None,
) -> list[Rule]:
    """Load approved rules filtered by zone/R-code applicability.

    NULL applicable_zones / applicable_r_codes means the rule is global (applies to all).
    """
    from sqlalchemy import cast, or_
    from sqlalchemy.dialects.postgresql import JSONB as PgJSONB

    q = session.query(Rule).filter(Rule.lifecycle_status == "approved")

    if council_scope:
        q = q.filter(
            (Rule.council_scope == None) | (Rule.council_scope == council_scope)  # noqa: E711
        )

    if zone_codes and any(zone_codes):
        zone_filters = [Rule.applicable_zones == None]  # noqa: E711
        for zc in zone_codes:
            zone_filters.append(
                Rule.applicable_zones.contains(cast([zc], PgJSONB))
            )
        q = q.filter(or_(*zone_filters))

    if r_codes and any(r_codes):
        r_code_filters = [Rule.applicable_r_codes == None]  # noqa: E711
        for rc in r_codes:
            r_code_filters.append(
                Rule.applicable_r_codes.contains(cast([rc], PgJSONB))
            )
        q = q.filter(or_(*r_code_filters))

    return q.all()


_ADVISORY_CHECK_TYPES = (
    "categorical",
    "boolean_presence",
    "qualitative_performance",
    "conditional",
)

# Keywords used to RANK advisory rules by relevance to the proposal. The decode
# rules mostly lack structured applicable_zones/r_codes, so a SQL filter alone
# cannot scope them — we score by content so a residential lot surfaces siting/
# design rules first instead of an alphabetical wall of subdivision/admin items.
_RESIDENTIAL_KW = (
    "setback", "boundary", "wall", "fence", "garage", "carport", "outbuilding",
    "patio", "shed", "dwelling", "height", "storey", "plot ratio", "site cover",
    "open space", "outdoor living", "landscap", "overlook", "privacy", "solar",
    "parking", "driveway", "crossover", "building envelope", "facade", "roof",
    "eaves", "porch", "verandah", "retaining", "fill", "excavation", "amenity",
)
_DOWNWEIGHT_KW = (
    "subdivision", "subdivide", "lot design", "road reserve", "developer contribution",
    "strata", "commercial", "industrial", "rural", "pastoral", "mining", "marina",
    "dredging", "structure plan area", "precinct", "regional", "foreshore reserve",
)


def _advisory_relevance_score(
    rule: Rule, r_codes: list[str] | None, zone_codes: list[str] | None
) -> float:
    """Heuristic relevance of a non-numeric rule to the current proposal.

    Higher = more relevant. Uses the proposal r-code/zone and residential
    development keywords; downweights subdivision/commercial/admin content.
    """
    logic = rule.rule_logic_json if isinstance(rule.rule_logic_json, dict) else {}
    applies = str(logic.get("applies_when") or "").lower()
    text = " ".join([
        rule.canonical_rule_key or rule.rule_key or "",
        str(logic.get("what_it_means") or ""),
        applies,
    ]).lower()
    score = 0.0
    for rc in (r_codes or []):
        rcl = str(rc).lower()
        if rcl and (rcl in applies or rcl in text):
            score += 6.0
    for zc in (zone_codes or []):
        if str(zc).lower() in text:
            score += 3.0
    if "residential" in text or "dwelling" in text:
        score += 2.0
    score += sum(1.0 for kw in _RESIDENTIAL_KW if kw in text)
    score -= sum(1.5 for kw in _DOWNWEIGHT_KW if kw in text)
    # Rules explicitly scoped to this proposal (non-null applicable_*) rank above
    # globally-applicable ones of equal content.
    if rule.applicable_r_codes or rule.applicable_zones:
        score += 1.0
    return score


def _get_advisory_rules(
    session: Session,
    *,
    council_scope: str | None,
    r_codes: list[str] | None,
    zone_codes: list[str] | None = None,
) -> list[Rule]:
    """Load applicable NON-numeric development rules (categorical / presence /
    conditional / qualitative-performance), RANKED by relevance to the proposal
    (not alphabetical) so the most pertinent rules surface first."""
    from sqlalchemy import cast, or_
    from sqlalchemy.dialects.postgresql import JSONB as PgJSONB

    q = session.query(Rule).filter(
        Rule.lifecycle_status == "approved",
        Rule.check_type.in_(_ADVISORY_CHECK_TYPES),
    )
    if council_scope:
        q = q.filter(
            (Rule.council_scope == None) | (Rule.council_scope == council_scope)  # noqa: E711
        )
    if r_codes and any(r_codes):
        r_code_filters = [Rule.applicable_r_codes == None]  # noqa: E711
        for rc in r_codes:
            r_code_filters.append(Rule.applicable_r_codes.contains(cast([rc], PgJSONB)))
        q = q.filter(or_(*r_code_filters))
    if zone_codes and any(zone_codes):
        zone_filters = [Rule.applicable_zones == None]  # noqa: E711
        for zc in zone_codes:
            zone_filters.append(Rule.applicable_zones.contains(cast([zc], PgJSONB)))
        q = q.filter(or_(*zone_filters))
    candidates = q.limit(3000).all()
    candidates.sort(
        key=lambda r: (
            -_advisory_relevance_score(r, r_codes, zone_codes),
            r.canonical_rule_key or r.rule_key or "",
        )
    )
    return candidates


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
        # 2. Load PropertyFacts for this project (needed before rule filtering)
        #    Confirmed facts are authoritative (spatial synth / promoted docs).
        #    Manual overrides are the USER's proposed design values — they must
        #    also flow into the checks, otherwise a user who types a proposed
        #    setback/height gets silent needs_more_info (their input dropped).
        #    The rule still supplies the cited threshold; the override supplies
        #    the measured value (provenance records it as manual_override).
        # ------------------------------------------------------------------
        from sqlalchemy import or_

        facts: list[PropertyFact] = (
            session.query(PropertyFact)
            .filter(
                PropertyFact.project_id == UUID(project_id),
                or_(
                    PropertyFact.review_status == "confirmed",
                    PropertyFact.method == "manual_override",
                ),
            )
            .all()
        )
        # Build lookup: fact_type -> PropertyFact (most-recent wins, so a user's
        # manual override of a fact takes precedence over an earlier synth value).
        fact_by_type: dict[str, PropertyFact] = {}
        for fact in sorted(facts, key=lambda f: f.created_at):
            fact_by_type[fact.fact_type] = fact

        # ------------------------------------------------------------------
        # 3. Resolve council_scope from confirmed PropertyFacts first.
        # ------------------------------------------------------------------
        council_scope, council_scope_source = _resolve_council_scope(project, fact_by_type)

        # Extract zone and r_code codes for rule applicability filtering
        zone_codes: list[str] = []
        r_codes: list[str] = []
        for fact in facts:
            if fact.fact_type == "zone" and isinstance(fact.value_json, dict):
                code = fact.value_json.get("code")
                if code:
                    zone_codes.append(str(code))
            elif fact.fact_type == "r_code" and isinstance(fact.value_json, dict):
                code = fact.value_json.get("code")
                if code:
                    r_codes.append(str(code))

        # ------------------------------------------------------------------
        # 4. Load approved rules filtered by zone/R-code applicability
        # ------------------------------------------------------------------
        rules: list[Rule] = _get_applicable_rules(
            session,
            council_scope=council_scope,
            zone_codes=zone_codes or None,
            r_codes=r_codes or None,
        )


        # ------------------------------------------------------------------
        # 5. Create the CheckRun record
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
        # 6. Evaluate each Tier-1 check key
        # ------------------------------------------------------------------
        results: list[CheckResultItem] = []
        any_fail = False
        any_missing = False

        for check_def in ALL_CHECKS:
            check_key = check_def.key
            # Find the best matching approved rule for this check
            rule: Rule | None = _select_rule(rules, check_key, r_codes)

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
                    note="missing_rule: no approved rule found for this check key",
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
                    note="assumption_fact_unconfirmed: fact sourced from assumption; confirmation required before compliance use",
                )
                results.append(item)
                any_missing = True
                continue

            missing_reason: str | None = None
            if measured_value is None:
                status = "needs_more_info"
                missing_reason = _missing_reason(
                    rule=rule,
                    measured_value=measured_value,
                    threshold_value=threshold_value,
                )
                note = f"{missing_reason}: no measurement provided (expected fact_type in: {fact_keys})"
                any_missing = True
            elif threshold_value is None:
                status = "needs_more_info"
                missing_reason = _missing_reason(
                    rule=rule,
                    measured_value=measured_value,
                    threshold_value=threshold_value,
                )
                note = f"{missing_reason}: rule threshold value is missing or non-numeric"
                any_missing = True
            else:
                operator = _normalize_operator(rule.operator)
                op_fn = _OPERATORS.get(operator)
                if op_fn is None:
                    status = "needs_more_info"
                    missing_reason = _missing_reason(
                        rule=rule,
                        measured_value=measured_value,
                        threshold_value=threshold_value,
                        operator=operator,
                    )
                    note = f"{missing_reason}: unknown operator '{operator}' in rule"
                    any_missing = True
                else:
                    try:
                        passes = op_fn(measured_value, threshold_value)
                    except Exception as exc:
                        logger.warning("Operator evaluation error for %s: %s", check_key, exc)
                        status = "needs_more_info"
                        missing_reason = "evaluation_error"
                        note = f"{missing_reason}: {exc}"
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
            # 7. Persist ResolvedRule + CheckResult rows
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
                    "council_scope_source": council_scope_source,
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
                    "missing_info_reason": missing_reason,
                },
                drawing_evidence_json=_drawing_evidence(matched_fact),
                pathway_note=rule.pathway if rule.pathway != "none" else None,
            )
            session.add(check_result)

        # ------------------------------------------------------------------
        # 7. Surface applicable NON-NUMERIC development rules as advisory items.
        #    These carry the decoded "what it means" / "how to query" so the
        #    panel can show the rule and how it would be verified.  They never
        #    emit a false pass/fail — auto_presence/categorical that can't be
        #    confirmed are needs_more_info; qualitative are needs_assessment.
        # ------------------------------------------------------------------
        emitted_keys = {it.check_key for it in results}
        seen_adv: set[str] = set()
        for rule in _get_advisory_rules(
            session, council_scope=council_scope, r_codes=r_codes or None,
            zone_codes=zone_codes or None,
        ):
            key = rule.canonical_rule_key or rule.rule_key
            if not key or key in emitted_keys or key in seen_adv:
                continue
            seen_adv.add(key)
            if len(seen_adv) > 80:
                break
            logic = rule.rule_logic_json if isinstance(rule.rule_logic_json, dict) else {}
            adv_status = (
                "needs_assessment" if rule.evaluable == "ai_judgement" else "needs_more_info"
            )
            results.append(
                CheckResultItem(
                    check_key=key,
                    status=adv_status,
                    threshold_value=None,
                    threshold_unit=None,
                    measured_value=None,
                    rule_id=str(rule.id),
                    rule_quote=rule.quote,
                    citation=_build_citation(rule),
                    note=str(logic.get("how_to_query") or "") or None,
                    check_type=rule.check_type,
                    what_it_means=str(logic.get("what_it_means") or "") or None,
                    how_to_query=str(logic.get("how_to_query") or "") or None,
                )
            )
            any_missing = True

        # ------------------------------------------------------------------
        # 8. Update CheckRun status
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

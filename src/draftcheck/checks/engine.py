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
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from draftcheck.checks.registry import ALL_CHECKS
from draftcheck.domain.address.lga import canonical_local_government_name
from draftcheck.db.models import (
    CheckResult,
    CheckRun,
    Project,
    PropertyFact,
    ResolvedRule,
    Rule,
    Source,
    SourceVersion,
)

logger = logging.getLogger(__name__)

ENGINE_VERSION = "1.0.0"

# Operators supported by Rule.operator
_OPERATORS: dict[str, Any] = {
    "lte": lambda measured, threshold: float(measured) <= float(threshold),
    "gte": lambda measured, threshold: float(measured) >= float(threshold),
    "lt": lambda measured, threshold: float(measured) < float(threshold),
    "gt": lambda measured, threshold: float(measured) > float(threshold),
    "eq": lambda measured, threshold: float(measured) == float(threshold),
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
    "setback_side_primary": ("side_setback_primary", "primary_street_setback", "side_setback"),
    "setback_side_secondary": ("side_setback_secondary", "secondary_street_setback", "side_setback"),
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
    raw = rule.rule_key or ""
    parts = raw.split(".")
    if len(parts) <= 1:
        return raw
    if len(parts) == 2:
        # Two-part keys like "side_setback.primary" carry a meaningful
        # qualifier — join so they match specific base keys (e.g.
        # "side_setback_primary" in _CHECK_TO_BASE_RULE_KEYS).
        return "_".join(parts)
    # 3+ segment keys are WP6 density/dwelling-suffixed (e.g.
    # "site_area.R40.grouped_dwelling") — first segment is the base.
    return parts[0]


def _dwelling_type(rule: Rule) -> str:
    cond = rule.condition_json if isinstance(rule.condition_json, dict) else {}
    return str(cond.get("dwelling_type") or "any")


_NUMERIC_CONDITION_FACTS: dict[str, tuple[str, ...]] = {
    "wall_height_m": (
        "proposed_wall_height_m",
        "proposed_boundary_wall_height_m",
        "wall_height_m",
    ),
    "wall_length_m": (
        "proposed_wall_length_m",
        "proposed_boundary_wall_length_m",
        "wall_length_m",
    ),
}
_CONDITION_METADATA_KEYS = {
    "wall_height_label",
    "wall_length_label",
    # Documentation artifacts from extraction, not real conditions:
    "notes",
    "reference",
    "source_clause",
    "figure_ref",
    "table_ref",
}


def _numeric_fact(
    fact_by_type: dict[str, PropertyFact],
    fact_keys: tuple[str, ...],
) -> float | None:
    for fact_key in fact_keys:
        fact = fact_by_type.get(fact_key)
        if fact is None:
            continue
        value_json = fact.value_json
        if not isinstance(value_json, dict):
            value_json = {"value": value_json}
        value = _extract_numeric(value_json)
        if value is not None:
            return value
    return None


def _condition_rank(
    rule: Rule,
    fact_by_type: dict[str, PropertyFact],
) -> tuple[bool, float, tuple[str, ...]]:
    """Return whether a rule's structured conditions are satisfied.

    Numeric table headings are upper-bound buckets unless their label says
    ``over``. Unknown conditions are never guessed: they require operator
    review rather than allowing a compliance verdict.
    """
    conditions = rule.condition_json if isinstance(rule.condition_json, dict) else {}
    if not conditions:
        return True, 0.0, ()

    missing: list[str] = []

    # dwelling_type is a hard categorical filter: a rule scoped to a specific
    # dwelling type must not apply to a property of a different type.  If the
    # property has no dwelling_type fact the rule is blocked (missing), not
    # silently ignored.
    required_dwelling = conditions.get("dwelling_type")
    if required_dwelling is not None and str(required_dwelling).strip():
        dwelling_fact = fact_by_type.get("dwelling_type")
        actual_dwelling = (
            _extract_text_value(
                dwelling_fact.value_json
                if dwelling_fact is not None and isinstance(dwelling_fact.value_json, dict)
                else None
            )
            if dwelling_fact is not None
            else None
        )
        if actual_dwelling is None:
            missing.append("dwelling_type")
        elif actual_dwelling.lower() != str(required_dwelling).strip().lower():
            return False, 0.0, ()

    # density_codes is a hard categorical filter scoped to R-codes: a rule
    # listing density_codes (e.g. ["R40","R60"]) must only apply to properties
    # whose R-code appears in that list.  If the property has no r_code fact
    # the rule is blocked (missing), not silently ignored.
    required_density_codes = conditions.get("density_codes")
    if isinstance(required_density_codes, list) and required_density_codes:
        r_code_fact = fact_by_type.get("r_code")
        actual_r_code = (
            _extract_text_value(
                r_code_fact.value_json
                if r_code_fact is not None and isinstance(r_code_fact.value_json, dict)
                else None
            )
            if r_code_fact is not None
            else None
        )
        if actual_r_code is None:
            missing.append("r_code")
        else:
            allowed = {str(c).strip().upper() for c in required_density_codes if str(c).strip()}
            if actual_r_code.strip().upper() not in allowed:
                return False, 0.0, ()

    distance = 0.0
    for condition_key, fact_keys in _NUMERIC_CONDITION_FACTS.items():
        if conditions.get(condition_key) is None:
            continue
        measured = _numeric_fact(fact_by_type, fact_keys)
        if measured is None:
            missing.extend(fact_keys)
            continue
        try:
            boundary = float(str(conditions[condition_key]))
        except (TypeError, ValueError):
            missing.append(f"condition:{condition_key}")
            continue

        label = str(conditions.get(condition_key.replace("_m", "_label")) or "").lower()
        _LOWER_BOUND_MARKERS = ("over", "more than", "greater than", "exceeds", "minimum", "at least")
        if any(marker in label for marker in _LOWER_BOUND_MARKERS):
            if measured <= boundary:
                return False, 0.0, ()
            distance += measured - boundary
        else:
            if measured > boundary:
                return False, 0.0, ()
            distance += boundary - measured

    unsupported = (
        set(conditions)
        - set(_NUMERIC_CONDITION_FACTS)
        - _CONDITION_METADATA_KEYS
        - {"dwelling_type", "density_codes"}
    )
    missing.extend(f"condition:{key}" for key in sorted(unsupported))
    if missing:
        return False, 0.0, tuple(dict.fromkeys(missing))
    return True, -distance, ()


_EXCEPTION_KEY_MARKERS = ("exception", "variant")


def _is_exception_rule(rule: Rule) -> bool:
    """Whether a rule is an exception/variant that modifies a base standard.

    Exceptions carry a trigger condition and must only apply when that trigger
    is genuinely met.  They are flagged either by ``rule_type == "exception"``
    or by a ``rule_key`` containing an ``exception``/``variant`` marker (open-
    vocab clustering pulls ``<key>.exception_*`` rows into canonical clusters).
    """
    if (rule.rule_type or "").strip().lower() == "exception":
        return True
    key = (rule.rule_key or "").lower()
    return any(marker in key for marker in _EXCEPTION_KEY_MARKERS)


def _exception_trigger_satisfied(
    key: str,
    required: object,
    fact_by_type: dict[str, PropertyFact],
) -> bool:
    """Whether one non-numeric trigger condition on an exception rule is backed
    by a satisfied property fact.  Unknown categorical triggers have no fact
    mapping and can never be verified, so they are treated as unsatisfied."""
    if key == "dwelling_type":
        if required is None or not str(required).strip():
            return True
        fact = fact_by_type.get("dwelling_type")
        actual = _extract_text_value(
            fact.value_json if fact is not None and isinstance(fact.value_json, dict) else None
        )
        return actual is not None and actual.lower() == str(required).strip().lower()
    if key == "density_codes":
        fact = fact_by_type.get("r_code")
        actual = _extract_text_value(
            fact.value_json if fact is not None and isinstance(fact.value_json, dict) else None
        )
        if actual is None:
            return False
        allowed = {
            str(c).strip().upper()
            for c in (required if isinstance(required, list) else [])
            if str(c).strip()
        }
        return actual.strip().upper() in allowed
    return False


def _exception_trigger_gap(
    rule: Rule,
    fact_by_type: dict[str, PropertyFact],
) -> tuple[str, ...]:
    """Non-numeric trigger conditions on an exception rule not backed by a
    satisfied fact.  An exception must never be selected on an unmet trigger,
    so any such gap is a hard block (returned as missing condition facts)."""
    conditions = rule.condition_json if isinstance(rule.condition_json, dict) else {}
    trigger_keys = set(conditions) - set(_NUMERIC_CONDITION_FACTS) - _CONDITION_METADATA_KEYS
    return tuple(
        f"condition:{key}"
        for key in sorted(trigger_keys)
        if not _exception_trigger_satisfied(key, conditions[key], fact_by_type)
    )


def _source_type_hierarchy_rank(rule: Rule) -> int:
    """Rank rules by WA planning instrument hierarchy.

    Local planning schemes outrank structure plans, which outrank state-level
    R-Codes.  The source_type is read from ``metadata_json`` (denormalised at
    rule creation) or, as a fallback, via a direct attribute.
    """
    st = ""
    meta = getattr(rule, "metadata_json", None)
    meta = meta if isinstance(meta, dict) else {}
    st = str(meta.get("source_type") or "").strip().lower()
    if not st:
        st = str(getattr(rule, "source_type", "") or "").strip().lower()
    if "local_planning" in st or "planning_scheme" in st or "scheme" in st:
        return 2
    if "structure_plan" in st or "local_development_plan" in st:
        return 1
    return 0


def _select_rule_with_context(
    rules: list[Rule],
    check_key: str,
    r_codes: list[str],
    fact_by_type: dict[str, PropertyFact],
) -> tuple[Rule | None, tuple[str, ...]]:
    """Pick the best approved rule for a check key.

    Ranking: a usable numeric threshold dominates, then zone-specific rules
    (local scheme scoped to the property's zone) beat global rules, then
    source-type hierarchy (local scheme > structure plan > state R-Codes),
    then R-code-specific match, then dwelling-type-agnostic, then base-key
    preference order, then newest.
    """
    base_keys = _CHECK_TO_BASE_RULE_KEYS.get(check_key, ())
    accepted = (check_key, *base_keys)
    best: Rule | None = None
    best_rank: tuple[Any, ...] = ()
    missing_conditions: list[str] = []
    conditional_rules_seen = False
    conditional_rule_matched = False

    # Collect the property's zone codes from zone facts for zone-specificity
    # ranking.  Rules scoped to one of these zones outrank global rules.
    property_zones: set[str] = set()
    for fact in fact_by_type.values():
        if getattr(fact, "fact_type", None) == "zone" and isinstance(
            getattr(fact, "value_json", None), dict
        ):
            code = fact.value_json.get("code")
            if code:
                property_zones.add(str(code).strip().upper())

    for rule in rules:
        base = _base_rule_key(rule)
        # Open-vocab derived checks key on canonical_rule_key (filled by
        # wp6_apply_clustering.py); the seed checks key on rule_key / base key.
        canonical = getattr(rule, "canonical_rule_key", None) or base
        if rule.rule_key != check_key and base not in accepted and canonical != check_key:
            continue
        conditions = rule.condition_json if isinstance(rule.condition_json, dict) else {}
        has_material_conditions = bool(set(conditions) - _CONDITION_METADATA_KEYS)
        conditional_rules_seen = conditional_rules_seen or has_material_conditions
        conditions_match, conditions_rank, missing = _condition_rank(rule, fact_by_type)
        missing_conditions.extend(missing)
        if not conditions_match:
            continue
        conditional_rule_matched = conditional_rule_matched or has_material_conditions

        raw = rule.value_json.get("value") if isinstance(rule.value_json, dict) else None
        try:
            has_threshold = raw is not None and float(str(raw)) == float(str(raw))
        except (TypeError, ValueError):
            has_threshold = False
        specific = bool(
            rule.applicable_r_codes and r_codes and set(r_codes) & set(rule.applicable_r_codes)
        )
        # Zone specificity: a rule scoped to the property's zone outranks a
        # global rule (applicable_zones NULL/empty).  This enforces the WA
        # planning hierarchy where local scheme provisions take precedence.
        rule_zones = getattr(rule, "applicable_zones", None)
        zone_specific = bool(
            rule_zones
            and property_zones
            and {str(z).strip().upper() for z in rule_zones if str(z).strip()} & property_zones
        )
        # A check's headline threshold should come from a base/standard rule, not
        # an exception modifier.  Open-vocab clustering can pull "<key>.exception_*"
        # rows into a canonical cluster; deprioritise them so the engine reports
        # the base rule's threshold (exceptions still inform legal_edges).
        is_standard = (rule.rule_type or "standard") != "exception"
        rank = (
            1 if has_threshold else 0,
            1 if is_standard else 0,
            1 if zone_specific else 0,
            _source_type_hierarchy_rank(rule),
            2 if specific else (1 if not rule.applicable_r_codes else 0),
            1 if _dwelling_type(rule) == "any" else 0,
            1 if has_material_conditions else 0,
            conditions_rank,
            len(accepted) - accepted.index(base if base in accepted else check_key),
            rule.created_at or datetime.min.replace(tzinfo=UTC),
        )
        if rank > best_rank:
            best, best_rank = rule, rank
    unresolved = tuple(dict.fromkeys(missing_conditions))
    if unresolved:
        return None, unresolved
    if conditional_rules_seen and not conditional_rule_matched:
        return None, ("condition:no_matching_rule",)
    # Finding #8: an exception/variant rule must never be selected on an unmet
    # trigger.  If the winning rule is an exception carrying a non-numeric
    # trigger condition that no satisfied fact backs, treat it as a hard block
    # (needs_more_info) rather than applying the exception.  Standard rules are
    # unaffected.
    if best is not None and _is_exception_rule(best):
        trigger_gap = _exception_trigger_gap(best, fact_by_type)
        if trigger_gap:
            return None, trigger_gap
    return best, ()


def _select_rule(
    rules: list[Rule],
    check_key: str,
    r_codes: list[str],
    fact_by_type: dict[str, PropertyFact] | None = None,
) -> Rule | None:
    """Pick the best approved rule whose conditions are supported by facts."""
    return _select_rule_with_context(
        rules,
        check_key,
        r_codes,
        fact_by_type or {},
    )[0]


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
    spatial_disagreement_active: bool = False


@dataclass
class CheckRunResult:
    """Container returned by ComplianceEngine.run_check."""

    check_run_id: str
    project_id: str
    org_id: str
    status: str
    results: list[CheckResultItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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


def _resolve_council_scope(
    project: Project, fact_by_type: dict[str, PropertyFact]
) -> tuple[str | None, str]:
    """Resolve council from confirmed facts first, then legacy project fields.

    Spatial synth writes the resolved LGA as ``fact_type='local_government'``
    (value_json ``{"name": "City of ..."}``).  Older paths used ``council``.
    Both are honoured so WP-0 council scoping works regardless of fact source.
    """
    for fact_type in ("council", "local_government"):
        fact = fact_by_type.get(fact_type)
        council_from_fact = _extract_text_value(
            fact.value_json if fact is not None and isinstance(fact.value_json, dict) else None
        )
        if council_from_fact:
            canonical = canonical_local_government_name(council_from_fact)
            return canonical or council_from_fact, f"property_fact:{fact_type}"
    project_scope = _project_council_scope(project)
    if project_scope:
        canonical = canonical_local_government_name(project_scope)
        return canonical or project_scope, "project.council_scope"
    return None, "missing"


_SPATIAL_REFERENCE_RE = re.compile(r"\b(?:SPN|LDP)\s*[/_-]?\s*\d+\b", re.IGNORECASE)
_SPATIALLY_SCOPED_SOURCE_TYPES = {
    "structure_plan",
    "local_structure_plan",
    "local_development_plan",
    "precinct_structure_plan",
}
_SPATIALLY_SCOPED_TITLE_MARKERS = (
    "structure plan",
    "local development plan",
)


def _normalized_spatial_reference(value: object) -> str:
    raw = " ".join(str(value or "").strip().upper().split())
    match = re.fullmatch(r"(SPN|LDP)\s*[/_-]?\s*(\d+)", raw)
    return f"{match.group(1)}/{match.group(2)}" if match else raw


def _property_spatial_scopes(facts: list[PropertyFact]) -> dict[str, set[str]]:
    scopes: dict[str, set[str]] = {}
    for fact in facts:
        fact_type = str(fact.fact_type or "").strip().lower()
        if fact_type not in {"structure_plan", "special_area", "local_development_plan"}:
            continue
        value = fact.value_json if isinstance(fact.value_json, dict) else {}
        if fact_type in {"structure_plan", "local_development_plan"}:
            from draftcheck.domain.address.planwa import structure_plan_is_current

            if not structure_plan_is_current(value):
                continue
        raw_values: list[object] = [
            value.get("code"),
            value.get("reference"),
            value.get("filenumber"),
            value.get("file_number"),
        ]
        references = value.get("references")
        if isinstance(references, list):
            raw_values.extend(references)
        normalized = {
            _normalized_spatial_reference(item)
            for item in raw_values
            if item is not None and str(item).strip()
        }
        scopes.setdefault(fact_type, set()).update(normalized)
    return scopes


def _source_spatial_scope(source: Source) -> tuple[bool, str, set[str]]:
    """Return (scope_required, fact_type, references) for a source document."""
    metadata = source.metadata_json if isinstance(source.metadata_json, dict) else {}
    explicit = metadata.get("spatial_scope")
    explicit = explicit if isinstance(explicit, dict) else {}
    source_type = str(source.source_type or "").strip().lower()
    title = str(source.title or "")
    title_lower = title.lower()
    scope_required = bool(explicit.get("required")) or source_type in _SPATIALLY_SCOPED_SOURCE_TYPES
    scope_required = scope_required or any(
        marker in title_lower for marker in _SPATIALLY_SCOPED_TITLE_MARKERS
    )
    fact_type = str(explicit.get("fact_type") or explicit.get("kind") or "structure_plan")
    # Keep local_development_plan distinct — resolver writes fact_type as-is
    # from _SPATIAL_SCOPE_FACT_TYPES (no remap), so remapping here would cause
    # _source_applies_to_spatial_facts to look up the wrong property_scopes key.

    refs: set[str] = set()
    explicit_refs = explicit.get("references") or explicit.get("refs") or []
    if isinstance(explicit_refs, str):
        explicit_refs = [explicit_refs]
    if isinstance(explicit_refs, list):
        refs.update(
            _normalized_spatial_reference(value)
            for value in explicit_refs
            if str(value or "").strip()
        )
    searchable = " ".join(
        [
            title,
            str(source.canonical_url or ""),
            str(metadata.get("file_number") or ""),
            str(metadata.get("reference") or ""),
        ]
    )
    refs.update(
        _normalized_spatial_reference(match.group(0))
        for match in _SPATIAL_REFERENCE_RE.finditer(searchable)
    )
    return scope_required, fact_type, refs


def _source_applies_to_spatial_facts(
    source: Source,
    property_scopes: dict[str, set[str]],
) -> bool:
    required, fact_type, required_refs = _source_spatial_scope(source)
    if not required:
        return True
    # Fail closed: a parcel-specific source with no mappable reference must not
    # silently become an LGA-wide rule.
    if not required_refs:
        return False
    return bool(required_refs & property_scopes.get(fact_type, set()))


def _filter_rules_by_spatial_scope(
    session: Session,
    rules: list[Rule],
    facts: list[PropertyFact],
    *,
    blocked_scope_types: set[str] | None = None,
) -> list[Rule]:
    version_ids = {rule.source_version_id for rule in rules if rule.source_version_id}
    if not version_ids:
        return rules
    sources_by_version = {
        version_id: source
        for version_id, source in (
            session.query(SourceVersion.id, Source)
            .join(Source, SourceVersion.source_id == Source.id)
            .filter(SourceVersion.id.in_(version_ids))
            .all()
        )
    }
    property_scopes = _property_spatial_scopes(facts)
    for fact_type in blocked_scope_types or set():
        property_scopes.pop(fact_type, None)
    return [
        rule
        for rule in rules
        if (
            # Fail closed: if the source_version can't be resolved (deleted
            # source, missing version), exclude the rule rather than silently
            # applying it LGA-wide.
            rule.source_version_id in sources_by_version
            and _source_applies_to_spatial_facts(
                sources_by_version[rule.source_version_id],
                property_scopes,
            )
        )
    ]


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
    else:
        # When the property's LGA is unknown, restrict to global rules only.
        # Without this, council-scoped rules from every LGA leak into the
        # candidate set and may be selected over the correct global rule.
        q = q.filter(Rule.council_scope == None)  # noqa: E711

    if zone_codes and any(zone_codes):
        zone_filters = [Rule.applicable_zones == None]  # noqa: E711
        for zc in zone_codes:
            zone_filters.append(Rule.applicable_zones.contains(cast([zc], PgJSONB)))
        q = q.filter(or_(*zone_filters))

    if r_codes and any(r_codes):
        r_code_filters = [Rule.applicable_r_codes == None]  # noqa: E711
        for rc in r_codes:
            r_code_filters.append(Rule.applicable_r_codes.contains(cast([rc], PgJSONB)))
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
    "setback",
    "boundary",
    "wall",
    "fence",
    "garage",
    "carport",
    "outbuilding",
    "patio",
    "shed",
    "dwelling",
    "height",
    "storey",
    "plot ratio",
    "site cover",
    "open space",
    "outdoor living",
    "landscap",
    "overlook",
    "privacy",
    "solar",
    "parking",
    "driveway",
    "crossover",
    "building envelope",
    "facade",
    "roof",
    "eaves",
    "porch",
    "verandah",
    "retaining",
    "fill",
    "excavation",
    "amenity",
)
_DOWNWEIGHT_KW = (
    "subdivide",
    "lot design",
    "road reserve",
    "developer contribution",
    "strata",
    "commercial",
    "industrial",
    "rural",
    "pastoral",
    "mining",
    "marina",
    "dredging",
    "structure plan area",
    "precinct",
    "regional",
    "foreshore reserve",
)
_LIGHT_DOWNWEIGHT_KW = (
    # Sometimes relevant in residential contexts — lighter penalty.
    "subdivision",
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
    text = " ".join(
        [
            rule.canonical_rule_key or rule.rule_key or "",
            str(logic.get("what_it_means") or ""),
            applies,
        ]
    ).lower()
    score = 0.0
    for rc in r_codes or []:
        rcl = str(rc).lower()
        if rcl and (rcl in applies or rcl in text):
            score += 6.0
    for zc in zone_codes or []:
        if str(zc).lower() in text:
            score += 3.0
    if "residential" in text or "dwelling" in text:
        score += 2.0
    score += sum(1.0 for kw in _RESIDENTIAL_KW if kw in text)
    score -= sum(1.5 for kw in _DOWNWEIGHT_KW if kw in text)
    score -= sum(0.5 for kw in _LIGHT_DOWNWEIGHT_KW if kw in text)
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
    else:
        q = q.filter(Rule.council_scope == None)  # noqa: E711
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
    # Spatially-scoped sources are filtered after this query because their
    # applicability comes from the source document + parcel facts. Loading the
    # complete approved advisory set prevents a large unrelated structure-plan
    # corpus from crowding global/local-scheme rules out before that gate.
    candidates = q.all()
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
                    # Resolver-written spatial facts are authoritative even though
                    # they arrive as pending_review — without this the engine sees
                    # zero facts for freshly-resolved projects.
                    PropertyFact.method.like("postgis_st_intersects%"),
                    PropertyFact.method == "gnaf_trigram_or_like_match",
                ),
            )
            .all()
        )
        live_verification = (
            session.query(PropertyFact)
            .filter(
                PropertyFact.project_id == UUID(project_id),
                PropertyFact.fact_type == "planwa_live_verification",
            )
            .order_by(PropertyFact.created_at.desc())
            .first()
        )
        live_value = (
            live_verification.value_json
            if live_verification is not None
            and isinstance(live_verification.value_json, dict)
            else {}
        )
        raw_live_disagreements = live_value.get("disagreements")
        live_disagreements: dict[str, object] = (
            raw_live_disagreements if isinstance(raw_live_disagreements, dict) else {}
        )
        blocked_scope_types = set(live_disagreements)
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
        rules = _filter_rules_by_spatial_scope(
            session,
            rules,
            facts,
            blocked_scope_types=blocked_scope_types,
        )

        # ------------------------------------------------------------------
        # 5. Create the CheckRun record
        # ------------------------------------------------------------------
        pack_hash = _rule_pack_hash(rules) if rules else None
        source_version_ids = list({str(r.source_version_id) for r in rules if r.source_version_id})

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
            rule, missing_condition_facts = _select_rule_with_context(
                rules,
                check_key,
                r_codes,
                fact_by_type,
            )

            if rule is None:
                # A conditional rule without its condition facts is not
                # unsupported; it is explicitly blocked pending more evidence.
                missing_conditions = bool(missing_condition_facts)
                item = CheckResultItem(
                    check_key=check_key,
                    status="needs_more_info" if missing_conditions else "unsupported",
                    threshold_value=None,
                    threshold_unit=None,
                    measured_value=None,
                    rule_id=None,
                    rule_quote=None,
                    citation=None,
                    note=(
                        "missing_rule_conditions: required condition facts are absent or "
                        f"unsupported ({list(missing_condition_facts)})"
                        if missing_conditions
                        else "missing_rule: no approved rule found for this check key"
                    ),
                )
                results.append(item)
                any_missing = any_missing or missing_conditions
                continue

            # Extract threshold from rule.value_json
            threshold_raw = (
                rule.value_json.get("value") if isinstance(rule.value_json, dict) else None
            )
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
                spatial_disagreement_active=bool(live_disagreements) and status in (
                    "likely_pass", "likely_fail",
                ),
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
                    "condition_json": rule.condition_json,
                },
                selection_trace_json={
                    "engine_version": ENGINE_VERSION,
                    "matched_on": "rule_key",
                    "council_scope": council_scope,
                    "council_scope_source": council_scope_source,
                    "condition_json": rule.condition_json,
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
                    "condition_json": rule.condition_json,
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
        advisory_rules = _filter_rules_by_spatial_scope(
            session,
            _get_advisory_rules(
                session,
                council_scope=council_scope,
                r_codes=r_codes or None,
                zone_codes=zone_codes or None,
            ),
            facts,
            blocked_scope_types=blocked_scope_types,
        )
        for rule in advisory_rules:
            key = rule.canonical_rule_key or rule.rule_key
            if not key or key in emitted_keys or key in seen_adv:
                continue
            seen_adv.add(key)
            if len(seen_adv) > 200:
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

        run_warnings: list[str] = []
        if live_disagreements:
            run_warnings.append(
                "planwa_live_disagreement: local and live official spatial "
                f"layers differ ({sorted(live_disagreements)}). Results are "
                "advisory pending spatial reconciliation."
            )

        return CheckRunResult(
            check_run_id=str(check_run.id),
            project_id=project_id,
            org_id=org_id,
            status=overall_status,
            results=results,
            warnings=run_warnings,
        )


def _build_citation(rule: Rule) -> str | None:
    """Construct a short citation string from the rule's source version."""
    parts: list[str] = []
    if rule.rule_key:
        parts.append(rule.rule_key)
    if rule.source_version_id:
        parts.append(f"source_version:{rule.source_version_id}")
    return " | ".join(parts) if parts else None

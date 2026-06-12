"""Unit tests for engine rule selection against WP6-style rule keys."""
from __future__ import annotations

from datetime import UTC, datetime

from draftcheck.checks.engine import (
    _base_rule_key,
    _drawing_evidence,
    _extract_text_value,
    _missing_reason,
    _normalize_operator,
    _resolve_council_scope,
    _select_rule,
)
from draftcheck.db.models import Project, PropertyFact, Rule


def _rule(rule_key, base=None, value=4.0, operator="gte", r_codes=None,
          dwelling=None, created=None):
    vj = {"value": value}
    if base:
        vj["base_rule_key"] = base
    cond = {"dwelling_type": dwelling} if dwelling else {}
    r = Rule(
        rule_key=rule_key,
        rule_type="requirement",
        pathway="none",
        lifecycle_status="approved",
        operator=operator,
        value_json=vj,
        unit="m",
        condition_json=cond,
        quote="q",
        applicable_r_codes=r_codes,
    )
    r.created_at = created or datetime(2026, 1, 1, tzinfo=UTC)
    return r


def test_normalize_operator_aliases():
    assert _normalize_operator("pct_lte") == "lte"
    assert _normalize_operator("pct_gte") == "gte"
    assert _normalize_operator(">=") == "gte"
    assert _normalize_operator("<=") == "lte"
    assert _normalize_operator(None) == "lte"
    assert _normalize_operator("gte") == "gte"


def test_base_rule_key_prefers_value_json():
    assert _base_rule_key(_rule("site_area.R40", base="site_area")) == "site_area"
    assert _base_rule_key(_rule("primary_street_setback.all")) == "primary_street_setback"


def test_select_rule_maps_check_key_to_wp6_base_keys():
    rules = [_rule("primary_street_setback.all", base="primary_street_setback")]
    assert _select_rule(rules, "setback_front", []) is rules[0]
    assert _select_rule(rules, "setback_rear", []) is None


def test_select_rule_prefers_r_code_specific_match():
    glob = _rule("garage_width.all", base="garage_width", value=6.0)
    specific = _rule("garage_width.R40.single_house", base="garage_width",
                     value=5.0, r_codes=["R40"], dwelling="single_house")
    assert _select_rule([glob, specific], "garage_width", ["R40"]) is specific
    assert _select_rule([glob, specific], "garage_width", ["R60"]) is glob
    assert _select_rule([glob, specific], "garage_width", []) is glob


def test_select_rule_skips_rules_without_numeric_threshold():
    no_value = _rule("front_setback", base="front_setback", value=None)
    with_value = _rule("primary_street_setback.all", base="primary_street_setback", value=4.0)
    assert _select_rule([no_value, with_value], "setback_front", []) is with_value


def test_select_rule_exact_check_key_still_matches():
    legacy = _rule("setback_front")
    assert _select_rule([legacy], "setback_front", []) is legacy


def test_extract_text_value_accepts_council_shapes():
    assert _extract_text_value({"value": "City of Cockburn"}) == "City of Cockburn"
    assert _extract_text_value({"name": "Demo Bay"}) == "Demo Bay"
    assert _extract_text_value({"code": "R40"}) == "R40"
    assert _extract_text_value({}) is None


def test_resolve_council_scope_prefers_confirmed_property_fact():
    project = Project(name="p", council_scope="Legacy Council", metadata_json={})
    council_fact = PropertyFact(
        fact_type="council",
        value_json={"value": "Fact Council"},
        confidence=1.0,
        method="manual_override",
        provenance_json={},
        review_status="confirmed",
    )

    council, source = _resolve_council_scope(project, {"council": council_fact})

    assert council == "Fact Council"
    assert source == "property_fact:council"


def test_missing_reason_classifies_fact_rule_and_operator_gaps():
    rule = _rule("site_cover", value=50)
    assert _missing_reason(rule=None, measured_value=None, threshold_value=None) == "missing_rule"
    assert _missing_reason(rule=rule, measured_value=None, threshold_value=50) == "missing_measurement_fact"
    assert _missing_reason(rule=rule, measured_value=45, threshold_value=None) == "missing_rule_threshold"
    assert (
        _missing_reason(rule=rule, measured_value=45, threshold_value=50, operator="bogus")
        == "unknown_rule_operator"
    )


def test_drawing_evidence_keeps_document_fact_provenance():
    fact = PropertyFact(
        fact_type="proposed_site_cover_pct",
        value_json={"value": 48.0, "unit": "%", "document_fact_id": "docfact-1"},
        confidence=0.91,
        method="document_extraction_promoted",
        provenance_json={"source_document_id": "doc-1", "source_fact_id": "docfact-1"},
        review_status="confirmed",
    )

    evidence = _drawing_evidence(fact)

    assert evidence["fact_type"] == "proposed_site_cover_pct"
    assert evidence["method"] == "document_extraction_promoted"
    assert evidence["document_fact_id"] == "docfact-1"
    assert evidence["source_document_id"] == "doc-1"

"""Unit tests for engine rule selection against WP6-style rule keys."""
from __future__ import annotations

from datetime import UTC, datetime

from draftcheck.checks.engine import (
    _base_rule_key,
    _drawing_evidence,
    _extract_numeric,
    _extract_text_value,
    _missing_reason,
    _normalize_council_scope,
    _normalize_operator,
    _resolve_council_scope,
    _select_measurement_fact,
    _select_rule,
    _units_compatible,
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


def test_select_rule_maps_new_registry_keys_to_wp6_base_keys():
    rules = [
        _rule("retaining_fill.R30", base="retaining_fill", value=0.5),
        _rule("vehicle_access.required", base="vehicle_access", value=1.0),
        _rule("outdoor_living_area.R30", base="outdoor_living_area", value=24.0),
        _rule("parking_bays_per_dwelling.single", base="parking_bays_per_dwelling", value=2.0),
        _rule("driveway_width.single", base="driveway_width", value=3.0),
        _rule("fence_height_front.single", base="fence_height_front", value=1.2),
        _rule("plot_ratio.single", base="plot_ratio", value=0.5),
    ]

    assert _select_rule(rules, "retaining_fill_trigger", []) is rules[0]
    assert _select_rule(rules, "vehicle_access", []) is rules[1]
    assert _select_rule(rules, "outdoor_living_area", []) is rules[2]
    assert _select_rule(rules, "parking_bays_per_dwelling", []) is rules[3]
    assert _select_rule(rules, "driveway_width", []) is rules[4]
    assert _select_rule(rules, "fence_height_front", []) is rules[5]
    assert _select_rule(rules, "plot_ratio", []) is rules[6]


def test_extract_text_value_accepts_council_shapes():
    assert _extract_text_value({"value": "City of Cockburn"}) == "City of Cockburn"
    assert _extract_text_value({"name": "Demo Bay"}) == "Demo Bay"
    assert _extract_text_value({"code": "R40"}) == "R40"
    assert _extract_text_value({}) is None


def test_extract_numeric_accepts_boolean_trigger_facts():
    assert _extract_numeric({"value": True}) == 1.0
    assert _extract_numeric({"value": False}) == 0.0


def test_normalize_council_scope_strips_legal_prefix_and_bbox_suffix():
    assert _normalize_council_scope("City of Cockburn (bbox extent)") == "Cockburn"
    assert _normalize_council_scope("Shire of Example") == "Example"
    assert _normalize_council_scope("Cockburn") == "Cockburn"


def test_units_compatible_rejects_percent_rule_with_area_fact():
    assert _units_compatible("%", "%") is True
    assert _units_compatible("m2", "sqm") is True
    assert _units_compatible("%", "m2") is False


def test_select_measurement_fact_skips_incompatible_area_for_percent_rule():
    area_fact = PropertyFact(
        fact_type="site_area_m2",
        value_json={"value": 580.0, "unit": "m2"},
        confidence=1.0,
        method="postgis_parcel",
        provenance_json={},
        review_status="confirmed",
    )
    pct_fact = PropertyFact(
        fact_type="proposed_site_cover_pct",
        value_json={"value": 48.0, "unit": "%"},
        confidence=1.0,
        method="document_extraction_promoted",
        provenance_json={},
        review_status="confirmed",
    )

    matched, measured, reason = _select_measurement_fact(
        {"site_area_m2": area_fact},
        ["proposed_site_cover_pct", "site_area_m2"],
        "%",
    )
    assert matched is None
    assert measured is None
    assert reason and reason.startswith("unit_mismatch")

    matched, measured, reason = _select_measurement_fact(
        {"site_area_m2": area_fact, "proposed_site_cover_pct": pct_fact},
        ["proposed_site_cover_pct", "site_area_m2"],
        "%",
    )
    assert matched is pct_fact
    assert measured == 48.0
    assert reason is None


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


def test_resolve_council_scope_accepts_address_local_government_fact():
    project = Project(name="p", council_scope="Legacy Council", metadata_json={})
    council_fact = PropertyFact(
        fact_type="local_government",
        value_json={"name": "City of Cockburn"},
        confidence=1.0,
        method="postgis_st_intersects_lga",
        provenance_json={},
        review_status="confirmed",
    )

    council, source = _resolve_council_scope(project, {"local_government": council_fact})

    assert council == "Cockburn"
    assert source == "property_fact:local_government"


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

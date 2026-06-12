from scripts.wp7_conflict_sweep import (
    RuleRow,
    cross_instrument_conflicts,
    density_codes,
    extraction_bug_groups,
    select_exception_base,
    value_signature,
)


def rule(**overrides) -> RuleRow:
    base = dict(
        id="00000000-0000-0000-0000-000000000001",
        org_id="1d31c315-5087-47df-a8d4-ebfd08efad5d",
        source_version_id="10000000-0000-0000-0000-000000000001",
        source_id="20000000-0000-0000-0000-000000000001",
        instrument_name="Instrument A",
        authority="Authority",
        clause_id="30000000-0000-0000-0000-000000000001",
        clause_path="5.1.2",
        section_ref=None,
        clause_text="Clause 5.1.2 requires a 4 m setback.",
        rule_key="primary_street_setback",
        rule_type="standard",
        pathway="deemed_to_comply",
        operator="gte",
        value_json={"value": 4.0, "base_rule_key": "primary_street_setback"},
        unit="m",
        condition_json={"density_codes": ["R30"]},
        applicable_r_codes=None,
        applicable_zones=None,
        council_scope=None,
        quote="requires a 4 m setback",
    )
    base.update(overrides)
    return RuleRow(**base)


def test_density_codes_prefers_applicable_r_codes() -> None:
    row = rule(applicable_r_codes=["R40"], condition_json={"density_codes": ["R30"]})

    assert density_codes(row) == ("R40",)


def test_cross_instrument_conflicts_group_by_rule_density_and_pathway() -> None:
    rows = [
        rule(id="00000000-0000-0000-0000-000000000001", source_id="a", instrument_name="A"),
        rule(id="00000000-0000-0000-0000-000000000002", source_id="b", instrument_name="B"),
    ]

    conflicts = cross_instrument_conflicts(rows)

    assert len(conflicts) == 1
    assert conflicts[0]["rule_key"] == "primary_street_setback"
    assert conflicts[0]["density_code"] == "R30"
    assert conflicts[0]["instrument_count"] == 2


def test_same_instrument_same_applicability_different_values_is_extraction_bug() -> None:
    rows = [
        rule(id="00000000-0000-0000-0000-000000000001", value_json={"value": 4.0}),
        rule(id="00000000-0000-0000-0000-000000000002", value_json={"value": 4.5}),
    ]

    bugs = extraction_bug_groups(rows)

    assert len(bugs) == 1
    assert bugs[0]["rule_ids"] == [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]


def test_select_exception_base_requires_named_base_rule() -> None:
    base = rule(id="00000000-0000-0000-0000-000000000001", clause_path="5.1.2")
    exception = rule(
        id="00000000-0000-0000-0000-000000000003",
        rule_type="exception",
        quote="Despite clause 5.1.2, a reduced setback may apply.",
        clause_text="Despite clause 5.1.2, a reduced setback may apply.",
    )

    assert select_exception_base(exception, [base, exception]) == base


def test_select_exception_base_returns_none_when_context_does_not_name_base() -> None:
    base = rule(id="00000000-0000-0000-0000-000000000001", clause_path="5.1.2")
    exception = rule(
        id="00000000-0000-0000-0000-000000000003",
        rule_type="exception",
        quote="A reduced setback may apply on corner lots.",
        clause_text="A reduced setback may apply on corner lots.",
    )

    assert select_exception_base(exception, [base, exception]) is None


def test_value_signature_uses_operator_value_and_unit() -> None:
    assert value_signature(rule()) == ("gte", 4.0, "m")

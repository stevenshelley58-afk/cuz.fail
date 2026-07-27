from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from draftcheck.checks.engine import _select_rule, _select_rule_with_context


def _rule(height: float, length: float, threshold: float):
    return SimpleNamespace(
        rule_key=f"boundary_setback_major_openings_min_m_h{height}_l{length}",
        canonical_rule_key="boundary_setback_major_openings_min_m",
        value_json={"value": threshold},
        condition_json={
            "wall_height_m": height,
            "wall_height_label": str(height),
            "wall_length_m": length,
            "wall_length_label": str(length),
        },
        applicable_r_codes=["R20"],
        rule_type="standard",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _fact(value: float):
    return SimpleNamespace(value_json={"value": value})


def test_conditional_rule_is_not_selected_without_condition_facts() -> None:
    rule = _rule(4.5, 15.0, 2.0)

    selected, missing = _select_rule_with_context(
        [rule],
        "boundary_setback_major_openings_min_m",
        ["R20"],
        {},
    )

    assert selected is None
    assert "proposed_wall_height_m" in missing
    assert "proposed_wall_length_m" in missing


def test_conditional_rule_selects_smallest_matching_table_bucket() -> None:
    rules = [
        _rule(3.5, 10.0, 1.0),
        _rule(3.5, 15.0, 1.5),
        _rule(4.5, 10.0, 2.0),
        _rule(4.5, 15.0, 2.5),
    ]
    facts = {
        "proposed_wall_height_m": _fact(4.0),
        "proposed_wall_length_m": _fact(12.0),
    }

    selected = _select_rule(
        rules,
        "boundary_setback_major_openings_min_m",
        ["R20"],
        facts,
    )

    assert selected is rules[3]
    assert selected.value_json["value"] == 2.5


def test_unknown_condition_requires_review_instead_of_a_verdict() -> None:
    rule = _rule(4.5, 15.0, 2.5)
    rule.condition_json["unmodelled_exception"] = True
    facts = {
        "proposed_wall_height_m": _fact(4.0),
        "proposed_wall_length_m": _fact(12.0),
    }

    selected, missing = _select_rule_with_context(
        [rule],
        "boundary_setback_major_openings_min_m",
        ["R20"],
        facts,
    )

    assert selected is None
    assert missing == ("condition:unmodelled_exception",)

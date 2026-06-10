"""Pure unit tests for scripts/adversarial_review.py (Phase 5 adversarial harness).

No DB, no network, no LLM — only the deterministic decision functions:
finding diff logic, closure / stopping-rule computation, judge quote-checks,
defense decisions, and deterministic fact-pattern / question generation.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

_MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "adversarial_review.py"
)
_spec = importlib.util.spec_from_file_location("adversarial_review", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
ar = importlib.util.module_from_spec(_spec)
sys.modules["adversarial_review"] = ar  # required for @dataclass resolution at exec time
_spec.loader.exec_module(ar)


def _atom(**overrides) -> dict:
    base = {
        "rule_id": "r-1",
        "rule_key": "primary_street_setback",
        "rule_type": "standard",
        "operator": "gte",
        "value": 4.0,
        "unit": "m",
        "pathway": "deemed_to_comply",
        "condition": "",
        "density_codes": ["R30"],
        "dwelling_type": "any",
        "quote": "shall be set back at least 4m from the primary street",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# quote_exists — the deterministic verbatim anchor check
# ---------------------------------------------------------------------------


def test_quote_exists_whitespace_normalised():
    text = "The   wall must\nnot exceed   9 m in length."
    assert ar.quote_exists("wall must not exceed 9 m", text)


def test_quote_exists_absent_or_empty():
    text = "The wall must not exceed 9 m in length."
    assert not ar.quote_exists("must not exceed 12 m", text)
    assert not ar.quote_exists("", text)
    assert not ar.quote_exists(None, text)
    assert not ar.quote_exists("9 m", None)


# ---------------------------------------------------------------------------
# diff_atom_sets — re-extractor finding diff logic
# ---------------------------------------------------------------------------


def test_diff_identical_atoms_yields_no_mismatch():
    assert ar.diff_atom_sets([_atom()], [_atom()]) == []


def test_diff_value_mismatch_is_critical():
    out = ar.diff_atom_sets([_atom(value=4.0)], [_atom(value=6.0)])
    assert len(out) == 1
    m = out[0]
    assert m["kind"] == "field_mismatch"
    assert m["field"] == "value"
    assert m["db_value"] == 4.0
    assert m["fresh_value"] == 6.0
    assert ar.mismatch_severity(m) == "critical"


def test_diff_unit_and_operator_mismatches_detected():
    out = ar.diff_atom_sets([_atom()], [_atom(unit="m2", operator="lte")])
    fields = {m["field"] for m in out}
    assert fields == {"unit", "operator"}
    assert all(m["kind"] == "field_mismatch" for m in out)
    assert all(ar.mismatch_severity(m) == "critical" for m in out)


def test_diff_pathway_and_condition_mismatch_are_major():
    out = ar.diff_atom_sets(
        [_atom(pathway="deemed_to_comply", condition="")],
        [_atom(pathway="design_principle", condition="corner lots only")],
    )
    fields = {m["field"]: m for m in out}
    assert set(fields) == {"pathway", "condition"}
    assert ar.mismatch_severity(fields["pathway"]) == "major"
    assert ar.mismatch_severity(fields["condition"]) == "major"


def test_diff_condition_compare_ignores_case_and_whitespace():
    out = ar.diff_atom_sets(
        [_atom(condition="Corner   Lots only")], [_atom(condition="corner lots only")]
    )
    assert out == []


def test_diff_missing_atoms_both_directions():
    db_only = _atom(rule_key="site_cover", density_codes=["R40"])
    fresh_only = _atom(rule_key="open_space", density_codes=["R20"], value=45.0)
    out = ar.diff_atom_sets([db_only], [fresh_only])
    kinds = {m["kind"] for m in out}
    assert kinds == {"missing_in_reextraction", "missing_in_db"}
    by_kind = {m["kind"]: m for m in out}
    assert by_kind["missing_in_reextraction"]["rule_key"] == "site_cover"
    assert by_kind["missing_in_db"]["rule_key"] == "open_space"
    assert ar.mismatch_severity(by_kind["missing_in_db"]) == "major"
    assert ar.mismatch_severity(by_kind["missing_in_reextraction"]) == "minor"


def test_diff_value_tolerance_and_float_coercion():
    out = ar.diff_atom_sets([_atom(value=4.0)], [_atom(value=4.0000000001)])
    assert out == []


def test_atom_match_key_normalises_density_codes():
    a = _atom(density_codes=["r30", "R20"])
    b = _atom(density_codes=["R20", "R30"])
    assert ar.atom_match_key(a) == ar.atom_match_key(b)


# ---------------------------------------------------------------------------
# Prosecutor question generation — deterministic, DB-only inputs
# ---------------------------------------------------------------------------


def test_generate_prosecution_questions_deterministic():
    checks = ["setback_front", "site_cover"]
    codes = ["R30", "R20"]
    q1 = ar.generate_prosecution_questions(checks, codes)
    q2 = ar.generate_prosecution_questions(list(reversed(checks)), list(reversed(codes)))
    assert q1 == q2


def test_generate_prosecution_questions_coverage_and_edge_cases():
    qs = ar.generate_prosecution_questions(["setback_front", "site_cover"], ["R20", "R30"])
    keys = [q["key"] for q in qs]
    assert len(keys) == len(set(keys))
    assert "setback_front:R20:standard" in keys
    assert "site_cover:R30:standard" in keys
    scenarios = {q["scenario"] for q in qs}
    assert {"corner_lot", "battle_axe", "granny_flat", "mixed_pathway"} <= scenarios
    # every question is a non-empty string mentioning its density code
    for q in qs:
        assert q["density_code"] in q["question"]


def test_generate_prosecution_questions_no_edge_cases_flag():
    qs = ar.generate_prosecution_questions(["site_cover"], ["R30"], include_edge_cases=False)
    assert [q["key"] for q in qs] == ["site_cover:R30:standard"]


# ---------------------------------------------------------------------------
# Conflict prosecutor — fact-pattern generation + single-winner resolution
# ---------------------------------------------------------------------------


def test_generate_fact_patterns_deterministic_and_complete():
    p1 = ar.generate_fact_patterns(["R30", "R20"])
    p2 = ar.generate_fact_patterns(["R20", "R30"])
    assert p1 == p2
    keys = [p["key"] for p in p1]
    assert len(keys) == len(set(keys))
    lot_types = {p["lot_type"] for p in p1}
    assert lot_types == {"standard", "corner", "battle_axe"}
    assert any(p["pathway"] == "design_principle" for p in p1)
    assert any(p["dwelling_type"] == "ancillary_dwelling" for p in p1)
    codes = {p["density_code"] for p in p1}
    assert codes == {"R20", "R30"}


def _fact(**overrides) -> dict:
    base = {
        "key": "R30|standard|deemed_to_comply",
        "density_code": "R30",
        "lot_type": "standard",
        "pathway": "deemed_to_comply",
        "dwelling_type": "single_house",
    }
    base.update(overrides)
    return base


def test_resolve_winner_single_winner():
    res = ar.resolve_winner([_atom()], _fact())
    assert res["outcome"] == "one_winner"
    assert len(res["winners"]) == 1


def test_resolve_winner_same_requirement_twice_is_one_winner():
    res = ar.resolve_winner([_atom(rule_id="r-1"), _atom(rule_id="r-2")], _fact())
    assert res["outcome"] == "one_winner"


def test_resolve_winner_two_distinct_values_is_multiple_winners():
    res = ar.resolve_winner([_atom(value=4.0), _atom(rule_id="r-2", value=6.0)], _fact())
    assert res["outcome"] == "multiple_winners"
    assert len(res["winners"]) == 2


def test_resolve_winner_zero_winners_when_no_code_match():
    res = ar.resolve_winner([_atom(density_codes=["R80"])], _fact(density_code="R20"))
    assert res["outcome"] == "zero_winners"
    assert res["candidates_considered"] == 0


def test_resolve_winner_corner_exception_fires_and_wins():
    standard = _atom(value=4.0)
    exception = _atom(
        rule_id="r-exc", rule_type="exception", value=2.0, condition="on corner lots"
    )
    res = ar.resolve_winner([standard, exception], _fact(lot_type="corner"))
    assert res["outcome"] == "one_winner"
    assert res["winners"][0]["rule_id"] == "r-exc"
    assert res["fired_exceptions"] and res["fired_exceptions"][0]["rule_id"] == "r-exc"
    # on a standard lot the exception must NOT fire
    res2 = ar.resolve_winner([standard, exception], _fact(lot_type="standard"))
    assert res2["winners"][0]["rule_id"] == "r-1"


def test_resolve_winner_flags_dead_exception():
    exception = _atom(rule_id="r-dead", rule_type="exception", condition="")
    res = ar.resolve_winner([_atom(), exception], _fact())
    assert [e["rule_id"] for e in res["dead_exceptions"]] == ["r-dead"]


def test_resolve_winner_pathway_filtering():
    dtc = _atom(pathway="deemed_to_comply")
    dp = _atom(rule_id="r-dp", pathway="design_principle", value=3.0)
    res = ar.resolve_winner([dtc, dp], _fact(pathway="design_principle"))
    assert res["outcome"] == "one_winner"
    assert res["winners"][0]["rule_id"] == "r-dp"


# ---------------------------------------------------------------------------
# Judge / Defense — deterministic quote-existence decisions
# ---------------------------------------------------------------------------

CLAUSE = (
    "C2.1 Buildings shall be set back at least 4m from the primary street. "
    "On corner lots a 2m secondary street setback is permitted."
)


def test_judge_decide_unanchored_attack_is_rejected():
    assert ar.judge_decide("must be 12m from the street", CLAUSE, "at least 4m") == "rejected"


def test_judge_decide_anchored_attack_vs_unanchored_db_is_confirmed():
    verdict = ar.judge_decide("2m secondary street setback", CLAUSE, "a 9m setback applies")
    assert verdict == "confirmed"


def test_judge_decide_both_anchored_is_pending():
    verdict = ar.judge_decide(
        "2m secondary street setback", CLAUSE, "set back at least 4m"
    )
    assert verdict == "pending"


def test_defense_decide_rejects_with_verbatim_quote():
    claim = {"kind": "field_mismatch", "field": "value"}
    action, detail = ar.defense_decide(
        claim, "must be 12m from the street", CLAUSE, "set back at least 4m"
    )
    assert action == "reject"
    assert detail["quote"] == "set back at least 4m"


def test_defense_decide_proposes_fix_when_db_unanchored():
    claim = {"kind": "field_mismatch", "field": "value"}
    action, detail = ar.defense_decide(
        claim, "2m secondary street setback", CLAUSE, "a 9m setback applies"
    )
    assert action == "fix"
    assert detail["proposed_fix"] == claim
    assert "auto-mutat" in detail["note"] or "not auto" in detail["note"]


def test_defense_decide_leaves_disputed_finding_open():
    claim = {"kind": "field_mismatch", "field": "value"}
    action, _ = ar.defense_decide(
        claim, "2m secondary street setback", CLAUSE, "set back at least 4m"
    )
    assert action == "open"


def test_defense_decide_structural_kinds_get_fix_without_source():
    for kind in ("missing_instrument", "zero_winners", "multiple_winners", "dead_exception"):
        action, detail = ar.defense_decide({"kind": kind}, None, None, None)
        assert action == "fix", kind
        assert detail["proposed_fix"]["kind"] == kind


# ---------------------------------------------------------------------------
# Gap hunter — index link extraction + deterministic manifest diff
# ---------------------------------------------------------------------------

INDEX_HTML = """
<html><body>
<a href="/spp/7-3">State Planning Policy 7.3 &ndash; Residential Design Codes</a>
<a href="/spp/3-7">State Planning Policy 3.7 Planning in Bushfire Prone Areas</a>
<a href="/contact">Contact us</a>
<a href="/lpp/4-2"><span>Local Planning Policy 4.2 Activity Centres</span></a>
</body></html>
"""


def test_extract_index_links_strips_tags_and_entities():
    links = ar.extract_index_links(INDEX_HTML)
    texts = [link["text"] for link in links]
    assert "Local Planning Policy 4.2 Activity Centres" in texts
    assert any("State Planning Policy 7.3" in t for t in texts)
    assert all("<" not in t for t in texts)


def test_diff_index_entries_flags_only_unknown_instruments():
    entries = ar.extract_index_links(INDEX_HTML)
    unmatched = ar.diff_index_entries(
        entries,
        manifest_names=["State Planning Policy 7.3 - Residential Design Codes"],
        alias_exact=[],
        alias_regex=[r"Bushfire\s+Prone"],
    )
    texts = [e["text"] for e in unmatched]
    # SPP 7.3 matched by manifest, 3.7 by alias regex, "Contact us" is not an instrument
    assert texts == ["Local Planning Policy 4.2 Activity Centres"]


def test_diff_index_entries_exact_alias_and_dedup():
    entries = [
        {"href": "/a", "text": "Local Planning Policy 4.2 Activity Centres"},
        {"href": "/b", "text": "Local  Planning Policy 4.2 ACTIVITY centres"},
    ]
    unmatched = ar.diff_index_entries(entries, [], ["Local Planning Policy 4.2 Activity Centres"], [])
    assert unmatched == []
    unmatched2 = ar.diff_index_entries(entries, [], [], [])
    assert len(unmatched2) == 1  # case/whitespace duplicates collapse to one finding


# ---------------------------------------------------------------------------
# Closure — stopping-rule computation
# ---------------------------------------------------------------------------


def test_compute_closure_no_rounds_not_closed():
    out = ar.compute_closure({})
    assert out["closed"] is False
    assert out["rounds_run"] == 0


def test_compute_closure_two_trailing_clean_rounds_closes():
    out = ar.compute_closure({
        1: {"confirmed": 3, "open": 0},
        2: {"confirmed": 0, "open": 0},
        3: {"confirmed": 0, "open": 0},
    })
    assert out["closed"] is True
    assert out["trailing_clean_rounds"] == 2


def test_compute_closure_confirmed_in_last_round_blocks():
    out = ar.compute_closure({
        1: {"confirmed": 0, "open": 0},
        2: {"confirmed": 0, "open": 0},
        3: {"confirmed": 1, "open": 0},
    })
    assert out["closed"] is False
    assert out["trailing_clean_rounds"] == 0


def test_compute_closure_open_findings_block():
    out = ar.compute_closure({
        1: {"confirmed": 0, "open": 0},
        2: {"confirmed": 0, "open": 2},
    })
    assert out["closed"] is False


def test_compute_closure_single_clean_round_not_enough():
    out = ar.compute_closure({1: {"confirmed": 0, "open": 0}})
    assert out["closed"] is False
    assert out["trailing_clean_rounds"] == 1


# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------


def test_canonical_claim_is_order_independent():
    a = ar.canonical_claim({"b": 1, "a": [2, 3]})
    b = ar.canonical_claim({"a": [2, 3], "b": 1})
    assert a == b
    assert json.loads(a) == {"a": [2, 3], "b": 1}


def test_parse_fresh_atoms_discards_unanchored_quotes():
    clause = "Site coverage shall not exceed 60% of the site area."
    payload = {
        "atoms": [
            {"rule_key": "site_cover", "rule_type": "standard", "pathway": "deemed_to_comply",
             "operator": "lte", "value": 60, "unit": "%",
             "applicability": {"density_codes": ["R30"], "dwelling_type": "any",
                               "condition": ""},
             "quote": "shall not exceed 60%"},
            {"rule_key": "site_cover", "rule_type": "standard", "pathway": "deemed_to_comply",
             "operator": "lte", "value": 70, "unit": "%",
             "applicability": {"density_codes": ["R40"], "dwelling_type": "any",
                               "condition": ""},
             "quote": "shall not exceed 70%"},  # hallucinated — not in the clause
        ]
    }
    atoms = ar.parse_fresh_atoms(payload, clause)
    assert len(atoms) == 1
    assert atoms[0]["value"] == 60.0
    assert atoms[0]["density_codes"] == ["R30"]

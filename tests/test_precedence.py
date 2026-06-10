"""Pure unit tests for the WA precedence ruleset, edge-quote validator and
the deterministic conflict sweep (Phase 4b of CORPUS_COMPLETENESS_PLAN).

No DB, no LLM, no network — synthetic rows only.  Any numeric/legal values in
these fixtures are illustrative test data, never real thresholds.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from draftcheck.checks.precedence import (
    EDGE_RELATIONS,
    EXCEPTION_PHRASES,
    MODIFICATION_PHRASES,
    PRECEDENCE_RULESET,
    CandidateRule,
    Edge,
    InstrumentLevel,
    instrument_level_for,
    resolve_precedence,
    validate_edge_quote,
)

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_conflict_sweep():
    spec = importlib.util.spec_from_file_location(
        "conflict_sweep", _SCRIPTS / "conflict_sweep.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conflict_sweep = _load_conflict_sweep()


def make_candidate(
    rule_id: str,
    level: InstrumentLevel,
    value: str = "v1",
    rule_type: str = "requirement",
    citation: str | None = None,
    clause_ref: str | None = None,
    sv: str | None = None,
) -> CandidateRule:
    return CandidateRule(
        rule_id=rule_id,
        rule_key="example.key",
        instrument_level=level,
        rule_type=rule_type,
        value_repr=value,
        citation=citation or f"citation for {rule_id}",
        clause_ref=clause_ref,
        source_version_id=sv,
    )


# ---------------------------------------------------------------------------
# Ruleset shape
# ---------------------------------------------------------------------------


class TestRulesetShape:
    def test_every_entry_carries_a_citation(self):
        for entry in PRECEDENCE_RULESET:
            assert entry.citation and len(entry.citation) > 20, entry.key

    def test_ruleset_is_ordered_and_typed(self):
        kinds = {e.kind for e in PRECEDENCE_RULESET}
        assert kinds <= {
            "exception_edge", "unconditional_level",
            "express_edge_required", "intra_level_express",
        }
        # The exception entry must be walked first.
        assert PRECEDENCE_RULESET[0].kind == "exception_edge"

    def test_level_mapping(self):
        assert instrument_level_for("local_planning_scheme") is InstrumentLevel.SCHEME
        assert instrument_level_for("r_codes") is InstrumentLevel.RCODES_STATE_POLICY
        assert instrument_level_for("local_planning_policy") is \
            InstrumentLevel.LOCAL_PLANNING_POLICY
        # Unknown types must never silently outrank mapped instruments.
        assert instrument_level_for("mystery_doc") is InstrumentLevel.GUIDANCE
        assert instrument_level_for(None) is InstrumentLevel.GUIDANCE


# ---------------------------------------------------------------------------
# resolve_precedence scenarios
# ---------------------------------------------------------------------------


class TestResolvePrecedence:
    def test_no_candidates_needs_more_info(self):
        res = resolve_precedence([], [])
        assert res.status == "needs_more_info"
        assert res.winner is None

    def test_single_candidate_wins(self):
        c = make_candidate("r1", InstrumentLevel.RCODES_STATE_POLICY)
        res = resolve_precedence([c], [])
        assert res.status == "winner"
        assert res.winner == c

    def test_exception_fires_over_base(self):
        base = make_candidate("base", InstrumentLevel.RCODES_STATE_POLICY, value="v_base")
        exc = make_candidate(
            "exc", InstrumentLevel.RCODES_STATE_POLICY, value="v_exc", rule_type="exception"
        )
        edge = Edge(from_ref="exc", to_ref="base", relation="exception_to",
                    review_status="approved")
        res = resolve_precedence([base, exc], [edge])
        assert res.status == "winner"
        assert res.winner.rule_id == "exc"
        assert any(t["entry"] == "exception_over_base" for t in res.trace)

    def test_exception_without_approved_edge_does_not_fire(self):
        base = make_candidate("base", InstrumentLevel.RCODES_STATE_POLICY, value="v_base")
        exc = make_candidate(
            "exc", InstrumentLevel.RCODES_STATE_POLICY, value="v_exc", rule_type="exception"
        )
        edge = Edge(from_ref="exc", to_ref="base", relation="exception_to",
                    review_status="pending_review")
        res = resolve_precedence([base, exc], [edge])
        assert res.status == "needs_more_info"
        assert len(res.surviving) == 2

    def test_scheme_does_not_beat_rcodes_without_express_edge(self):
        scheme = make_candidate("scheme", InstrumentLevel.SCHEME, value="v_scheme")
        rcodes = make_candidate("rcodes", InstrumentLevel.RCODES_STATE_POLICY,
                                value="v_rcodes")
        res = resolve_precedence([scheme, rcodes], [])
        assert res.status == "needs_more_info"
        assert {c.rule_id for c in res.surviving} == {"scheme", "rcodes"}
        # Both citations surfaced — never silently pick one.
        assert len(res.citations) == 2

    def test_scheme_overrides_rcodes_with_express_edge(self):
        scheme = make_candidate("scheme", InstrumentLevel.SCHEME, value="v_scheme")
        rcodes = make_candidate("rcodes", InstrumentLevel.RCODES_STATE_POLICY,
                                value="v_rcodes")
        edge = Edge(from_ref="scheme", to_ref="rcodes", relation="overrides",
                    review_status="approved")
        res = resolve_precedence([scheme, rcodes], [edge])
        assert res.status == "winner"
        assert res.winner.rule_id == "scheme"
        assert any(
            t["entry"] == "scheme_amends_rcodes_only_where_express" for t in res.trace
        )

    def test_express_edge_matches_on_lineage_refs(self):
        scheme = make_candidate("scheme", InstrumentLevel.SCHEME, value="v_scheme",
                                clause_ref="clause-9", sv="sv-scheme")
        rcodes = make_candidate("rcodes", InstrumentLevel.RCODES_STATE_POLICY,
                                value="v_rcodes", sv="sv-rcodes")
        edge = Edge(from_ref="clause-9", to_ref="sv-rcodes", relation="modifies",
                    review_status="approved", from_type="clause", to_type="source_version")
        res = resolve_precedence([scheme, rcodes], [edge])
        assert res.status == "winner"
        assert res.winner.rule_id == "scheme"

    def test_pending_express_edge_does_not_count(self):
        scheme = make_candidate("scheme", InstrumentLevel.SCHEME, value="v_scheme")
        rcodes = make_candidate("rcodes", InstrumentLevel.RCODES_STATE_POLICY,
                                value="v_rcodes")
        edge = Edge(from_ref="scheme", to_ref="rcodes", relation="overrides",
                    review_status="pending_review")
        res = resolve_precedence([scheme, rcodes], [edge])
        assert res.status == "needs_more_info"

    def test_deemed_provisions_beat_scheme_without_edge(self):
        deemed = make_candidate("deemed", InstrumentLevel.DEEMED_PROVISIONS, value="v_d")
        scheme = make_candidate("scheme", InstrumentLevel.SCHEME, value="v_s")
        res = resolve_precedence([deemed, scheme], [])
        assert res.status == "winner"
        assert res.winner.rule_id == "deemed"
        assert any(t["entry"] == "deemed_provisions_prevail" for t in res.trace)

    def test_scheme_beats_lpp_without_edge(self):
        scheme = make_candidate("scheme", InstrumentLevel.SCHEME, value="v_s")
        lpp = make_candidate("lpp", InstrumentLevel.LOCAL_PLANNING_POLICY, value="v_l")
        res = resolve_precedence([scheme, lpp], [])
        assert res.status == "winner"
        assert res.winner.rule_id == "scheme"

    def test_lpp_beats_rcodes_only_with_empowerment_edge(self):
        lpp = make_candidate("lpp", InstrumentLevel.LOCAL_PLANNING_POLICY, value="v_l")
        rcodes = make_candidate("rcodes", InstrumentLevel.RCODES_STATE_POLICY, value="v_r")
        # Without empowerment: two winners -> needs_more_info.
        res = resolve_precedence([lpp, rcodes], [])
        assert res.status == "needs_more_info"
        # With approved empowerment edge: LPP wins.
        edge = Edge(from_ref="lpp", to_ref="rcodes", relation="applies_with",
                    review_status="approved")
        res2 = resolve_precedence([lpp, rcodes], [edge])
        assert res2.status == "winner"
        assert res2.winner.rule_id == "lpp"
        assert any(t["entry"] == "lpp_where_scheme_empowers" for t in res2.trace)

    def test_statutory_beats_guidance(self):
        rcodes = make_candidate("rcodes", InstrumentLevel.RCODES_STATE_POLICY, value="v_r")
        guide = make_candidate("guide", InstrumentLevel.GUIDANCE, value="v_g")
        res = resolve_precedence([rcodes, guide], [])
        assert res.status == "winner"
        assert res.winner.rule_id == "rcodes"

    def test_two_winners_same_level_needs_more_info(self):
        a = make_candidate("a", InstrumentLevel.RCODES_STATE_POLICY, value="v_a")
        b = make_candidate("b", InstrumentLevel.RCODES_STATE_POLICY, value="v_b")
        res = resolve_precedence([a, b], [])
        assert res.status == "needs_more_info"
        assert res.winner is None
        assert len(res.surviving) == 2

    def test_agreeing_survivors_are_not_a_conflict(self):
        a = make_candidate("a", InstrumentLevel.RCODES_STATE_POLICY, value="same")
        b = make_candidate("b", InstrumentLevel.RCODES_STATE_POLICY, value="same")
        res = resolve_precedence([a, b], [])
        assert res.status == "winner"

    def test_intra_level_express_override(self):
        a = make_candidate("a", InstrumentLevel.SCHEME, value="v_a")
        b = make_candidate("b", InstrumentLevel.SCHEME, value="v_b")
        edge = Edge(from_ref="a", to_ref="b", relation="overrides",
                    review_status="approved")
        res = resolve_precedence([a, b], [edge])
        assert res.status == "winner"
        assert res.winner.rule_id == "a"


# ---------------------------------------------------------------------------
# Edge-quote validator (Phase 4b item 2 — "No quote, no edge")
# ---------------------------------------------------------------------------


DOC = (
    "5.1.2 Street setbacks.  Notwithstanding the provisions of the Residential "
    "Design Codes, the setback standards in Table 2 of this Scheme prevail to the "
    "extent of any inconsistency.  Lots are generally rectangular in this area."
)


class TestValidateEdgeQuote:
    def test_accepts_verbatim_quote_with_modification_language(self):
        quote = ("Notwithstanding the provisions of the Residential Design Codes, the "
                 "setback standards in Table 2 of this Scheme prevail")
        v = validate_edge_quote(quote, DOC)
        assert v.ok, v.detail

    def test_accepts_whitespace_mangled_quote(self):
        quote = ("Notwithstanding   the provisions\nof the Residential Design Codes, "
                 "the setback standards in Table 2 of this Scheme prevail")
        assert validate_edge_quote(quote, DOC).ok

    def test_rejects_quote_not_in_document(self):
        v = validate_edge_quote(
            "Despite anything in this policy, the rear setback may be varied", DOC
        )
        assert not v.ok
        assert "not found" in v.detail

    def test_rejects_quote_without_modification_language(self):
        v = validate_edge_quote("Lots are generally rectangular in this area.", DOC)
        assert not v.ok
        assert "closed" in v.detail

    def test_rejects_empty_and_short_quotes(self):
        assert not validate_edge_quote("", DOC).ok
        assert not validate_edge_quote(None, DOC).ok
        assert not validate_edge_quote("unless", DOC).ok  # too short to anchor

    def test_phrase_lists_are_closed_and_lowercase(self):
        for phrase in MODIFICATION_PHRASES + EXCEPTION_PHRASES:
            assert phrase == phrase.lower()
        assert set(EXCEPTION_PHRASES) <= set(MODIFICATION_PHRASES)
        assert "exception_to" in EDGE_RELATIONS


# ---------------------------------------------------------------------------
# Conflict sweep on synthetic rows (no DB)
# ---------------------------------------------------------------------------


def rule_row(
    rid: str,
    rule_key: str = "example.key",
    value: float = 1.0,
    operator: str = "gte",
    unit: str = "m",
    source_type: str = "r_codes",
    lifecycle_status: str = "approved",
    r_codes: list[str] | None = None,
    zones: list[str] | None = None,
    condition: dict | None = None,
    clause_id: str | None = None,
    sv: str | None = None,
) -> dict:
    return {
        "id": rid,
        "rule_key": rule_key,
        "rule_type": "requirement",
        "pathway": "none",
        "lifecycle_status": lifecycle_status,
        "operator": operator,
        "value_json": {"value": value},
        "unit": unit,
        "condition_json": condition or {},
        "applicable_r_codes": r_codes,
        "applicable_zones": zones,
        "clause_id": clause_id,
        "source_version_id": sv or f"sv-{rid}",
        "source_type": source_type,
        "citation": f"Example Instrument cl {rid}",
    }


class TestConflictSweep:
    def test_conflict_detected_without_precedence_path(self):
        a = rule_row("a", value=1.0, source_type="r_codes")
        b = rule_row("b", value=2.0, source_type="local_planning_scheme")
        findings = conflict_sweep.find_conflicts([a, b], [])
        assert len(findings) == 1
        f = findings[0]
        assert f["kind"] == "rule_conflict"
        assert f["rule_ids"] == ["a", "b"]
        assert len(f["citations"]) == 2  # both citations, never silently pick one

    def test_no_conflict_with_express_override_edge(self):
        a = rule_row("a", value=1.0, source_type="r_codes")
        b = rule_row("b", value=2.0, source_type="local_planning_scheme")
        edges = [{"from_type": "rule", "from_ref": "b", "to_type": "rule",
                  "to_ref": "a", "relation": "overrides", "review_status": "approved"}]
        assert conflict_sweep.find_conflicts([a, b], edges) == []

    def test_no_conflict_when_applicability_disjoint(self):
        a = rule_row("a", value=1.0, r_codes=["R20"])
        b = rule_row("b", value=2.0, r_codes=["R40"])
        assert conflict_sweep.find_conflicts([a, b], []) == []

    def test_null_applicability_means_applies_to_all(self):
        a = rule_row("a", value=1.0, r_codes=None)
        b = rule_row("b", value=2.0, r_codes=["R40"])
        assert len(conflict_sweep.find_conflicts([a, b], [])) == 1

    def test_same_value_is_not_a_conflict(self):
        a = rule_row("a", value=1.0)
        b = rule_row("b", value=1.0)
        assert conflict_sweep.find_conflicts([a, b], []) == []

    def test_non_approved_rules_ignored(self):
        a = rule_row("a", value=1.0)
        b = rule_row("b", value=2.0, lifecycle_status="pending_review")
        assert conflict_sweep.find_conflicts([a, b], []) == []

    def test_dwelling_type_disjointness(self):
        a = rule_row("a", value=1.0, condition={"dwelling_type": "single_house"})
        b = rule_row("b", value=2.0, condition={"dwelling_type": "multiple_dwelling"})
        assert conflict_sweep.find_conflicts([a, b], []) == []


class TestDependencyClosure:
    def test_depends_on_missing_target_is_a_finding(self):
        a = rule_row("a")
        edges = [{"from_type": "rule", "from_ref": "a", "to_type": "rule",
                  "to_ref": "ghost", "relation": "depends_on",
                  "review_status": "approved"}]
        findings = conflict_sweep.check_dependency_closure([a], edges)
        assert len(findings) == 1
        assert findings[0]["kind"] == "dependency_unresolved"

    def test_depends_on_approved_target_is_clean(self):
        a = rule_row("a")
        definition = rule_row("def1", rule_key="definition.site_area")
        edges = [{"from_type": "rule", "from_ref": "a", "to_type": "rule",
                  "to_ref": "def1", "relation": "depends_on",
                  "review_status": "approved"}]
        assert conflict_sweep.check_dependency_closure([a, definition], edges) == []

    def test_depends_on_unapproved_target_is_a_finding(self):
        a = rule_row("a")
        definition = rule_row("def1", lifecycle_status="pending_review")
        edges = [{"from_type": "rule", "from_ref": "a", "to_type": "rule",
                  "to_ref": "def1", "relation": "depends_on",
                  "review_status": "approved"}]
        findings = conflict_sweep.check_dependency_closure([a, definition], edges)
        assert len(findings) == 1

    def test_external_reference_target_is_a_finding(self):
        a = rule_row("a")
        edges = [{"from_type": "rule", "from_ref": "a",
                  "to_type": "external_reference", "to_ref": "AS 1234",
                  "relation": "depends_on", "review_status": "approved"}]
        assert len(conflict_sweep.check_dependency_closure([a], edges)) == 1

    def test_condition_json_refs_must_resolve(self):
        a = rule_row("a", condition={"definition_refs": ["definition.site_area"]})
        findings = conflict_sweep.check_dependency_closure([a], [])
        assert len(findings) == 1
        definition = rule_row("def1", rule_key="definition.site_area")
        assert conflict_sweep.check_dependency_closure([a, definition], []) == []

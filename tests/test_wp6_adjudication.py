"""Unit tests for family-aware core-vote adjudication (WP6).

Pure-function tests — no DB, no LLM.
"""

from draftcheck.extraction.adjudication import (
    PENDING,
    PROMOTE,
    REASON_DENSITY,
    REASON_DWELLING,
    REASON_PATHWAY,
    REASON_SINGLE_FAMILY,
    Vote,
    adjudicate,
    core_of,
    group_by_core,
    model_family,
)

MM = "minimax:MiniMax-M2"
OA = "openai:gpt-4o"


def vote(**kw) -> Vote:
    base = dict(
        rule_key="primary_street_setback",
        rule_type="standard",
        pathway="deemed_to_comply",
        operator="gte",
        value=4.0,
        unit="m",
        density_codes=("R30",),
        dwelling_type="any",
        model=MM,
    )
    base.update(kw)
    return Vote(**base)


def test_model_family():
    assert model_family("openai:gpt-4o:challenge") == "openai"
    assert model_family("minimax:MiniMax-M2") == "minimax"
    assert model_family("") == ""


def test_core_ignores_applicability_metadata():
    a = vote(density_codes=("R30",), dwelling_type="any")
    b = vote(density_codes=("R30", "R40"), dwelling_type="single_house")
    assert core_of(a) == core_of(b)


def test_two_families_same_core_promotes():
    d = adjudicate([vote(model=MM), vote(model=OA)])
    assert d.outcome == PROMOTE
    assert d.confidence == 0.9
    assert d.families == ("minimax", "openai")
    assert d.density_codes == ("R30",)


def test_same_family_twice_is_one_vote():
    # temp-0 duplicate passes must not self-confirm
    d = adjudicate([vote(model=MM), vote(model=MM)])
    assert d.outcome == PENDING
    assert d.reason == REASON_SINGLE_FAMILY


def test_three_votes_two_families_full_agreement_is_095():
    d = adjudicate([vote(model=MM), vote(model=MM), vote(model=OA)])
    assert d.outcome == PROMOTE
    assert d.confidence == 0.95


def test_pathway_disagreement_blocks():
    d = adjudicate([vote(model=MM), vote(model=OA, pathway="design_principle")])
    assert d.outcome == PENDING
    assert d.reason == REASON_PATHWAY


def test_pathway_majority_wins_with_two_distinct_families():
    """Two families agree on deemed_to_comply, one openai dissenter -> promote
    with the majority pathway and record the loser as dissent."""
    AN = "anthropic:claude-sonnet-4-6"
    d = adjudicate([
        vote(model=MM, pathway="deemed_to_comply"),
        vote(model=AN, pathway="deemed_to_comply"),
        vote(model=OA, pathway="design_principle"),
    ])
    assert d.outcome == PROMOTE
    assert d.pathway == "deemed_to_comply"
    assert "pathway_dissent_design_principle" in d.dissent


def test_pathway_majority_blocks_when_winner_is_single_family():
    """Two openai votes for one pathway, one minimax for another. The majority
    pathway is single-family — still PEND (independence requirement holds)."""
    d = adjudicate([
        vote(model=OA, pathway="deemed_to_comply"),
        vote(model=OA + ":challenge", pathway="deemed_to_comply"),
        vote(model=MM, pathway="design_principle"),
    ])
    assert d.outcome == PENDING
    assert d.reason == REASON_PATHWAY


def test_pathway_tied_count_pends():
    """1 vs 1 tie pends, even with two families."""
    d = adjudicate([
        vote(model=MM, pathway="deemed_to_comply"),
        vote(model=OA, pathway="design_principle"),
    ])
    assert d.outcome == PENDING
    assert d.reason == REASON_PATHWAY


def test_density_codes_intersect_conservatively():
    d = adjudicate([
        vote(model=MM, density_codes=("R30", "R40")),
        vote(model=OA, density_codes=("R30",)),
    ])
    assert d.outcome == PROMOTE
    assert d.density_codes == ("R30",)
    assert "density_codes_narrowed" in d.dissent
    assert d.confidence == 0.85


def test_density_code_empty_intersection_blocks():
    d = adjudicate([
        vote(model=MM, density_codes=("R30",)),
        vote(model=OA, density_codes=("R40",)),
    ])
    assert d.outcome == PENDING
    assert d.reason == REASON_DENSITY


def test_omitted_codes_do_not_widen():
    d = adjudicate([
        vote(model=MM, density_codes=("R30",)),
        vote(model=OA, density_codes=()),
    ])
    assert d.outcome == PROMOTE
    assert d.density_codes == ("R30",)
    assert "density_codes_partial" in d.dissent


def test_dwelling_specific_narrows_any():
    d = adjudicate([
        vote(model=MM, dwelling_type="single_house"),
        vote(model=OA, dwelling_type="any"),
    ])
    assert d.outcome == PROMOTE
    assert d.dwelling_type == "single_house"
    assert "dwelling_type_narrowed" in d.dissent


def test_two_specific_dwelling_types_block():
    d = adjudicate([
        vote(model=MM, dwelling_type="single_house"),
        vote(model=OA, dwelling_type="multiple_dwelling"),
    ])
    assert d.outcome == PENDING
    assert d.reason == REASON_DWELLING


def test_rule_type_mix_is_dissent_not_block():
    d = adjudicate([
        vote(model=MM, rule_type="standard"),
        vote(model=OA, rule_type="deemed_to_comply"),
    ])
    assert d.outcome == PROMOTE
    assert "rule_type_mixed" in d.dissent


def test_group_by_core_separates_different_values():
    votes = [vote(value=4.0), vote(value=4.5, model=OA)]
    groups = group_by_core(votes)
    assert len(groups) == 2


def test_challenge_model_counts_as_its_family():
    d = adjudicate([vote(model=MM), vote(model="openai:gpt-4o:challenge")])
    assert d.outcome == PROMOTE

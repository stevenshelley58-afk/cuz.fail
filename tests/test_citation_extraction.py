"""Unit tests for the deterministic citation extractor (WP5 / Phase 3).

Pure — no DB, no LLM. Exercises extraction over realistic WA planning text
(R-Codes clause style, scheme text style), alias normalization / resolution
helpers, and the closed out-of-scope classification list from
docs/CORPUS_SCOPE.md.
"""

from __future__ import annotations

import re

from draftcheck.extraction.citations import (
    PATTERNS,
    build_alias_map,
    candidate_keys,
    classify_out_of_scope,
    default_category,
    extract_references,
    normalize_instrument_key,
    out_of_scope_note,
    resolve_key,
)


def refs_by_key(text):
    return {r.instrument_key: r for r in extract_references(text) if r.instrument_key}


# ---------------------------------------------------------------------------
# R-Codes clause style
# ---------------------------------------------------------------------------


class TestRCodesStyleText:
    TEXT = (
        "C2.1 Buildings set back from the primary street in accordance with "
        "clause 5.1.2 of the Residential Design Codes Volume 1, except where a "
        "local development plan adopted under the deemed provisions provides "
        "otherwise. Garages to comply with AS 2890.1 and the requirements of "
        "NCC Volume Two."
    )

    def test_clause_of_instrument(self):
        refs = extract_references(self.TEXT)
        composite = [r for r in refs if r.pattern == "clause_of_instrument"]
        assert len(composite) == 1
        ref = composite[0]
        assert ref.clause_path == "5.1.2"
        assert ref.instrument_key == "residential design codes volume 1"
        assert ref.raw.startswith("clause 5.1.2 of the Residential Design Codes")

    def test_companion_references(self):
        keys = set(refs_by_key(self.TEXT))
        assert "deemed provisions" in keys
        assert "as 2890.1" in keys
        assert "ncc volume two" in keys

    def test_offsets_are_exact(self):
        for ref in extract_references(self.TEXT):
            assert self.TEXT[ref.start : ref.end] == ref.raw

    def test_no_double_count_of_contained_match(self):
        # "Residential Design Codes" inside the composite span must not also
        # surface as a standalone r_codes reference.
        refs = extract_references(self.TEXT)
        assert sum(1 for r in refs if r.pattern == "r_codes") == 0


# ---------------------------------------------------------------------------
# Scheme text style
# ---------------------------------------------------------------------------


class TestSchemeStyleText:
    TEXT = (
        "Notwithstanding clause 32 of the Scheme, development within the "
        "Coastal Zone must comply with State Planning Policy 2.6 and the "
        "deemed provisions in Schedule 2 of the Planning and Development "
        "(Local Planning Schemes) Regulations 2015. Residential development "
        "shall satisfy the R-Codes and Local Planning Policy 5.6 - Vehicle "
        "Access, having due regard to the Planning and Development Act 2005."
    )

    def test_expected_keys(self):
        keys = refs_by_key(self.TEXT)
        assert keys["scheme"].clause_path == "32"
        assert "spp 2.6" in keys
        assert "deemed provisions" in keys
        assert "r-codes" in keys
        assert "lpp 5.6" in keys
        assert "planning and development act 2005" in keys

    def test_schedule_of_regulations(self):
        keys = refs_by_key(self.TEXT)
        ref = keys["planning and development local planning schemes regulations 2015"]
        assert ref.clause_path == "Schedule 2"
        assert ref.pattern == "schedule_reference"

    def test_pd_act_extracted_once(self):
        refs = extract_references(self.TEXT)
        pd = [r for r in refs if r.instrument_key == "planning and development act 2005"]
        assert len(pd) == 1  # specific pattern wins over the generic act pattern


# ---------------------------------------------------------------------------
# Individual pattern coverage
# ---------------------------------------------------------------------------


class TestPatternCoverage:
    def test_spp_variants(self):
        for snippet, key in [
            ("SPP 7.3 applies", "spp 7.3"),
            ("SPP No. 3.7 applies", "spp 3.7"),
            ("State Planning Policy 3.7 applies", "spp 3.7"),
            ("SPP7.3 applies", "spp 7.3"),
        ]:
            assert key in refs_by_key(snippet), snippet

    def test_australian_standards(self):
        keys = refs_by_key("Comply with AS 3959, AS/NZS 1170.2 and AS 2870:2011.")
        assert {"as 3959", "as/nzs 1170.2", "as 2870"} <= set(keys)

    def test_lowercase_as_not_matched(self):
        assert refs_by_key("such as setbacks and walls") == {}

    def test_ncc_variants(self):
        text = "Building Code of Australia, BCA, NCC Volume 1, NCC Volume Two and the NCC."
        keys = set(refs_by_key(text))
        assert {"building code of australia", "bca", "ncc volume one", "ncc volume two",
                "ncc"} <= keys

    def test_r_codes_variants(self):
        assert "r-codes" in refs_by_key("the R-Codes apply")
        assert "r-codes" in refs_by_key("the R Codes apply")
        assert "residential design codes" in refs_by_key("Residential Design Codes apply")
        assert "r-codes volume 2" in refs_by_key("R-Codes Volume 2 applies")
        assert "residential design codes volume 2" in refs_by_key(
            "the Residential Design Codes - Apartments"
        )

    def test_region_schemes(self):
        text = "land reserved under the MRS, the Peel Region Scheme and GBRS"
        keys = set(refs_by_key(text))
        assert {"metropolitan region scheme", "peel region scheme",
                "greater bunbury region scheme"} <= keys

    def test_the_act_and_the_regulations(self):
        keys = refs_by_key("in accordance with the Act and the Regulations")
        assert "planning and development act 2005" in keys
        assert "planning and development local planning schemes regulations 2015" in keys

    def test_tps_forms(self):
        assert "tps 3" in refs_by_key("approval under TPS3 is required")
        assert "town planning scheme no 3" in refs_by_key("Town Planning Scheme No. 3 applies")
        assert "city of cockburn town planning scheme no 3" in refs_by_key(
            "the City of Cockburn Town Planning Scheme No. 3"
        )

    def test_lpp_forms(self):
        assert "lpp 1.2" in refs_by_key("LPP 1.2 applies")
        assert "lpp 5.23" in refs_by_key("Local Planning Policy 5.23 - Tree Protection")

    def test_generic_act_with_year(self):
        keys = refs_by_key("subject to the Strata Titles Act 1985 and the Building Act 2011")
        assert "strata titles act 1985" in keys
        assert "building act 2011" in keys

    def test_article_separates_two_instruments(self):
        keys = set(refs_by_key(
            "see the Metropolitan Region Scheme and the Planning and Development Act 2005"
        ))
        assert "metropolitan region scheme" in keys
        assert "planning and development act 2005" in keys
        assert not any(" and the " in k for k in keys)

    def test_bushfire_guidelines(self):
        assert "guidelines for planning in bushfire prone areas" in refs_by_key(
            "SPP 3.7 and the Guidelines for Planning in Bushfire Prone Areas"
        )

    def test_internal_schedule_reference(self):
        refs = extract_references("as set out in Schedule 4")
        assert len(refs) == 1
        assert refs[0].internal
        assert refs[0].instrument_key is None
        assert refs[0].clause_path == "Schedule 4"

    def test_composite_span_trims_at_instrument_boundary(self):
        # "AS 3959" after the cited instrument must survive as its own reference,
        # not be swallowed by the composite phrase.
        refs = extract_references(
            "Development shall comply with clause 5.1.2 of the R-Codes and AS 3959."
        )
        by_pattern = {r.pattern: r for r in refs}
        assert by_pattern["clause_of_instrument"].instrument_key == "r-codes"
        assert by_pattern["clause_of_instrument"].raw == "clause 5.1.2 of the R-Codes"
        assert by_pattern["as_standard"].instrument_key == "as 3959"

    def test_clause_of_schedule_is_internal(self):
        refs = extract_references("see clause 67(2) of Schedule 2 for procedure")
        assert all(r.instrument_key is None for r in refs)
        composite = [r for r in refs if r.pattern == "clause_of_instrument"]
        assert composite and composite[0].clause_path == "67(2)"

    def test_pattern_table_is_well_formed(self):
        names = [spec.name for spec in PATTERNS]
        assert len(names) == len(set(names))
        for spec in PATTERNS:
            assert isinstance(spec.regex, re.Pattern)
            assert callable(spec.build)


# ---------------------------------------------------------------------------
# Normalization + resolution
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_basic(self):
        assert normalize_instrument_key("The R-Codes") == "r-codes"
        assert normalize_instrument_key("R-CODES ") == "r-codes"
        assert normalize_instrument_key("TPS No. 3") == "tps no 3"
        assert normalize_instrument_key("SPP 7.3") == "spp 7.3"

    def test_punctuation_and_parens(self):
        assert (
            normalize_instrument_key(
                "The  Planning and Development (Local Planning Schemes) Regulations 2015"
            )
            == "planning and development local planning schemes regulations 2015"
        )

    def test_dash_separator_vs_intraword_hyphen(self):
        assert (
            normalize_instrument_key("LPP 5.23 - Tree Protection") == "lpp 5.23 tree protection"
        )
        assert normalize_instrument_key("Local Planning Policy 5.6 – Vehicle Access") == (
            "local planning policy 5.6 vehicle access"
        )

    def test_idempotent(self):
        for s in ("the R-Codes", "AS/NZS 1170.2", "SPP 2.0", "Town Planning Scheme No. 3"):
            once = normalize_instrument_key(s)
            assert normalize_instrument_key(once) == once


class TestCandidateKeys:
    def test_spp_zero_variants(self):
        assert "spp 2.0" in candidate_keys("spp 2")
        assert "spp 2" in candidate_keys("spp 2.0")

    def test_r_codes_residential_design_codes_bridge(self):
        assert "residential design codes volume 1" in candidate_keys("r-codes volume 1")
        assert "r-codes" in candidate_keys("residential design codes")

    def test_as_nzs_falls_back_to_as(self):
        assert "as 1170.2" in candidate_keys("as/nzs 1170.2")

    def test_tps_variants(self):
        cands = candidate_keys("tps 3")
        assert "tps3" in cands
        assert "town planning scheme no 3" in cands

    def test_lga_prefix_stripped(self):
        assert "town planning scheme no 3" in candidate_keys(
            "city of cockburn town planning scheme no 3"
        )

    def test_long_form_policy_names(self):
        assert "spp 3.7" in candidate_keys("state planning policy 3.7 bushfire")
        assert "lpp 5.6" in candidate_keys("local planning policy 5.6 vehicle access")

    def test_ncc_volume_digit_word_bridge(self):
        assert "ncc volume one" in candidate_keys("ncc volume 1")
        assert "ncc volume 1" in candidate_keys("ncc volume one")


class TestResolution:
    """'the R-Codes' / 'SPP 7.3' / 'Residential Design Codes Volume 1' are ONE instrument."""

    ALIASES = [
        # mirrors prod instrument_aliases rows (scripts/wp3_manifest_seed.py batch 2/4)
        ("State Planning Policy 7.3 Residential Design Codes Volume 1", "rc1"),
        ("SPP 7.3", "rc1"),
        ("R-Codes", "rc1"),
        ("the R-Codes", "rc1"),
        ("Residential Design Codes", "rc1"),
        ("Residential Design Codes Volume 1", "rc1"),
        ("R-Codes Volume 1", "rc1"),
        ("R-Codes Volume 2", "rc2"),
        ("Residential Design Codes - Apartments", "rc2"),
        ("TPS3", "tps3"),
        ("Town Planning Scheme No. 3", "tps3"),
        ("the Scheme", "tps3"),
        ("SPP 2.0", "spp2"),
    ]

    def test_one_instrument_many_names(self):
        amap = build_alias_map(self.ALIASES)
        for snippet in ("the R-Codes", "SPP 7.3", "Residential Design Codes Volume 1",
                        "the R Codes"):
            (ref,) = extract_references(snippet)
            assert resolve_key(ref.instrument_key, amap) == "rc1", snippet

    def test_volume_2_is_distinct(self):
        amap = build_alias_map(self.ALIASES)
        (ref,) = extract_references("the Residential Design Codes - Apartments")
        assert resolve_key(ref.instrument_key, amap) == "rc2"

    def test_scheme_and_tps_aliases(self):
        amap = build_alias_map(self.ALIASES)
        for snippet in ("the Scheme", "TPS3", "Town Planning Scheme No. 3",
                        "the City of Cockburn Town Planning Scheme No. 3"):
            (ref,) = extract_references(snippet)
            assert resolve_key(ref.instrument_key, amap) == "tps3", snippet

    def test_spp_dot_zero_bridging(self):
        amap = build_alias_map(self.ALIASES)
        (ref,) = extract_references("State Planning Policy 2.0 applies")
        assert resolve_key(ref.instrument_key, amap) == "spp2"
        (ref,) = extract_references("SPP 2 applies")
        assert resolve_key(ref.instrument_key, amap) == "spp2"

    def test_unresolvable_returns_none(self):
        amap = build_alias_map(self.ALIASES)
        (ref,) = extract_references("AS 3959 applies")
        assert resolve_key(ref.instrument_key, amap) is None

    def test_first_mapping_wins(self):
        amap = build_alias_map([("R-Codes", "first"), ("the R-Codes", "second")])
        assert amap == {"r-codes": "first"}


# ---------------------------------------------------------------------------
# Out-of-scope classification (closed list from docs/CORPUS_SCOPE.md)
# ---------------------------------------------------------------------------


class TestOutOfScope:
    def test_strata(self):
        assert classify_out_of_scope("strata titles act 1985") == "strata_titles"

    def test_building_act(self):
        assert classify_out_of_scope("building act 2011") == "building_act_process"

    def test_environmental(self):
        assert classify_out_of_scope("environmental protection act 1986") == (
            "environmental_protection"
        )

    def test_aboriginal_heritage(self):
        assert classify_out_of_scope("aboriginal cultural heritage act 2021") == (
            "aboriginal_cultural_heritage"
        )
        assert classify_out_of_scope("aboriginal heritage act 1972") == (
            "aboriginal_cultural_heritage"
        )

    def test_non_pilot_lga(self):
        assert classify_out_of_scope("city of stirling local planning scheme no 3") == (
            "non_pilot_lga"
        )
        assert classify_out_of_scope("shire of serpentine-jarrahdale tps 2") == "non_pilot_lga"

    def test_pilot_lga_in_scope(self):
        assert classify_out_of_scope("city of cockburn town planning scheme no 3") is None

    def test_lga_precedence_over_state_names(self):
        # Town of Victoria Park is a non-pilot LGA, not the state of Victoria.
        assert classify_out_of_scope("town of victoria park lps 1") == "non_pilot_lga"

    def test_draft_instrument(self):
        assert classify_out_of_scope("draft state planning policy 4.1") == "draft_instrument"

    def test_other_jurisdiction(self):
        assert classify_out_of_scope("nsw environmental planning policy") == "other_jurisdiction"

    def test_in_scope_instruments_are_none(self):
        for key in ("spp 7.3", "r-codes", "deemed provisions", "ncc volume one",
                    "planning and development act 2005", "as 3959",
                    "metropolitan region scheme", "lpp 5.23"):
            assert classify_out_of_scope(key) is None, key

    def test_context_is_instrument_only(self):
        # An in-scope key must stay in scope even with an instrument phrase context.
        assert classify_out_of_scope("spp 7.3", "SPP 7.3") is None

    def test_notes_exist_for_every_category(self):
        for key in ("strata_titles", "non_pilot_lga", "draft_instrument"):
            assert "CORPUS_SCOPE" in out_of_scope_note(key)


# ---------------------------------------------------------------------------
# Manifest category guesses
# ---------------------------------------------------------------------------


class TestDefaultCategory:
    def test_pattern_mapped(self):
        assert default_category("spp", "spp 7.3") == "state_planning_policy"
        assert default_category("as_standard", "as 3959") == "standard"
        assert default_category("ncc", "ncc volume one") == "building_code"
        assert default_category("tps", "tps 3") == "local_planning_scheme"

    def test_composite_falls_back_to_key(self):
        assert default_category("clause_of_instrument", "strata titles act 1985") == "act"
        assert default_category(
            "schedule_reference",
            "planning and development local planning schemes regulations 2015",
        ) == "regulations"
        assert default_category("clause_of_instrument", "r-codes volume 1") == (
            "state_planning_policy"
        )
        assert default_category("clause_of_instrument", "something unknown") == "uncategorised"

"""Tests for Stage 3 validators — no DB required."""

from draftcheck.extraction.validators import (
    validate_quote_anchor,
    validate_normative_language,
    validate_no_orphan_numbers,
    validate_unit_normalization,
    validate_rule_key,
    validate_unit_category_sanity,
    validate_value_finite,
    run_all_validators,
)


def test_quote_anchor_pass():
    r = validate_quote_anchor("not exceed 50 percent", "Site coverage shall not exceed 50 percent of the site area.")
    assert r.passed


def test_quote_anchor_fail_not_found():
    r = validate_quote_anchor("not exceed 80 percent", "Site coverage shall not exceed 50 percent of the site area.")
    assert not r.passed


def test_quote_anchor_fail_too_short():
    r = validate_quote_anchor("50%", "Site coverage shall not exceed 50 percent.")
    assert not r.passed


def test_quote_anchor_fail_empty():
    r = validate_quote_anchor("", "Site coverage shall not exceed 50 percent.")
    assert not r.passed


def test_quote_anchor_whitespace_normalized():
    # Extra whitespace in quote or text should not cause a false failure.
    r = validate_quote_anchor(
        "not  exceed 50",
        "Site coverage shall not exceed 50 percent.",
    )
    # Both sides are normalized, so this should pass.
    assert r.passed


def test_normative_language_pass():
    r = validate_normative_language("Site coverage shall not exceed 50 percent.", "rule_bearing")
    assert r.passed


def test_normative_language_fail_no_normative():
    r = validate_normative_language("This provision relates to site cover.", "rule_bearing")
    assert not r.passed


def test_normative_language_non_rule_bearing_skipped():
    # Non-rule-bearing clauses pass regardless of language.
    r = validate_normative_language("No normative language here at all.", "informational")
    assert r.passed


def test_normative_language_detail_lists_searched():
    r = validate_normative_language("This provision relates to site cover.", "rule_bearing")
    assert not r.passed
    # Detail should mention what was searched for.
    assert "searched" in r.detail.lower() or "normative" in r.detail.lower()


def test_no_orphan_numbers_pass():
    r = validate_no_orphan_numbers("not exceed 50 percent", 50)
    assert r.passed


def test_no_orphan_numbers_fail():
    r = validate_no_orphan_numbers("not exceed 60 percent", 50)
    assert not r.passed


def test_no_orphan_numbers_pass_float_as_int_in_text():
    # value_json = 50.0 should match "50" in the quote.
    r = validate_no_orphan_numbers("setback of 50 metres", 50.0)
    assert r.passed


def test_no_orphan_numbers_no_values():
    # No numeric values → always pass.
    r = validate_no_orphan_numbers("some quote text", None)
    assert r.passed


def test_no_orphan_numbers_dict_value():
    r = validate_no_orphan_numbers("between 4.5 and 9 metres", {"min": 4.5, "max": 9})
    assert r.passed


def test_unit_normalization_pass_m():
    r = validate_unit_normalization(4.5, "m")
    assert r.passed


def test_unit_normalization_pass_percent():
    r = validate_unit_normalization(50, "%")
    assert r.passed


def test_unit_normalization_pass_none():
    r = validate_unit_normalization(1, None)
    assert r.passed


def test_unit_normalization_fail_mm():
    r = validate_unit_normalization(4500, "mm")
    assert not r.passed


def test_unit_normalization_fail_cm():
    r = validate_unit_normalization(450, "cm")
    assert not r.passed


def test_unit_normalization_fail_percent_word():
    r = validate_unit_normalization(50, "percent")
    assert not r.passed


def test_rule_key_pass():
    r = validate_rule_key("site_cover")
    assert r.passed


def test_rule_key_fail():
    r = validate_rule_key("Hallucinated Check")
    assert not r.passed


def test_rule_key_open_vocab_passes_unhinted_snake_case():
    r = validate_rule_key("noise_attenuation_distance")
    assert r.passed
    assert "hinted=False" in r.detail


def test_rule_key_all_hint_keys():
    from draftcheck.extraction.vocabulary import RULE_KEY_HINTS
    for key in RULE_KEY_HINTS:
        r = validate_rule_key(key)
        assert r.passed, f"Expected {key!r} to be valid"


def test_unit_category_sanity():
    r = validate_unit_category_sanity({"value": 1200}, "length")
    assert not r.passed

    r = validate_unit_category_sanity({"value": 995}, "length")
    assert r.passed


def test_value_finite_rejects_infinity():
    r = validate_value_finite(float("inf"))
    assert not r.passed


def test_run_all_validators_all_pass():
    results = run_all_validators(
        quote="shall not exceed 50 percent of the site area",
        clause_text="Site coverage shall not exceed 50 percent of the site area.",
        disposition="rule_bearing",
        value_json=50,
        unit="%",
        rule_key="site_cover",
    )
    assert set(results.keys()) == {
        "quote_anchor", "normative_language", "no_orphan_numbers",
        "unit_normalization", "value_finite", "unit_category_sanity", "rule_key",
    }
    failed = [name for name, v in results.items() if not v["pass"]]
    assert failed == [], f"Expected all to pass, but failed: {failed}"


def test_run_all_validators_returns_dict_format():
    results = run_all_validators(
        quote="shall not exceed 50 percent of the site area",
        clause_text="Site coverage shall not exceed 50 percent of the site area.",
        disposition="rule_bearing",
        value_json=50,
        unit="%",
        rule_key="site_cover",
    )
    for name, v in results.items():
        assert "pass" in v, f"Missing 'pass' key in {name}"
        assert "detail" in v, f"Missing 'detail' key in {name}"
        assert isinstance(v["pass"], bool)
        assert isinstance(v["detail"], str)


def test_run_all_validators_unhinted_rule_key_passes():
    results = run_all_validators(
        quote="shall not exceed 50 percent of the site area",
        clause_text="Site coverage shall not exceed 50 percent of the site area.",
        disposition="rule_bearing",
        value_json=50,
        unit="%",
        rule_key="not_a_real_key",
    )
    assert results["rule_key"]["pass"]
    assert "hinted=False" in results["rule_key"]["detail"]

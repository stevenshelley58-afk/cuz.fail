"""Pure unit tests for scripts/wp6_rule_matrix.py and scripts/wp6_per_doc_gates.py.

No DB, no LLM: the scripts factor cell resolution, gap classification and the
per-doc gate into pure functions over plain dicts/lists; these tests exercise
that logic with synthetic rows.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import wp6_per_doc_gates as gates  # noqa: E402
import wp6_rule_matrix as matrix  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic row factories
# ---------------------------------------------------------------------------


def _rule(rule_id="rule-1", base="primary_street_setback", codes=("R30",), value=4.0, **over):
    suffix = "_".join(c.replace("-", "").replace(".", "p") for c in codes) or "all"
    row = {
        "id": rule_id,
        "rule_key": f"{base}.{suffix}",
        "rule_type": "standard",
        "pathway": "deemed_to_comply",
        "lifecycle_status": "approved",
        "operator": "gte",
        "value_json": {"value": value, "base_rule_key": base},
        "unit": "m",
        "condition_json": {"density_codes": list(codes)},
        "metadata_json": {"wp6": True},
        "applicable_r_codes": list(codes) or None,
        "quote": "the minimum street setback shall be 4.0 m",
        "source_version_id": "sv-1",
    }
    row.update(over)
    return row


def _candidate(cid="cand-1", rule_key="primary_street_setback", status="pending_review",
               codes=("R40",), value=4.0, confidence=0.6, **over):
    row = {
        "id": cid,
        "rule_key": rule_key,
        "review_status": status,
        "operator": "gte",
        "value_json": {"value": value},
        "unit": "m",
        "condition_json": {"density_codes": list(codes), "dwelling_type": "any", "condition": ""},
        "quote": "street setback must be at least 4.0 m",
        "confidence": confidence,
        "source_version_id": "sv-1",
    }
    row.update(over)
    return row


def _clause(cid="cl-1", path="5.1.2", disposition="rule_bearing",
            text="The minimum street setback must be 4.5 m for lots coded R30"):
    return {"id": cid, "clause_path": path, "disposition": disposition, "text": text}


# ---------------------------------------------------------------------------
# Matrix: density codes + base-key resolution
# ---------------------------------------------------------------------------


def test_matrix_density_codes_are_r5_to_r80_sorted():
    codes = matrix.matrix_density_codes()
    assert codes == [
        "R5", "R10", "R12.5", "R15", "R17.5", "R20", "R25",
        "R30", "R35", "R40", "R50", "R60", "R80",
    ]
    # extended codes from VALID_R_CODES are out of matrix scope
    assert "R100" not in codes and "R-AC" not in codes and "R160" not in codes


def test_every_tier1_check_key_has_a_base_rule_key_mapping():
    for check in matrix.TIER1_CHECKS:
        assert check.key in matrix.CHECK_TO_BASE_RULE_KEYS


def test_base_rule_key_prefers_value_json_then_rule_key_prefix():
    assert matrix.base_rule_key(_rule()) == "primary_street_setback"
    row = _rule(value_json={"value": 4.0})  # no base_rule_key recorded
    assert matrix.base_rule_key(row) == "primary_street_setback"
    assert matrix.base_rule_key({"rule_key": "site_cover.max"}) == "site_cover"


# ---------------------------------------------------------------------------
# Matrix: cell resolution
# ---------------------------------------------------------------------------


def test_resolve_cell_fills_on_explicit_code_match():
    rows = [_rule()]
    res = matrix.resolve_cell("setback_front", "R30", rows)
    assert res["status"] == "filled"
    assert res["rule_id"] == "rule-1"
    assert res["cell"] == "rule-1 | gte 4.0 m"


def test_resolve_cell_missing_when_code_not_covered():
    rows = [_rule(codes=("R30",))]
    res = matrix.resolve_cell("setback_front", "R40", rows)
    assert res["status"] == "missing"
    assert res["cell"] == "MISSING"


def test_resolve_cell_global_rule_covers_every_code():
    rows = [_rule(rule_id="global-1", applicable_r_codes=None)]
    for code in matrix.matrix_density_codes():
        assert matrix.resolve_cell("setback_front", code, rows)["status"] == "filled"


def test_resolve_cell_prefers_explicit_match_over_global():
    rows = [
        _rule(rule_id="global-1", applicable_r_codes=None),
        _rule(rule_id="explicit-1", codes=("R30",)),
    ]
    assert matrix.resolve_cell("setback_front", "R30", rows)["rule_id"] == "explicit-1"
    assert matrix.resolve_cell("setback_front", "R40", rows)["rule_id"] == "global-1"


def test_resolve_cell_ignores_unapproved_rules():
    rows = [_rule(lifecycle_status="pending_review")]
    assert matrix.resolve_cell("setback_front", "R30", rows)["status"] == "missing"


def test_resolve_cell_explicit_non_applicability_yields_cited_na():
    rows = [
        _rule(
            rule_id="na-1",
            codes=("R80",),
            value_json={
                "base_rule_key": "primary_street_setback",
                "not_applicable": True,
                "na_reason": "R-Codes Table 1 sets no primary street setback at R80",
            },
        )
    ]
    res = matrix.resolve_cell("setback_front", "R80", rows)
    assert res["status"] == "n/a"
    assert res["cell"] == "n/a (R-Codes Table 1 sets no primary street setback at R80)"


def test_resolve_cell_unmapped_check_key_is_missing_with_reason():
    res = matrix.resolve_cell("height_overall", "R30", [_rule()])
    assert res["status"] == "missing"
    assert "no base-rule-key mapping" in res["reason"]


def test_resolve_cell_secondary_side_accepts_either_base_key():
    rows = [_rule(base="secondary_street_setback", codes=("R30",))]
    assert matrix.resolve_cell("setback_side_secondary", "R30", rows)["status"] == "filled"
    rows = [_rule(base="side_setback", codes=("R30",))]
    assert matrix.resolve_cell("setback_side_secondary", "R30", rows)["status"] == "filled"


# ---------------------------------------------------------------------------
# Matrix: gap classification / nearest candidates
# ---------------------------------------------------------------------------


def test_nearest_candidates_orders_validators_passed_first():
    cands = [
        _candidate(cid="pending", status="pending_review", value=4.0),
        _candidate(cid="passed", status="validators_passed", value=4.5),
        _candidate(cid="global", status="validators_passed", codes=(), value=5.0),
        _candidate(cid="failed", status="validator_failed", value=6.0),
    ]
    out = matrix.nearest_candidates("setback_front", "R40", cands)
    assert [c["candidate_id"] for c in out] == ["passed", "global", "pending"]
    assert out[0]["review_status"] == "validators_passed"


def test_nearest_candidates_filters_wrong_key_and_wrong_code():
    cands = [
        _candidate(cid="wrong-key", rule_key="site_cover"),
        _candidate(cid="wrong-code", codes=("R20",)),
        _candidate(cid="right", codes=("R40",)),
    ]
    out = matrix.nearest_candidates("setback_front", "R40", cands)
    assert [c["candidate_id"] for c in out] == ["right"]


def test_nearest_candidates_dedupes_ensemble_pass_duplicates():
    cands = [
        _candidate(cid="pass1", status="validators_passed", value=4.0),
        _candidate(cid="pass2", status="validators_passed", value=4.0),
        _candidate(cid="pass3", status="validators_passed", value=4.0),
    ]
    out = matrix.nearest_candidates("setback_front", "R40", cands)
    assert len(out) == 1


def test_build_matrix_counts_defects_and_lists_candidates(tmp_path):
    rules = [
        _rule(rule_id="sc-global", base="site_cover", codes=(), applicable_r_codes=None,
              operator="lte", unit="%", value=60.0),
        _rule(rule_id="fs-r30", base="primary_street_setback", codes=("R30",)),
    ]
    cands = [_candidate(cid="fill-me", status="validators_passed", codes=("R40",))]
    result = matrix.build_matrix(rules, cands)

    n_codes = len(result["codes"])
    n_checks = len(result["checks"])
    assert result["summary"]["cells"] == n_codes * n_checks
    # site_cover row fully filled by the global rule + one explicit setback cell
    assert result["summary"]["filled"] == n_codes + 1
    assert result["summary"]["missing"] == n_codes * n_checks - n_codes - 1
    assert len(result["defects"]) == result["summary"]["missing"]
    assert "site_cover" not in result["summary"]["missing_by_check"]

    gap = next(d for d in result["defects"]
               if d["check_key"] == "setback_front" and d["r_code"] == "R40")
    assert gap["nearest_candidates"][0]["candidate_id"] == "fill-me"
    assert gap["base_rule_keys"] == ["primary_street_setback"]

    # CSV writer: header + one row per Tier-1 check, MISSING where unresolved
    csv_path = tmp_path / "rule_matrix.csv"
    matrix.write_matrix_csv(result, str(csv_path))
    with open(csv_path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["check_key", *result["codes"]]
    assert len(rows) == 1 + n_checks
    by_check = {r[0]: r[1:] for r in rows[1:]}
    assert all(cell.startswith("sc-global | lte 60.0 %") for cell in by_check["site_cover"])
    assert "MISSING" in by_check["setback_rear"]


# ---------------------------------------------------------------------------
# Per-doc gates: orphan sweep
# ---------------------------------------------------------------------------


def test_orphan_sweep_passes_when_numbers_claimed():
    clauses = [_clause()]
    quotes = ["The minimum street setback must be 4.5 m for lots coded R30"]
    sweep = gates.orphan_number_sweep(clauses, quotes)
    assert sweep["clauses_with_orphans"] == 0
    assert sweep["tier1_numeric_tokens"] == sweep["claimed"] == 2  # 4.5 and 30


def test_orphan_sweep_flags_unclaimed_numbers():
    sweep = gates.orphan_number_sweep([_clause()], [])
    assert sweep["clauses_with_orphans"] == 1
    assert sweep["detail"][0]["orphan_numbers"] == ["30", "4.5"]


def test_orphan_sweep_ignores_years_zero_and_non_tier1_clauses():
    clauses = [
        _clause(cid="cl-y", text="The street setback policy was gazetted in 2021 with 0 changes"),
        _clause(cid="cl-nt", text="Lodgement fees are 150 dollars"),  # no Tier-1 topic
    ]
    sweep = gates.orphan_number_sweep(clauses, [])
    assert sweep["tier1_numeric_tokens"] == 0
    assert sweep["clauses_with_orphans"] == 0


# ---------------------------------------------------------------------------
# Per-doc gates: gate evaluation
# ---------------------------------------------------------------------------


def _green_doc_inputs():
    clauses = [
        _clause(),
        _clause(cid="cl-2", path="intro", disposition="informational", text="Background only."),
    ]
    quotes = ["The minimum street setback must be 4.5 m for lots coded R30"]
    return clauses, quotes


def test_evaluate_doc_all_criteria_green():
    clauses, quotes = _green_doc_inputs()
    verdict = gates.evaluate_doc(clauses, quotes, 0, set())
    assert verdict["pass"] is True
    assert verdict["failing_criteria"] == []
    assert all(verdict["criteria"][k]["pass"] for k in gates.GATE_CRITERIA)


def test_evaluate_doc_fails_on_manual_review_disposition():
    clauses, quotes = _green_doc_inputs()
    clauses.append(_clause(cid="cl-3", disposition="manual_review", text="???"))
    verdict = gates.evaluate_doc(clauses, quotes, 0, set())
    assert verdict["pass"] is False
    assert verdict["failing_criteria"] == ["clause_dispositions"]
    assert verdict["criteria"]["clause_dispositions"]["undispositioned"] == 1


def test_evaluate_doc_fails_on_orphan_numbers():
    clauses, _ = _green_doc_inputs()
    verdict = gates.evaluate_doc(clauses, [], 0, set())
    assert "orphan_numbers" in verdict["failing_criteria"]


def test_evaluate_doc_exception_clause_unresolved_then_resolved():
    clauses, quotes = _green_doc_inputs()
    clauses.append(_clause(
        cid="cl-exc", path="5.1.3",
        text="Notwithstanding the street setback requirement, walls may be 1.5 m",
    ))
    quotes = quotes + ["walls may be 1.5 m"]
    unresolved = gates.evaluate_doc(clauses, quotes, 0, set())
    assert unresolved["failing_criteria"] == ["exception_language"]
    assert unresolved["criteria"]["exception_language"]["unresolved_paths"] == ["5.1.3"]
    resolved = gates.evaluate_doc(clauses, quotes, 0, {"cl-exc"})
    assert resolved["pass"] is True


def test_evaluate_doc_fails_when_pending_review_not_drained():
    clauses, quotes = _green_doc_inputs()
    verdict = gates.evaluate_doc(clauses, quotes, 7, set())
    assert verdict["failing_criteria"] == ["pending_review_drained"]
    assert verdict["criteria"]["pending_review_drained"]["pending_review"] == 7


def test_evaluate_doc_with_zero_clauses_fails_dispositions():
    verdict = gates.evaluate_doc([], [], 0, set())
    assert verdict["failing_criteria"] == ["clause_dispositions"]
    assert "structure pass has not run" in verdict["criteria"]["clause_dispositions"]["note"]


def test_summarize_counts_failures_per_criterion():
    clauses, quotes = _green_doc_inputs()
    docs = [
        gates.evaluate_doc(clauses, quotes, 0, set()),       # pass
        gates.evaluate_doc(clauses, quotes, 3, set()),       # pending_review fail
        gates.evaluate_doc([], [], 5, set()),                # dispositions + pending fail
    ]
    summary = gates.summarize(docs)
    assert summary["docs_evaluated"] == 3
    assert summary["docs_passing"] == 1
    assert summary["docs_failing"] == 2
    assert summary["failing_by_criterion"]["pending_review_drained"] == 2
    assert summary["failing_by_criterion"]["clause_dispositions"] == 1
    assert summary["failing_by_criterion"]["orphan_numbers"] == 0

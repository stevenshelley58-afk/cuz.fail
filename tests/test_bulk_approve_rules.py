from __future__ import annotations

from scripts.bulk_approve_rules import _candidate_id, validate_candidate


def _candidate(**overrides):
    candidate = {
        "source_version_id": "10000000-0000-0000-0000-000000000001",
        "clause_id": "20000000-0000-0000-0000-000000000001",
        "rule_key": "front_setback_min_m",
        "quote": "A dwelling must have a minimum 4 m front setback.",
        "value_json": {"value": 4.0},
        "unit": "m",
    }
    candidate.update(overrides)
    return candidate


def test_bulk_candidate_runs_every_universal_validator() -> None:
    candidate = _candidate()
    results, failures = validate_candidate(
        candidate,
        "A dwelling must have a minimum 4 m front setback.",
        "rule_bearing",
    )

    assert failures == []
    assert results
    assert all(result["pass"] for result in results.values())


def test_synthetic_report_quote_cannot_be_promoted() -> None:
    candidate = _candidate(
        quote="Table 2b: wall height 10.0, wall length 10 — 5.0 m",
        value_json={"value": 5.0},
    )
    results, failures = validate_candidate(
        candidate,
        "Boundary setbacks for walls with major openings must comply with Table 2b.",
        "rule_bearing",
    )

    assert not results["quote_anchor"]["pass"]
    assert any(failure.startswith("VALIDATOR-quote_anchor:") for failure in failures)


def test_candidate_identity_is_stable_for_idempotent_retries() -> None:
    candidate = _candidate()

    assert _candidate_id(candidate) == _candidate_id(dict(candidate))

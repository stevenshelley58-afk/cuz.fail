"""WP-I — Beeliar end-to-end canary gate.

The fixture evals/seeds/beeliar_canary.json pins the acceptance contract for the
open-vocab rebuild. The structural/consistency invariants are always enforced.
The end-to-end count gates (>=25 categories, >=10 pass/fail, citations) are
enforced once a real verification run has been recorded into the fixture
(`status == "verified"`); until then they are skipped honestly rather than
asserting invented numbers.

Recording flow (run phase): resolve the Beeliar address on prod, synth facts,
run the compliance engine, then write the real counts + per-check results into
the fixture's `recorded` block and set `status` to `verified`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from draftcheck.checks.registry import ALL_CHECKS, CHECK_BY_KEY

_FIXTURE = Path(__file__).resolve().parent.parent / "evals" / "seeds" / "beeliar_canary.json"


def _load() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def test_canary_fixture_is_well_formed() -> None:
    data = _load()
    assert data["address"]
    exp = data["expected"]
    # The contract itself must encode the WP-I gate thresholds.
    assert exp["min_categories_evaluated"] >= 25
    assert exp["min_pass_or_fail"] >= 10
    assert exp["min_synth_property_facts"] >= 6
    assert exp["every_result_has_citation"] is True
    assert data["status"] in {"pending_verification_run", "verified"}


def _recorded_or_skip() -> dict:
    data = _load()
    if data.get("status") != "verified" or not data.get("recorded"):
        pytest.skip(
            "Beeliar verification run not yet recorded into beeliar_canary.json "
            "(status != 'verified'). Run the prod verification, record results, "
            "then this gate enforces the counts."
        )
    return data


def test_recorded_checks_exist_in_registry() -> None:
    data = _load()
    recorded = data.get("recorded")
    if not recorded:
        pytest.skip("no recorded run yet")
    # Every evaluated check_key must be a real registry check (no drift).
    for result in recorded.get("results", []):
        assert result["check_key"] in CHECK_BY_KEY, result["check_key"]


def test_beeliar_meets_acceptance_contract() -> None:
    data = _recorded_or_skip()
    exp = data["expected"]
    rec = data["recorded"]

    # Registry must actually carry enough categories to support the gate.
    assert len(ALL_CHECKS) >= exp["min_categories_evaluated"], (
        f"registry has {len(ALL_CHECKS)} checks, gate needs "
        f">= {exp['min_categories_evaluated']}"
    )

    assert rec["categories_evaluated"] >= exp["min_categories_evaluated"]
    assert rec["pass_or_fail"] >= exp["min_pass_or_fail"]
    assert rec["synth_property_facts"] >= exp["min_synth_property_facts"]

    if exp.get("council_scope"):
        assert rec.get("council_scope") == exp["council_scope"]
    if exp.get("r_code"):
        assert rec.get("r_code") == exp["r_code"]

    if exp.get("every_result_has_citation"):
        missing = [
            r["check_key"]
            for r in rec.get("results", [])
            if r.get("status") in {"likely_pass", "likely_fail"}
            and not r.get("citation")
        ]
        assert not missing, f"pass/fail results missing citation: {missing}"

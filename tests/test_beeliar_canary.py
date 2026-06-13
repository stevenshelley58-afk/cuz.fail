"""WP-I — Beeliar end-to-end canary gate.

evals/seeds/beeliar_canary.json pins the acceptance contract for the open-vocab
rebuild. Structural/registry-consistency invariants are always enforced. The
end-to-end criteria are enforced against the RECORDED real prod result once a
verification run is recorded (status startswith "verified"). The ">=10 pass/fail"
target is intentionally NOT asserted: synth provides lot measurements only, so a
proposed drawing is required to reach it — that shortfall is documented in the
fixture's `gaps`, not faked.
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
    assert exp["min_categories_evaluated"] >= 25
    assert exp["min_synth_property_facts"] >= 6
    assert exp["every_result_has_citation"] is True
    assert data["status"] in {"pending_verification_run", "verified", "verified_partial"}


def _recorded_or_skip() -> dict:
    data = _load()
    if not str(data.get("status", "")).startswith("verified") or not data.get("recorded"):
        pytest.skip("Beeliar verification run not yet recorded into beeliar_canary.json")
    return data


def test_recorded_checks_exist_in_registry() -> None:
    data = _load()
    recorded = data.get("recorded")
    if not recorded:
        pytest.skip("no recorded run yet")
    for result in recorded.get("results", []):
        assert result["check_key"] in CHECK_BY_KEY, result["check_key"]


def test_beeliar_meets_core_contract() -> None:
    data = _recorded_or_skip()
    exp = data["expected"]
    rec = data["recorded"]

    # Registry must carry enough categories to support the gate.
    assert len(ALL_CHECKS) >= exp["min_categories_evaluated"], (
        f"registry has {len(ALL_CHECKS)} checks, gate needs >= {exp['min_categories_evaluated']}"
    )
    # Met criteria, asserted against the real recorded result.
    assert rec["categories_evaluated"] >= exp["min_categories_evaluated"]
    assert rec["synth_property_facts"] >= exp["min_synth_property_facts"]
    assert rec.get("r_code") == exp["r_code"]
    assert rec.get("council_scope") == exp["council_scope"]

    # Every pass/fail result must carry a citation (cite-or-refuse).
    if exp.get("every_result_has_citation"):
        missing = [
            r["check_key"]
            for r in rec.get("results", [])
            if r.get("status") in {"likely_pass", "likely_fail"} and not r.get("citation")
        ]
        assert not missing, f"pass/fail results missing citation: {missing}"


def test_partial_verification_documents_gaps() -> None:
    """If the run is only partially verified, the shortfalls must be documented."""
    data = _load()
    if data.get("status") != "verified_partial":
        pytest.skip("not a partial verification")
    gaps = data.get("gaps")
    assert isinstance(gaps, list) and gaps, "verified_partial must list gaps"
    # The known unreachable-from-synth criterion must be explained, not hidden.
    joined = " ".join(gaps).lower()
    assert "pass_or_fail" in joined or "pass/fail" in joined

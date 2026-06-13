"""WP-F — guard the generated check registry and the derivation logic.

The registry is now DERIVED from rule clusters (registry_generated.py).  These
tests pin the structural contract so accidental drift (a hand-edit, a bad
generator change, a duplicate key) is caught in CI, without pinning a brittle
exact checksum that would churn on every legitimate re-derivation.
"""
from __future__ import annotations

import re

import pytest

from draftcheck.checks.registry import (
    ALL_CHECKS,
    CHECK_BY_KEY,
    REGISTRY_SOURCE,
    SEED_ALL_CHECKS,
    SEED_CANONICAL_RULE_KEYS,
    CheckCategory,
    CheckDefinition,
    CheckTier,
)

_SNAKE = re.compile(r"[a-z][a-z0-9_]{2,160}$")


def test_registry_loads_from_generated_module() -> None:
    # The public surface must come from the generated module, not the fallback.
    assert REGISTRY_SOURCE == "generated"


def test_all_checks_are_structurally_valid() -> None:
    for c in ALL_CHECKS:
        assert isinstance(c, CheckDefinition)
        assert _SNAKE.match(c.key), f"check key not snake_case: {c.key!r}"
        assert isinstance(c.tier, CheckTier)
        assert isinstance(c.category, CheckCategory)
        assert isinstance(c.fact_keys, tuple) and len(c.fact_keys) >= 1, c.key
        assert all(isinstance(fk, str) and fk for fk in c.fact_keys), c.key
        assert isinstance(c.rule_key_pattern, str) and c.rule_key_pattern, c.key
        assert isinstance(c.unit, str)
        assert isinstance(c.description, str) and c.description, c.key


def test_no_duplicate_check_keys() -> None:
    keys = [c.key for c in ALL_CHECKS]
    dupes = {k for k in keys if keys.count(k) > 1}
    assert not dupes, f"duplicate check keys: {sorted(dupes)}"
    assert len(CHECK_BY_KEY) == len(ALL_CHECKS)


def test_seed_checks_are_always_present() -> None:
    # Derivation must never drop the hand-written seed checks.
    seed_keys = {c.key for c in SEED_ALL_CHECKS}
    present = set(CHECK_BY_KEY)
    assert seed_keys <= present, f"seed checks missing: {seed_keys - present}"


def test_registry_has_at_least_seed_count() -> None:
    # Floor: never fewer than the 11 seed checks.  After a real derivation run
    # this grows well past 25 (the WP-I gate); the canary fixture pins that.
    assert len(ALL_CHECKS) >= len(SEED_ALL_CHECKS) >= 11


# --- generator derivation logic (offline, no DB) -------------------------------

def _stat(key: str, n: int, unit: str = "m") -> dict:
    return {"canonical_rule_key": key, "n_approved": n, "unit": unit,
            "sample_quote": f"quote for {key}", "source": "sv-test"}


def test_derive_skips_seed_covered_and_respects_min_rules() -> None:
    derive_checks = pytest.importorskip(
        "scripts.wp6_register_checks_from_clusters"
    ).derive_checks
    stats = [
        _stat("primary_street_setback", 113),  # seed-covered -> skip
        _stat("building_height", 100),          # seed-covered -> skip
        _stat("outdoor_living_area", 59, "m2"), # derive
        _stat("driveway_width", 12),            # derive
        _stat("rarely_seen_key", 3),            # below min_rules=5 -> skip
        _stat("Bad Key!", 40),                  # not snake_case -> skip
        _stat("monetary_penalty", 40),          # denylisted noise -> skip
        _stat("none", 99),                      # denylisted noise -> skip
    ]
    derived = derive_checks(stats, min_rules=5)
    keys = {d["key"] for d in derived}
    assert keys == {"outdoor_living_area", "driveway_width"}
    # tier promotion: outdoor_living_area (59 >= 20) -> TIER1; driveway (12) -> TIER2
    by = {d["key"]: d for d in derived}
    assert by["outdoor_living_area"]["tier"] == "TIER1"
    assert by["driveway_width"]["tier"] == "TIER2"
    # determinism: sorted by key
    assert [d["key"] for d in derived] == sorted(d["key"] for d in derived)


def test_seed_canonical_map_covers_every_seed_check() -> None:
    seed_keys = {c.key for c in SEED_ALL_CHECKS}
    assert set(SEED_CANONICAL_RULE_KEYS) == seed_keys

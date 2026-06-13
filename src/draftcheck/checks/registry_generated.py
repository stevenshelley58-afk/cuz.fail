"""GENERATED check registry — DO NOT EDIT BY HAND.

Produced by ``scripts/wp6_register_checks_from_clusters.py`` from the open-vocab
rule clusters (canonical_rule_key) with >= MIN_RULES_FOR_CHECK approved rules.
See ``docs/OPEN_VOCAB_REBUILD_PLAN.md`` WP-F.

This checked-in version is the SEED baseline (the hand-written checks only).
Running the derivation script against the clustered rule DB regenerates this
file with the seed checks PLUS the cluster-derived checks, then it is committed
and deployed.  ``registry.py`` imports ``TIER1_CHECKS`` / ``TIER2_CHECKS`` from
here and falls back to the seed if this module is unavailable.
"""
from __future__ import annotations

from draftcheck.checks.registry import (
    SEED_TIER1_CHECKS,
    SEED_TIER2_CHECKS,
    CheckDefinition,
)

# regenerated_from: seed-only baseline (no derivation has been run yet)
GENERATED_FROM = "seed_baseline"

TIER1_CHECKS: list[CheckDefinition] = list(SEED_TIER1_CHECKS)
TIER2_CHECKS: list[CheckDefinition] = list(SEED_TIER2_CHECKS)

ALL_CHECKS: list[CheckDefinition] = TIER1_CHECKS + TIER2_CHECKS
CHECK_BY_KEY: dict[str, CheckDefinition] = {c.key: c for c in ALL_CHECKS}

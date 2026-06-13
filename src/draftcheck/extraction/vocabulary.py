"""Vocabulary hints for the extraction / validation pipeline.

Under the open-vocab rule pipeline (operator decision 2026-06-14), ``RULE_KEY_HINTS``
is a SOFT hint set used only for telemetry / confidence weighting via
``is_hinted_key()``. It is NOT a closed/allowed-list gate: the extractor may propose
any snake_case ``rule_key`` and validators accept new keys on their structural merits,
so nothing is dropped merely for being absent from this set. See
``docs/OPEN_VOCAB_REBUILD_PLAN.md`` for the canonical architecture.

``OPERATORS``, ``NORMATIVE_WORDS``, and ``RULE_TYPES`` below remain canonical
enumerations for their respective fields.
"""

RULE_KEY_HINTS = frozenset({
    # Original Tier-1 R-Codes Vol 1 design elements (2026-06-10).
    "site_cover",
    "primary_street_setback",
    "secondary_street_setback",
    "side_setback",
    "rear_setback",
    "open_space",
    "garage_dominance",
    "garage_width",
    "boundary_wall_length",
    "building_height",
    "site_area",
    "outdoor_living_area",
    "soft_landscaping",
    "building_storeys",
    # 2026-06-13 expansion (history). These keys were added back when the original
    # 14-key vocab was still a hard gate; they showed up in WP6 Sonnet pilots as
    # "no_rules=true" or rule_key validator failures. Under the open-vocab pipeline
    # (2026-06-14) the gate is gone and these are now just additional hints, but the
    # keys are retained as known-good signals. CheckDefinitions are derived post-hoc
    # from clusters (see docs/OPEN_VOCAB_REBUILD_PLAN.md), not bounded by this set.
    "lot_width",
    "lot_depth",
    "minimum_frontage",
    "wall_height",
    "ground_floor_height",
    "ceiling_height",
    "plot_ratio",
    "fence_height_front",
    "fence_height_side",
    "retaining_wall_height",
    "parking_bays_per_dwelling",
    "visitor_parking_per_dwelling",
    "car_bay_width",
    "driveway_width",
    "private_open_space",
    "communal_open_space",
    # 2026-06-13 second expansion (history). Coverage of parking detail per dwelling
    # type, bicycle parking, signage, balconies, building separation, eave/awning,
    # dwelling area minimums, and ancillary dwelling rules - all common WA
    # residential planning rule shapes found in Cockburn LPPs and Liveable
    # Neighbourhoods. Added when the then-30-key vocab was still a hard gate; under
    # the open-vocab pipeline (2026-06-14) they are soft hints like the rest.
    "parking_bays_per_single_house",
    "parking_bays_per_grouped_dwelling",
    "parking_bays_per_multiple_dwelling",
    "bicycle_parking_per_dwelling",
    "balcony_area",
    "balcony_depth",
    "building_separation",
    "eave_width",
    "awning_depth",
    "dwelling_area_minimum",
    "dwelling_area_average",
    "ancillary_dwelling_area",
    "ancillary_dwelling_height",
    "crossover_width",
    "footpath_setback",
    "sign_height_max",
    "sign_area_max",
    "lot_orientation_angle",
    "noise_attenuation_distance",
    "building_envelope_height",
})


def is_hinted_key(key: str) -> bool:
    """Return True when key matches one of the soft rule_key hints."""
    normalized = (key or "").strip().lower().replace("-", "_")
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized in RULE_KEY_HINTS


OPERATORS = frozenset({"lte", "gte", "eq", "lt", "gt", "range", "pct_lte", "pct_gte"})

NORMATIVE_WORDS = frozenset({
    "must",
    "shall",
    "required",
    "requirement",
    "maximum",
    "minimum",
    "not exceed",
    "not less than",
    "at least",
    "no more than",
})

RULE_TYPES = frozenset({"standard", "exception", "deemed_to_comply", "design_principle"})

"""Vocabulary hints for the extraction / validation pipeline."""

RULE_KEY_HINTS = frozenset({
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
    "minimum_frontage",
    "outdoor_living_area",
    "private_open_space",
    "soft_landscaping",
    "building_storeys",
    "wall_height",
    "ceiling_height",
    "ground_floor_height",
    "parking_bays_per_dwelling",
    "visitor_parking_per_dwelling",
    "driveway_width",
    "retaining_wall_height",
    "fence_height_front",
    "fence_height_side",
    "plot_ratio",
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

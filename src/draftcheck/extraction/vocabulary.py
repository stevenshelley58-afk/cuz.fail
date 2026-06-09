"""Closed vocabularies for the extraction / validation pipeline."""

RULE_KEYS = frozenset({
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
})

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

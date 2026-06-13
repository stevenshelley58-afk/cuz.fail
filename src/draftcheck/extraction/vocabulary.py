"""Closed vocabularies for the extraction / validation pipeline."""

RULE_KEYS = frozenset({
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
    # 2026-06-13 expansion. Covers the most common WA-residential rule shapes
    # that fell outside the original 14-key vocab and showed up in WP6 Sonnet
    # pilots as "no_rules=true" or rule_key validator failures. The compliance
    # engine's check registry has not been expanded yet, so rules with these
    # keys serve as reference data + retrieval hits until matching CheckDefinitions
    # land in src/draftcheck/checks/registry.py.
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
    # 2026-06-13 second expansion. Coverage of parking detail per dwelling type,
    # bicycle parking, signage, balconies, building separation, eave/awning,
    # dwelling area minimums, and ancillary dwelling rules - all common WA
    # residential planning rule shapes found in Cockburn LPPs and Liveable
    # Neighbourhoods that fell outside the first 30-key vocab.
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

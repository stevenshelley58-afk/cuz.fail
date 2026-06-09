"""Tier-1 check key definitions for DraftCheck WA.

TIER1_CHECK_KEYS   — ordered list of check keys the engine evaluates
CHECK_FACT_MAP     — maps each check_key to one or more PropertyFact.fact_type
                     keys to look up (first match wins)
CHECK_DISPLAY      — human-readable labels for UI / report rendering

All values here are metadata only — thresholds and operators live
exclusively in the rules table (lifecycle_status='approved').
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Ordered list of Tier-1 check keys
# ---------------------------------------------------------------------------

TIER1_CHECK_KEYS: list[str] = [
    "setback_front",
    "setback_rear",
    "setback_side",
    "site_cover",
    "open_space",
    "garage_width_dominance",
    "boundary_wall_length",
]

# ---------------------------------------------------------------------------
# Fact key mappings
# Each entry lists the PropertyFact.fact_type values to try in order.
# The first fact_type present for the project is used as the measurement.
# ---------------------------------------------------------------------------

CHECK_FACT_MAP: dict[str, list[str]] = {
    "setback_front": [
        "proposed_setback_front_m",
        "setback_front_m",
    ],
    "setback_rear": [
        "proposed_setback_rear_m",
        "setback_rear_m",
    ],
    "setback_side": [
        "proposed_setback_side_m",
        "setback_side_m",
    ],
    "site_cover": [
        "proposed_site_cover_pct",
        "site_coverage_pct",
        "site_cover_pct",
    ],
    "open_space": [
        "proposed_open_space_pct",
        "open_space_pct",
    ],
    "garage_width_dominance": [
        "proposed_garage_width_dominance_pct",
        "garage_width_dominance_pct",
        "garage_width_pct",
    ],
    "boundary_wall_length": [
        "proposed_boundary_wall_length_m",
        "boundary_wall_length_m",
    ],
}

# ---------------------------------------------------------------------------
# Human-readable display names
# ---------------------------------------------------------------------------

CHECK_DISPLAY: dict[str, str] = {
    "setback_front":           "Front Setback",
    "setback_rear":            "Rear Setback",
    "setback_side":            "Side Setback",
    "site_cover":              "Site Coverage",
    "open_space":              "Open Space",
    "garage_width_dominance":  "Garage Width Dominance",
    "boundary_wall_length":    "Boundary Wall Length",
}

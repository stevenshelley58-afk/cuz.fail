"""Heuristics for deriving CheckDefinitions from open-vocab rule clusters.

Small, hand-editable tables consumed by
``scripts/wp6_register_checks_from_clusters.py`` (WP-F).  When the derivation
guesses a wrong category or fact_keys for a cluster, fix it HERE and re-run the
generator — never hand-edit ``registry_generated.py``.

Nothing in here touches the database; it is pure string heuristics so it can be
unit-tested without a DB connection.
"""
from __future__ import annotations

from draftcheck.checks.registry import CheckCategory

# ---------------------------------------------------------------------------
# Category assignment.  Ordered: the FIRST matching token wins, so list the
# most specific tokens before the generic ones.
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: list[tuple[str, CheckCategory]] = [
    ("street_setback", CheckCategory.SETBACK),
    ("setback", CheckCategory.SETBACK),
    ("garage", CheckCategory.GARAGE),
    ("driveway", CheckCategory.DRIVEWAY),
    ("crossover", CheckCategory.DRIVEWAY),
    ("visitor_parking", CheckCategory.PARKING),
    ("bicycle_parking", CheckCategory.PARKING),
    ("car_bay", CheckCategory.PARKING),
    ("parking", CheckCategory.PARKING),
    ("bays", CheckCategory.PARKING),
    ("fence", CheckCategory.FENCE),
    ("retaining_wall", CheckCategory.WALL),
    ("boundary_wall", CheckCategory.BOUNDARY_WALL),
    ("storeys", CheckCategory.STOREYS),
    ("storey", CheckCategory.STOREYS),
    ("wall_height", CheckCategory.WALL),
    ("eave", CheckCategory.HEIGHT),
    ("ceiling_height", CheckCategory.HEIGHT),
    ("floor_height", CheckCategory.HEIGHT),
    ("building_height", CheckCategory.HEIGHT),
    ("building_envelope", CheckCategory.HEIGHT),
    ("height", CheckCategory.HEIGHT),
    ("site_cover", CheckCategory.SITE_COVER),
    ("plot_ratio", CheckCategory.SITE),
    ("site_area", CheckCategory.SITE),
    ("soft_landscaping", CheckCategory.LANDSCAPE),
    ("landscap", CheckCategory.LANDSCAPE),
    ("outdoor_living", CheckCategory.LANDSCAPE),
    ("communal_open", CheckCategory.OPEN_SPACE),
    ("private_open", CheckCategory.OPEN_SPACE),
    ("open_space", CheckCategory.OPEN_SPACE),
    ("balcony", CheckCategory.LANDSCAPE),
    ("frontage", CheckCategory.LOT),
    ("lot_width", CheckCategory.LOT),
    ("lot_depth", CheckCategory.LOT),
    ("lot_orientation", CheckCategory.LOT),
    ("dwelling_area", CheckCategory.LOT),
    ("separation", CheckCategory.SETBACK),
    ("noise", CheckCategory.OTHER),
    ("sign", CheckCategory.OTHER),
]


def category_for(canonical_key: str) -> CheckCategory:
    key = (canonical_key or "").lower()
    for token, category in CATEGORY_KEYWORDS:
        if token in key:
            return category
    return CheckCategory.OTHER


# ---------------------------------------------------------------------------
# Unit -> dimensional category.  Drives the default fact_keys shape.
# ---------------------------------------------------------------------------
_UNIT_CATEGORY: dict[str, str] = {
    "m": "length",
    "mm": "length",
    "cm": "length",
    "km": "length",
    "m2": "area",
    "ha": "area",
    "%": "percent",
    "storeys": "count_storeys",
    "ratio": "ratio",
    "count": "count",
    "degrees": "angle",
    "db": "noise",
    "lx": "light",
}


def unit_category_for(unit: str | None) -> str:
    if not unit:
        return "count"
    return _UNIT_CATEGORY.get(unit.strip().lower(), "count")


# ---------------------------------------------------------------------------
# fact_keys derivation.
#
# Most checks compare a PROPOSED design value to a threshold; for those the
# fact_key is ``proposed_<canonical>_<suffix>``.  A handful of checks are
# LOT-INTRINSIC — the measured value is a property fact the spatial layer can
# synthesise (lot area, frontage, depth) — so those evaluate to pass/fail from
# auto-synth'd facts with no drawing upload.  Those are listed explicitly.
# ---------------------------------------------------------------------------
# Substring-ordered so it is robust to the clustering normaliser's canonical
# forms (e.g. "minimum_frontage" normalises to "min_frontage").  First match
# wins; list the most specific substrings first.
#
# IMPORTANT: every fact_key listed for a check must be a valid MEASURED value
# for that check (alternate names are fine).  Never list a denominator/context
# fact (lot_area_m2, site_area_m2) here — the engine uses the first PRESENT
# fact_key as the measured value, so a stray denominator gets compared to the
# threshold and produces a nonsense pass/fail.  Lot-INTRINSIC checks (site_area,
# frontage, lot width/depth) legitimately measure a property fact.
# NB: lot-AREA concepts (site_area, min_lot_area, average_lot_size) are
# deliberately NOT auto-evaluated against the property's lot_area_m2.  The
# open-vocab "site_area" cluster mixes minimum-lot-size rules (R-Codes table)
# with the wrong extracted operator (eq/lt where the table means "at least"),
# so comparing a real lot area to the selected threshold can yield a misleading
# likely_fail.  Until those operators are curated (see WP-E follow-up), these
# stay needs_more_info rather than emit a confusing headline fail.  Frontage and
# lot width/depth are unambiguous "minimum" checks and DO evaluate from synth.
FACT_KEY_OVERRIDES: list[tuple[str, tuple[str, ...]]] = [
    ("plot_ratio", ("proposed_plot_ratio",)),
    ("frontage", ("lot_width_m", "frontage_width_m")),
    ("lot_width", ("lot_width_m",)),
    ("lot_depth", ("lot_depth_m",)),
]


def fact_keys_for(canonical_key: str, unit: str | None) -> tuple[str, ...]:
    key = (canonical_key or "").lower()
    for token, fact_keys in FACT_KEY_OVERRIDES:
        if token in key:
            return fact_keys
    cat = unit_category_for(unit)
    base = canonical_key
    if cat == "length":
        return (f"proposed_{base}_m",)
    if cat == "area":
        return (f"proposed_{base}_m2",)
    if cat == "percent":
        return (f"proposed_{base}_pct",)
    if cat == "count_storeys":
        return (f"proposed_{base}_storeys",)
    if cat == "ratio":
        return (f"proposed_{base}_ratio",)
    if cat == "angle":
        return (f"proposed_{base}_degrees",)
    return (f"proposed_{base}_count",)


def check_name_for(canonical_key: str) -> str:
    """Human display name: title-cased canonical key with underscores spaced."""
    return (canonical_key or "").replace("_", " ").strip().title()

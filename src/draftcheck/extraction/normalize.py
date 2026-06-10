"""Unit normalization utilities for the extraction pipeline."""

from __future__ import annotations

import re

_UNIT_ALIASES: dict[str, tuple[str, float]] = {
    "mm": ("m", 0.001),
    "millimetre": ("m", 0.001),
    "millimeter": ("m", 0.001),
    "cm": ("m", 0.01),
    "centimetre": ("m", 0.01),
    "centimeter": ("m", 0.01),
    "metre": ("m", 1.0),
    "meter": ("m", 1.0),
    "m": ("m", 1.0),
    "m2": ("m2", 1.0),
    "m²": ("m2", 1.0),
    "sqm": ("m2", 1.0),
    "square metres": ("m2", 1.0),
    "square meters": ("m2", 1.0),
    "storey": ("storeys", 1.0),
    "storeys": ("storeys", 1.0),
    "stories": ("storeys", 1.0),
    "%": ("%", 1.0),
    "percent": ("%", 1.0),
    "per cent": ("%", 1.0),
}


def normalize_unit(value: float | int, unit: str | None) -> tuple[float, str | None]:
    """Return (normalized_value, canonical_unit).

    Converts mm → m, cm → m.  % stays %.  Unknown units are returned as-is
    with the original value.
    """
    if unit is None:
        return float(value), None

    key = unit.strip().lower()
    if key in _UNIT_ALIASES:
        canonical, factor = _UNIT_ALIASES[key]
        return float(value) * factor, canonical

    # Unknown unit — pass through unchanged.
    return float(value), unit


def whitespace_normalize(text: str) -> str:
    """Collapse runs of whitespace to a single space and strip leading/trailing."""
    return re.sub(r"\s+", " ", text).strip()

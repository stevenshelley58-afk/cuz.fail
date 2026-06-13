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
    "km": ("m", 1000.0),
    "metre": ("m", 1.0),
    "meter": ("m", 1.0),
    "m": ("m", 1.0),
    "m2": ("m2", 1.0),
    "m²": ("m2", 1.0),
    "mÂ²": ("m2", 1.0),
    "sq m": ("m2", 1.0),
    "sq.m": ("m2", 1.0),
    "sqm": ("m2", 1.0),
    "metres squared": ("m2", 1.0),
    "square metres": ("m2", 1.0),
    "square meters": ("m2", 1.0),
    "ha": ("m2", 10000.0),
    "storey": ("storeys", 1.0),
    "storeys": ("storeys", 1.0),
    "stories": ("storeys", 1.0),
    "%": ("%", 1.0),
    "percent": ("%", 1.0),
    "per cent": ("%", 1.0),
    "\u00b0": ("degrees", 1.0),
    "degree": ("degrees", 1.0),
    "degrees": ("degrees", 1.0),
    "db": ("dB", 1.0),
    "decibels": ("dB", 1.0),
    "lx": ("lx", 1.0),
    "lux": ("lx", 1.0),
    "count": ("count", 1.0),
    "bay": ("count", 1.0),
    "bays": ("count", 1.0),
    "dwelling": ("count", 1.0),
    "dwellings": ("count", 1.0),
    "ratio": ("ratio", 1.0),
    "per dwelling": ("ratio", 1.0),
}

_UNIT_CATEGORIES: dict[str | None, str] = {
    None: "count",
    "m": "length",
    "m2": "area",
    "%": "percent",
    "storeys": "count_storeys",
    "count": "count",
    "ratio": "ratio",
    "degrees": "angle",
    "dB": "decibel",
    "lx": "illuminance",
}


def normalize_unit(value: float | int, unit: str | None) -> tuple[float, str | None]:
    """Return (normalized_value, canonical_unit)."""
    if unit is None:
        return float(value), None

    key = unit.strip().lower()
    if key in _UNIT_ALIASES:
        canonical, factor = _UNIT_ALIASES[key]
        return float(value) * factor, canonical

    return float(value), unit


def unit_category_for_unit(unit: str | None) -> str | None:
    """Return the broad sanity-check category for a canonical unit."""
    return _UNIT_CATEGORIES.get(unit)


def whitespace_normalize(text: str) -> str:
    """Collapse runs of whitespace to a single space and strip leading/trailing."""
    return re.sub(r"\s+", " ", text).strip()

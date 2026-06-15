"""Local-government naming helpers for spatial source scoping."""

from __future__ import annotations


def _title_lga_fragment(value: str) -> str:
    return " ".join(part.capitalize() for part in value.casefold().split())


def canonical_local_government_name(value: str | None) -> str:
    """Return the user-facing LGA name used by source and rule scoping."""
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    marker = "(bbox extent)"
    if cleaned.casefold().endswith(marker):
        cleaned = cleaned[: -len(marker)].strip()
    suffix_prefixes = (
        (", CITY OF", "City of"),
        (", SHIRE OF", "Shire of"),
        (", TOWN OF", "Town of"),
    )
    upper = cleaned.upper()
    for suffix, prefix in suffix_prefixes:
        if upper.endswith(suffix):
            place = cleaned[: -len(suffix)].strip(" ,")
            return f"{prefix} {_title_lga_fragment(place)}"
    prefix_labels = (
        ("CITY OF ", "City of"),
        ("SHIRE OF ", "Shire of"),
        ("TOWN OF ", "Town of"),
    )
    for prefix, label in prefix_labels:
        if upper.startswith(prefix):
            return f"{label} {_title_lga_fragment(cleaned[len(prefix):])}"
    return cleaned if cleaned != cleaned.upper() else _title_lga_fragment(cleaned)

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentFactCandidate:
    fact_type: str
    label: str
    value_text: str
    numeric_value: float | None
    unit: str | None
    source_text: str
    confidence: float
    measurement_key: str | None = None


NUMBER_PATTERN = r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
AREA_UNIT_PATTERN = r"(m2|sqm|square\s+metres?)"
LENGTH_UNIT_PATTERN = r"(m|metres?|mm|cm)"
DRAWING_UNIT_PATTERN = r"(mm|cm|m|in|ft|drawing\s+units)"

MEASUREMENT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "site_area_m2",
        "site area",
        rf"\bsite\s+area\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{AREA_UNIT_PATTERN}\b",
    ),
    (
        "building_footprint_m2",
        "building footprint",
        rf"\b(?:building\s+footprint|site\s+cover(?:age)?)\b[^\d]{{0,30}}"
        rf"{NUMBER_PATTERN}\s*{AREA_UNIT_PATTERN}\b",
    ),
    (
        "open_space_m2",
        "open space",
        rf"\bopen\s+space\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{AREA_UNIT_PATTERN}\b",
    ),
    (
        "front_setback_m",
        "front setback",
        rf"\bfront\s+setback\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
    (
        "side_setback_m",
        "side setback",
        rf"\bside\s+setback\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
    (
        "rear_setback_m",
        "rear setback",
        rf"\brear\s+setback\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
    (
        "garage_width_m",
        "garage width",
        rf"\bgarage\s+width\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
    (
        "frontage_width_m",
        "frontage width",
        rf"\bfrontage\s+width\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
    (
        "outdoor_living_area_m2",
        "outdoor living area",
        rf"\boutdoor\s+living\s+area\b[^\d]{{0,30}}"
        rf"{NUMBER_PATTERN}\s*{AREA_UNIT_PATTERN}\b",
    ),
    (
        "outdoor_living_min_dimension_m",
        "outdoor living minimum dimension",
        rf"\boutdoor\s+living\b[^\n]{{0,80}}\b(?:min(?:imum)?\s+dimension|dimension)"
        rf"\b[^\d]{{0,30}}{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
    (
        "retaining_fill_height_m",
        "retaining/fill height",
        rf"\b(?:retaining|fill)\b[^\n]{{0,60}}\bheight\b[^\d]{{0,30}}"
        rf"{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
    (
        "boundary_wall_length_m",
        "boundary wall length",
        rf"\bboundary\s+wall\b[^\n]{{0,60}}\blength\b[^\d]{{0,30}}"
        rf"{NUMBER_PATTERN}\s*{LENGTH_UNIT_PATTERN}\b",
    ),
)


def extract_fact_candidates(text: str) -> list[DocumentFactCandidate]:
    normalized_text = _normalize_text_units(text)
    facts: list[DocumentFactCandidate] = []
    facts.extend(_extract_named_measurements(normalized_text))
    facts.extend(_extract_generic_numbers(normalized_text))
    facts.extend(_extract_drawing_dimensions(normalized_text))
    facts.extend(_extract_drawing_markers(normalized_text))
    return _dedupe(facts)


def _extract_named_measurements(text: str) -> list[DocumentFactCandidate]:
    facts: list[DocumentFactCandidate] = []
    for key, label, pattern in MEASUREMENT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            numeric = _parse_number(match.group(1))
            unit = _normalise_unit(match.group(2))
            value = _normalise_measurement(numeric, unit)
            normalised_unit = "m2" if unit in {"m2", "sqm"} else "m"
            facts.append(
                DocumentFactCandidate(
                    fact_type="measurement",
                    label=label,
                    value_text=f"{value:g}{normalised_unit}",
                    numeric_value=value,
                    unit=normalised_unit,
                    source_text=_context(text, match.start(), match.end()),
                    confidence=0.82,
                    measurement_key=key,
                )
            )
    return facts


def _extract_generic_numbers(text: str) -> list[DocumentFactCandidate]:
    facts: list[DocumentFactCandidate] = []
    pattern = (
        rf"(?<![A-Z])\b{NUMBER_PATTERN}\s*"
        r"(mm|cm|m|m2|sqm|square\s+metres?|%)\b"
    )
    for match in re.finditer(pattern, text, re.IGNORECASE):
        unit = _normalise_unit(match.group(2))
        numeric = _parse_number(match.group(1))
        facts.append(
            DocumentFactCandidate(
                fact_type="numeric_value",
                label="numeric value",
                value_text=f"{numeric:g}{unit}",
                numeric_value=numeric,
                unit=unit,
                source_text=_context(text, match.start(), match.end()),
                confidence=0.45,
            )
        )
    return facts


def _extract_drawing_dimensions(text: str) -> list[DocumentFactCandidate]:
    facts: list[DocumentFactCandidate] = []
    pattern = (
        rf"\b(line\s+length|polyline\s+length|dimension\s+measurement)\b"
        rf"[^\d]{{0,80}}{NUMBER_PATTERN}\s*{DRAWING_UNIT_PATTERN}\b"
    )
    for match in re.finditer(pattern, text, re.IGNORECASE):
        unit = _normalise_unit(match.group(3))
        numeric = _parse_number(match.group(2))
        value = _normalise_measurement(numeric, unit)
        normalised_unit = "m" if unit in {"mm", "cm"} else unit
        facts.append(
            DocumentFactCandidate(
                fact_type="drawing_dimension",
                label=match.group(1).lower(),
                value_text=f"{value:g}{normalised_unit}",
                numeric_value=value,
                unit=normalised_unit,
                source_text=_context(text, match.start(), match.end()),
                confidence=0.65 if unit == "drawing_units" else 0.72,
            )
        )
    return facts


def _extract_drawing_markers(text: str) -> list[DocumentFactCandidate]:
    facts: list[DocumentFactCandidate] = []
    for match in re.finditer(r"\bA\d{2,3}\b", text, re.IGNORECASE):
        facts.append(
            DocumentFactCandidate(
                fact_type="drawing_reference",
                label="drawing sheet reference",
                value_text=match.group(0).upper(),
                numeric_value=None,
                unit=None,
                source_text=_context(text, match.start(), match.end()),
                confidence=0.75,
            )
        )
    for match in re.finditer(r"\b1\s*:\s*(\d{2,5})\b", text, re.IGNORECASE):
        facts.append(
            DocumentFactCandidate(
                fact_type="scale",
                label="drawing scale",
                value_text=f"1:{match.group(1)}",
                numeric_value=1.0,
                unit="boolean",
                source_text=_context(text, match.start(), match.end()),
                confidence=0.8,
                measurement_key="scale_present",
            )
        )
    for marker, key in [
        (r"\bnorth\b|\bNORTH\s+POINT\b", "north_point_present"),
        (r"\btitle\s+block\b", "title_block_present"),
        (r"\b(?:rev|revision)\b", "revision_present"),
        (r"\bdimensions?\b|\b\d+(?:\.\d+)?\s*(?:mm|m)\b", "dimensions_present"),
    ]:
        if re.search(marker, text, re.IGNORECASE):
            facts.append(
                DocumentFactCandidate(
                    fact_type="drawing_marker",
                    label=key.replace("_", " "),
                    value_text="present",
                    numeric_value=1.0,
                    unit="boolean",
                    source_text=key.replace("_", " "),
                    confidence=0.6,
                    measurement_key=key,
                )
            )
    level_pattern = rf"\b(FFL|NGL|RL)\s*[:=]?\s*{NUMBER_PATTERN}\b"
    for match in re.finditer(level_pattern, text, re.IGNORECASE):
        facts.append(
            DocumentFactCandidate(
                fact_type="level",
                label=match.group(1).upper(),
                value_text=match.group(2),
                numeric_value=_parse_number(match.group(2)),
                unit="m",
                source_text=_context(text, match.start(), match.end()),
                confidence=0.7,
            )
        )
    return facts


def _normalize_text_units(text: str) -> str:
    return (
        text.replace("m\u00c2\u00b2", "m2")
        .replace("m\u00b2", "m2")
        .replace("M\u00b2", "m2")
        .replace("m^2", "m2")
        .replace("M^2", "m2")
    )


def _normalise_unit(unit: str) -> str:
    value = (
        unit.lower()
        .replace("\u00c2\u00b2", "2")
        .replace("\u00b2", "2")
        .replace("^2", "2")
    )
    value = " ".join(value.split())
    if value in {"metre", "metres"}:
        return "m"
    if value in {"sqm", "square metre", "square metres"}:
        return "m2"
    if value == "drawing units":
        return "drawing_units"
    return value


def _normalise_measurement(value: float, unit: str) -> float:
    if unit == "mm":
        return round(value / 1000, 4)
    if unit == "cm":
        return round(value / 100, 4)
    return value


def _parse_number(value: str) -> float:
    return float(value.replace(",", ""))


def _context(text: str, start: int, end: int, radius: int = 80) -> str:
    return " ".join(text[max(0, start - radius) : min(len(text), end + radius)].split())


def _dedupe(facts: list[DocumentFactCandidate]) -> list[DocumentFactCandidate]:
    seen: set[tuple[str, str, str, str | None]] = set()
    unique: list[DocumentFactCandidate] = []
    for fact in facts:
        key = (fact.fact_type, fact.label, fact.value_text, fact.measurement_key)
        if key in seen:
            continue
        seen.add(key)
        unique.append(fact)
    return unique

"""DocumentFactService — regex-based numeric fact extraction from document text.

Pattern-matching only; no LLM in this pass.  All outputs are advisory with
status 'pending_review' until a human or downstream service promotes them.
"""

from __future__ import annotations

import re
from uuid import UUID, uuid4

from draftcheck.db.models import DocumentFact

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Each entry: (fact_key_template, pattern, unit, confidence)
# fact_key_template may contain '{location}' which is filled from the match
# or a fixed keyword position heuristic.

_SETBACK_PATTERNS: list[tuple[str, str, float]] = [
    # "front setback: 4.5 m" / "rear setback 3 metres"
    (
        r"(?P<loc>front|rear|side|secondary|primary|northern?|southern?|eastern?|western?)"
        r"[\s\-]*setback[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.80,
    ),
    # "setback to front boundary: 4.5m"
    (
        r"setback\s+to\s+(?P<loc>front|rear|side|secondary|primary|northern?|southern?|eastern?|western?)"
        r"[^0-9]{0,40}?(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.75,
    ),
    # bare "X.X m" or "X metres" near the word setback (lower confidence)
    (
        r"setback[^0-9]{0,60}?(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.60,
    ),
]

_AREA_PATTERNS: list[tuple[str, str, float]] = [
    (
        r"(?:gross\s+)?floor\s+area[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "sqm",
        0.82,
    ),
    (
        r"(?:lot|site|land)\s+area[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "sqm",
        0.82,
    ),
    (
        r"(?:building\s+)?footprint[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "sqm",
        0.78,
    ),
    (
        r"open\s+space[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "sqm",
        0.75,
    ),
    # generic "NNN m²" or "NNN sqm" — lowest confidence
    (
        r"(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "sqm",
        0.50,
    ),
]

_PERCENTAGE_PATTERNS: list[tuple[str, str, float]] = [
    (
        r"site\s+coverage[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:%|per\s*cent)\b",
        "%",
        0.82,
    ),
    (
        r"open\s+space\s+(?:ratio|percentage)[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:%|per\s*cent)\b",
        "%",
        0.78,
    ),
    (
        r"(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:%|per\s*cent)\b",
        "%",
        0.50,
    ),
]

# ---------------------------------------------------------------------------
# Fact key helpers
# ---------------------------------------------------------------------------

_LOCATION_NORMALISE: dict[str, str] = {
    "front": "front",
    "primary": "front",
    "rear": "rear",
    "side": "side",
    "secondary": "side",
    "north": "north",
    "northern": "north",
    "south": "south",
    "southern": "south",
    "east": "east",
    "eastern": "east",
    "west": "west",
    "western": "west",
}


def _setback_key(location_raw: str | None) -> str:
    if not location_raw:
        return "proposed_setback_m"
    loc = _LOCATION_NORMALISE.get(location_raw.lower().rstrip("n"), location_raw.lower())
    return f"proposed_setback_{loc}_m"


def _area_key(pattern_index: int) -> str:
    keys = [
        "proposed_floor_area_sqm",
        "proposed_site_area_sqm",
        "proposed_footprint_sqm",
        "proposed_open_space_sqm",
        "proposed_area_sqm",
    ]
    return keys[min(pattern_index, len(keys) - 1)]


def _percentage_key(pattern_index: int) -> str:
    keys = [
        "proposed_site_coverage_pct",
        "proposed_open_space_ratio_pct",
        "proposed_percentage",
    ]
    return keys[min(pattern_index, len(keys) - 1)]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DocumentFactService:
    """Extract numeric facts from plain text using regex patterns.

    All returned DocumentFact rows have review_status='pending_review'.
    No LLM is used in this pass.
    """

    PARSER_VERSION = "v0.1"

    def extract_facts_from_text(
        self,
        text: str,
        document_id: UUID,
        page_number: int,
        *,
        org_id: UUID | None = None,
        project_id: UUID | None = None,
        page_id: UUID | None = None,
    ) -> list[DocumentFact]:
        """Return a list of DocumentFact ORM instances (not yet persisted).

        Parameters
        ----------
        text:
            Plain text extracted from one document page.
        document_id:
            The UUID of the parent Document row.
        page_number:
            1-based page number for source attribution.
        org_id / project_id / page_id:
            Optional FK values; left NULL when not available.
        """
        facts: list[DocumentFact] = []
        seen: set[tuple[str, float]] = set()

        def _add(fact_key: str, numeric_value: float, unit: str, confidence: float, source_text: str) -> None:
            dedup_key = (fact_key, numeric_value)
            if dedup_key in seen:
                return
            seen.add(dedup_key)
            facts.append(
                DocumentFact(
                    id=uuid4(),
                    org_id=org_id,
                    project_id=project_id,
                    document_id=document_id,
                    page_id=page_id,
                    fact_kind="drawing_measurement",
                    check_key=fact_key,
                    value_json={
                        "numeric_value": numeric_value,
                        "unit": unit,
                        "fact_key": fact_key,
                        "source_text": source_text,
                        "page_number": page_number,
                    },
                    confidence=confidence,
                    evidence_ref_json={"page_number": page_number, "source_text": source_text},
                    promoted_to_measurement=False,
                    review_status="pending_review",
                    parser_name="draftcheck.regex_fact_extractor",
                    parser_version=self.PARSER_VERSION,
                    metadata_json={
                        "measurement_compliance_ready": False,
                        "measurement_readiness_reason": "human promotion required before compliance use",
                    },
                )
            )

        # --- setbacks ---
        for pattern, unit, confidence in _SETBACK_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                location = match.groupdict().get("loc")
                val = float(match.group("val"))
                key = _setback_key(location)
                _add(key, val, unit, confidence, match.group(0))

        # --- areas ---
        for idx, (pattern, unit, confidence) in enumerate(_AREA_PATTERNS):
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                val = float(match.group("val"))
                key = _area_key(idx)
                _add(key, val, unit, confidence, match.group(0))

        # --- percentages ---
        for idx, (pattern, unit, confidence) in enumerate(_PERCENTAGE_PATTERNS):
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                val = float(match.group("val"))
                key = _percentage_key(idx)
                _add(key, val, unit, confidence, match.group(0))

        return facts


# Alias satisfying the import contract: MeasurementExtractor = DocumentFactService
MeasurementExtractor = DocumentFactService

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
        "m2",
        0.82,
    ),
    (
        r"(?:lot|site|land)\s+area[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "m2",
        0.82,
    ),
    (
        r"(?:building\s+)?footprint[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "m2",
        0.78,
    ),
    (
        r"open\s+space[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "m2",
        0.75,
    ),
    # generic "NNN m²" or "NNN sqm" — lowest confidence
    (
        r"(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m²|m2|sqm|sq\.?\s*m)\b",
        "m2",
        0.50,
    ),
]

_PERCENTAGE_PATTERNS: list[tuple[str, str, float]] = [
    (
        r"site\s+(?:cover|coverage)[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:%|\bper\s*cent\b)",
        "%",
        0.82,
    ),
    (
        r"open\s+space(?:\s+(?:minimum|ratio|percentage))?[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:%|\bper\s*cent\b)",
        "%",
        0.78,
    ),
    (
        r"garage\s+(?:dominance|width\s+dominance)[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:%|\bper\s*cent\b)",
        "%",
        0.76,
    ),
    (
        r"(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:%|\bper\s*cent\b)",
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
        "site_area_m2",
        "proposed_covered_area_m2",
        "proposed_open_space_m2",
        "proposed_area_sqm",
    ]
    return keys[min(pattern_index, len(keys) - 1)]


def _percentage_key(pattern_index: int) -> str:
    keys = [
        "proposed_site_cover_pct",
        "proposed_open_space_pct",
        "proposed_garage_width_dominance_pct",
        "proposed_percentage",
    ]
    return keys[min(pattern_index, len(keys) - 1)]


_LINEAR_MEASUREMENT_PATTERNS: list[tuple[str, str, str, float]] = [
    (
        "proposed_garage_width_m",
        r"garage\s+width[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.78,
    ),
    (
        "proposed_boundary_wall_length_m",
        r"boundary\s+wall\s+length[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "proposed_boundary_wall_height_m",
        r"boundary\s+wall\s+height[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "dwelling_facade_width_m",
        r"(?:dwelling\s+|street\s+)?facade\s+width[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "frontage_width_m",
        r"(?:frontage\s+width|lot\s+frontage|street\s+frontage)[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.78,
    ),
    (
        "lot_depth_m",
        r"(?:lot|site)\s+depth[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "driveway_width_m",
        r"driveway\s+width[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "retaining_wall_height_m",
        r"retaining\s+wall\s+height[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "front_fence_height_m",
        r"front\s+fence\s+height[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "side_fence_height_m",
        r"(?:side|secondary)\s+fence\s+height[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.76,
    ),
    (
        "proposed_height_overall_m",
        r"(?:overall\s+building\s+height|maximum\s+building\s+height|building\s+height)[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.68,
    ),
    (
        "proposed_wall_height_m",
        r"(?:external\s+)?wall\s+height[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.70,
    ),
    (
        "natural_ground_level_m",
        r"(?:natural\s+ground\s+level|ngl)[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)?\b",
        "m",
        0.64,
    ),
    (
        "ceiling_height_m",
        r"ceiling\s+height[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.74,
    ),
    (
        "ground_floor_height_m",
        r"ground\s+floor\s+height[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\s*(?:m|metres?|meters?)\b",
        "m",
        0.72,
    ),
]

_DIRECT_NUMERIC_PATTERNS: list[tuple[str, str, str, float]] = [
    (
        "parking_bays_per_dwelling",
        r"parking\s+bays?\s+per\s+dwelling[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\b",
        "count",
        0.76,
    ),
    (
        "visitor_parking_per_dwelling",
        r"visitor\s+parking(?:\s+bays?)?\s+per\s+dwelling[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\b",
        "count",
        0.74,
    ),
    (
        "parking_bay_count",
        r"parking\s+bays?[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\b",
        "count",
        0.70,
    ),
    (
        "plot_ratio",
        r"plot\s+ratio[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\b",
        "ratio",
        0.74,
    ),
    (
        "building_storeys",
        r"(?:building\s+)?storeys?[:\s]*(?P<val>[0-9]+(?:\.[0-9]+)?)\b",
        "storeys",
        0.72,
    ),
]

_TITLE_BLOCK_PATTERNS: list[tuple[str, str, float]] = [
    (
        "drawing_number",
        r"(?:drawing|sheet)\s*(?:no\.?|number|#)[:\s]*(?P<val>[A-Z0-9][A-Z0-9._/-]{1,40})\b",
        0.74,
    ),
    (
        "drawing_revision",
        r"\b(?:revision|rev\.?)[:\s]*(?P<val>[A-Z0-9][A-Z0-9._/-]{0,20})\b",
        0.72,
    ),
    (
        "drawing_title",
        r"(?:drawing|sheet)\s*title[:\s]*(?P<val>[^\n\r]{3,120})",
        0.70,
    ),
    (
        "drawing_scale",
        r"\bscale[:\s]*(?P<val>(?:1\s*:\s*\d{1,5})|(?:NTS)|(?:as\s+shown))\b",
        0.68,
    ),
    (
        "r_code",
        r"\b(?:r-code|rcode|residential\s+density\s+code)[:\s]*(?P<val>R[0-9]{2,3}(?:/[0-9]{2,3})?)\b",
        0.66,
    ),
    (
        "zoning",
        r"\b(?:zone|zoning)[:\s]*(?P<val>[A-Za-z][A-Za-z0-9 /-]{2,80})",
        0.62,
    ),
    (
        "lot_number",
        r"\blot\s*(?:no\.?|number)[:\s]*(?P<val>[A-Z0-9][A-Z0-9._/-]{0,30})\b",
        0.60,
    ),
    (
        "street_address",
        r"\baddress[:\s]*(?P<val>[^\n\r]{5,120})",
        0.60,
    ),
]

_BOOLEAN_MARKER_PATTERNS: list[tuple[str, str, float]] = [
    ("title_block_present", r"(?:drawing|sheet)\s*(?:no\.?|number|#|title)", 0.70),
    ("revision_present", r"\b(?:revision|rev\.?)[:\s]*[A-Z0-9]", 0.70),
    ("scale_present", r"\bscale[:\s]*(?:1\s*:\s*\d{1,5}|NTS|as\s+shown)\b", 0.70),
    ("north_point_present", r"\b(?:north\s+point|north\s+arrow)\b", 0.65),
    ("dimensions_present", r"\b(?:dimensions?|dimensioned)\b", 0.55),
]


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
        seen_text: set[tuple[str, str]] = set()

        def _add(
            fact_key: str,
            numeric_value: float,
            unit: str,
            confidence: float,
            source_text: str,
            *,
            metadata_extra: dict[str, object] | None = None,
        ) -> None:
            dedup_key = (fact_key, numeric_value)
            if dedup_key in seen:
                return
            seen.add(dedup_key)
            metadata = {
                "measurement_compliance_ready": False,
                "measurement_readiness_reason": "human promotion required before compliance use",
            }
            if metadata_extra:
                metadata.update(metadata_extra)
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
                    metadata_json=metadata,
                )
            )

        def _add_text(fact_key: str, text_value: str, confidence: float, source_text: str) -> None:
            normalized_value = " ".join(text_value.strip().split())
            if not normalized_value:
                return
            dedup_key = (fact_key, normalized_value.casefold())
            if dedup_key in seen_text:
                return
            seen_text.add(dedup_key)
            facts.append(
                DocumentFact(
                    id=uuid4(),
                    org_id=org_id,
                    project_id=project_id,
                    document_id=document_id,
                    page_id=page_id,
                    fact_kind="drawing_title_block",
                    check_key=fact_key,
                    value_json={
                        "text_value": normalized_value,
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
                        "title_block_field": fact_key,
                        "measurement_compliance_ready": False,
                        "measurement_readiness_reason": "title-block text is project metadata, not a compliance measurement",
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

        # --- linear measurements used directly by Tier-1 checks ---
        for key, pattern, unit, confidence in _LINEAR_MEASUREMENT_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                val = float(match.group("val"))
                _add(key, val, unit, confidence, match.group(0))

        # --- direct numeric facts used by Cockburn rule families ---
        for key, pattern, unit, confidence in _DIRECT_NUMERIC_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                val = float(match.group("val"))
                _add(key, val, unit, confidence, match.group(0))

        # --- title-block metadata; useful context, not promoted measurements ---
        for key, pattern, confidence in _TITLE_BLOCK_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                _add_text(key, match.group("val"), confidence, match.group(0))

        # --- drawing QA markers; booleans remain review-gated facts ---
        for key, pattern, confidence in _BOOLEAN_MARKER_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                _add(key, 1.0, "bool", confidence, match.group(0))
                break

        self._add_derived_facts(facts, seen, document_id, page_number, org_id, project_id, page_id)

        return facts

    def _add_derived_facts(
        self,
        facts: list[DocumentFact],
        seen: set[tuple[str, float]],
        document_id: UUID,
        page_number: int,
        org_id: UUID | None,
        project_id: UUID | None,
        page_id: UUID | None,
    ) -> None:
        def _first(fact_key: str) -> float | None:
            for fact in facts:
                if fact.check_key != fact_key:
                    continue
                value_json = fact.value_json if isinstance(fact.value_json, dict) else {}
                raw = value_json.get("numeric_value")
                if raw is None:
                    raw = value_json.get("value")
                try:
                    return float(raw)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    return None
            return None

        def _derived(
            fact_key: str,
            value: float,
            unit: str,
            source_keys: tuple[str, ...],
            method: str,
        ) -> None:
            rounded = round(value, 4)
            dedup_key = (fact_key, rounded)
            if dedup_key in seen:
                return
            seen.add(dedup_key)
            source_text = f"derived:{method}"
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
                        "numeric_value": rounded,
                        "unit": unit,
                        "fact_key": fact_key,
                        "source_text": source_text,
                        "page_number": page_number,
                    },
                    confidence=0.62,
                    evidence_ref_json={"page_number": page_number, "source_text": source_text},
                    promoted_to_measurement=False,
                    review_status="pending_review",
                    parser_name="draftcheck.regex_fact_extractor",
                    parser_version=self.PARSER_VERSION,
                    metadata_json={
                        "measurement_compliance_ready": False,
                        "measurement_readiness_reason": "human review required before compliance use",
                        "derived_from_fact_keys": list(source_keys),
                        "calculation_method": method,
                    },
                )
            )

        site_area = _first("site_area_m2")
        covered_area = _first("proposed_covered_area_m2")
        open_space_area = _first("proposed_open_space_m2")
        garage_width = _first("proposed_garage_width_m")
        facade_width = _first("dwelling_facade_width_m")
        if _first("proposed_site_cover_pct") is None and site_area and site_area > 0 and covered_area is not None:
            _derived(
                "proposed_site_cover_pct",
                (covered_area / site_area) * 100,
                "%",
                ("proposed_covered_area_m2", "site_area_m2"),
                "covered_area_divided_by_site_area",
            )
        if _first("proposed_open_space_pct") is None and site_area and site_area > 0 and open_space_area is not None:
            _derived(
                "proposed_open_space_pct",
                (open_space_area / site_area) * 100,
                "%",
                ("proposed_open_space_m2", "site_area_m2"),
                "open_space_area_divided_by_site_area",
            )
        if (
            _first("proposed_garage_width_dominance_pct") is None
            and facade_width
            and facade_width > 0
            and garage_width is not None
        ):
            _derived(
                "proposed_garage_width_dominance_pct",
                (garage_width / facade_width) * 100,
                "%",
                ("proposed_garage_width_m", "dwelling_facade_width_m"),
                "garage_width_divided_by_facade_width",
            )


# Alias satisfying the import contract: MeasurementExtractor = DocumentFactService
MeasurementExtractor = DocumentFactService

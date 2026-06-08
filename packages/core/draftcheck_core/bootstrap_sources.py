from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.json_utils import hash_text, normalize_text, to_json
from draftcheck_core.models import (
    Clause,
    ClauseDisposition,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
)
from draftcheck_core.source_support import source_version_can_support_citable_retrieval
from draftcheck_shared.schemas import Citation


BOOTSTRAP_SOURCE_TITLE = "R-Codes Volume 1 bootstrap excerpt"
BOOTSTRAP_SOURCE_URL = "https://www.wa.gov.au/system/files/2026-04/r-codes-volume-1-10-april-2026.pdf"
BOOTSTRAP_STREET_SETBACK_TEXT = (
    "Table C: Minimum street setback 3.3 Street setbacks: Primary street R30 4m."
)
BOOTSTRAP_SITE_COVER_TEXT = "\n".join(
    [
        "C3.1.1 Development on each site does not exceed the maximum site cover percentages of Table 3.1a.",
        "Table 3.1a Maximum site cover requirements",
        "R30 maximum site cover 60%.",
        "R35 maximum site cover 60%.",
        "R40 maximum site cover 65%.",
        "R50 maximum site cover 65%.",
        "R60 maximum site cover 70%.",
        "R80 maximum site cover 70%.",
    ]
)
BOOTSTRAP_OPEN_SPACE_TEXT = "\n".join(
    [
        "Table B Primary controls for R30 single houses: minimum open space is 45% of the site.",
        "Table B Primary controls for R30 single houses: minimum outdoor living area is 24m2.",
    ]
)
BOOTSTRAP_OUTDOOR_LIVING_TEXT = "\n".join(
    [
        "C1.1 Outdoor living area is to be provided in accordance with Table B.",
        "C1.1 Outdoor living area has a minimum length and width dimension of 4m.",
        "Table B Primary controls for R30 single houses: minimum outdoor living area is 24m2.",
    ]
)
BOOTSTRAP_SOURCE_TEXT = "\n\n".join(
    [
        BOOTSTRAP_STREET_SETBACK_TEXT,
        BOOTSTRAP_SITE_COVER_TEXT,
        BOOTSTRAP_OPEN_SPACE_TEXT,
        BOOTSTRAP_OUTDOOR_LIVING_TEXT,
    ]
)
BOOTSTRAP_RETRIEVED_AT = datetime(2026, 6, 6)
BOOTSTRAP_SOURCE_DOCUMENT_ID = "src_bootstrap_rcodes_v1_excerpt"
BOOTSTRAP_SOURCE_VERSION_ID = "sv_bootstrap_rcodes_v1_20260410_excerpt"
BOOTSTRAP_LICENCE_REVIEW_ID = "slr_bootstrap_rcodes_v1_excerpt"
BOOTSTRAP_STREET_SETBACK_CLAUSE_ID = "cl_bootstrap_rcodes_v1_table_c_33"
BOOTSTRAP_STREET_SETBACK_DISPOSITION_ID = "cdisp_bootstrap_rcodes_v1_table_c_33"
BOOTSTRAP_STREET_SETBACK_RULE_ROW_ID = "rule_bootstrap_rcodes_v1_r30_primary_setback"
BOOTSTRAP_STREET_SETBACK_CHUNK_ID = "chk_bootstrap_rcodes_v1_table_c_33"
BOOTSTRAP_STREET_SETBACK_CITATION_ID = "cit_bootstrap_rcodes_v1_table_c_33"
BOOTSTRAP_SITE_COVER_CLAUSE_ID = "cl_bootstrap_rcodes_v1_c311_site_cover"
BOOTSTRAP_SITE_COVER_DISPOSITION_ID = "cdisp_bootstrap_rcodes_v1_c311_site_cover"
BOOTSTRAP_SITE_COVER_RULE_ROW_ID = "rule_bootstrap_rcodes_v1_r30_site_cover"
BOOTSTRAP_SITE_COVER_CHUNK_ID = "chk_bootstrap_rcodes_v1_c311_site_cover"
BOOTSTRAP_SITE_COVER_CITATION_ID = "cit_bootstrap_rcodes_v1_c311_site_cover"
BOOTSTRAP_OPEN_SPACE_CLAUSE_ID = "cl_bootstrap_rcodes_v1_table_b_open_space"
BOOTSTRAP_OPEN_SPACE_DISPOSITION_ID = "cdisp_bootstrap_rcodes_v1_table_b_open_space"
BOOTSTRAP_OPEN_SPACE_RULE_ROW_ID = "rule_bootstrap_rcodes_v1_r30_open_space"
BOOTSTRAP_OPEN_SPACE_CHUNK_ID = "chk_bootstrap_rcodes_v1_table_b_open_space"
BOOTSTRAP_OPEN_SPACE_CITATION_ID = "cit_bootstrap_rcodes_v1_table_b_open_space"
BOOTSTRAP_OUTDOOR_LIVING_CLAUSE_ID = "cl_bootstrap_rcodes_v1_c11_outdoor_living"
BOOTSTRAP_OUTDOOR_LIVING_DISPOSITION_ID = "cdisp_bootstrap_rcodes_v1_c11_outdoor_living"
BOOTSTRAP_OUTDOOR_LIVING_RULE_ROW_ID = "rule_bootstrap_rcodes_v1_r30_outdoor_living"
BOOTSTRAP_OUTDOOR_LIVING_CHUNK_ID = "chk_bootstrap_rcodes_v1_c11_outdoor_living"
BOOTSTRAP_OUTDOOR_LIVING_CITATION_ID = "cit_bootstrap_rcodes_v1_c11_outdoor_living"
BOOTSTRAP_SOLAR_GUIDANCE_VERSION_ID = "sv_bootstrap_solar_access_guidance"
BOOTSTRAP_NATURAL_VENTILATION_GUIDANCE_VERSION_ID = "sv_bootstrap_natural_ventilation_guidance"
BOOTSTRAP_BUSHFIRE_BAL_BASIC_GUIDANCE_VERSION_ID = "sv_bootstrap_bushfire_bal_basic_guidance"
BOOTSTRAP_SIDE_SETBACK_GUIDANCE_VERSION_ID = "sv_bootstrap_average_side_setback_guidance"
BOOTSTRAP_VOL2_A4_GUIDANCE_VERSION_ID = "sv_bootstrap_rcodes_vol2_a4_guidance"
BOOTSTRAP_VOL2_A5_GUIDANCE_VERSION_ID = "sv_bootstrap_rcodes_vol2_a5_guidance"


def ensure_demo_source_library(db: Session) -> dict[str, Any]:
    existing = db.get(SourceDocument, BOOTSTRAP_SOURCE_DOCUMENT_ID) or db.scalar(
        select(SourceDocument).where(SourceDocument.title == BOOTSTRAP_SOURCE_TITLE)
    )

    created = existing is None
    source = existing or SourceDocument(id=BOOTSTRAP_SOURCE_DOCUMENT_ID)
    source.title = BOOTSTRAP_SOURCE_TITLE
    source.jurisdiction = "WA"
    source.authority = "Department of Planning, Lands and Heritage"
    source.source_type = "r_code"
    source.canonical_url = BOOTSTRAP_SOURCE_URL
    source.licence_notes = (
        "Short public WA Government R-Codes excerpts used to verify source-cited retrieval bootstrap. "
        "Not a substitute for full source review."
    )
    source.access_type = "public"
    source.scrape_allowed = False
    source.is_active = True
    if created:
        db.add(source)
    db.flush()

    version = db.get(SourceVersion, BOOTSTRAP_SOURCE_VERSION_ID)
    version_created = version is None
    if version is None:
        version = SourceVersion(id=BOOTSTRAP_SOURCE_VERSION_ID)
        db.add(version)
    version.source_document_id = source.id
    version.version_label = "Residential Design Codes Volume 1 - 10 April 2026 short excerpts"
    version.effective_date = "2026-04-10"
    version.published_date = "2026-04-10"
    version.retrieved_at = BOOTSTRAP_RETRIEVED_AT
    version.content_sha256 = hash_text(BOOTSTRAP_SOURCE_TEXT)
    version.raw_text = BOOTSTRAP_SOURCE_TEXT
    version.parse_status = "ok"
    version.review_status = "accepted"
    version.reviewed_by = "system-bootstrap"
    version.reviewed_at = BOOTSTRAP_RETRIEVED_AT
    db.flush()

    licence = db.get(SourceLicenceReview, BOOTSTRAP_LICENCE_REVIEW_ID)
    if licence is None:
        licence = SourceLicenceReview(id=BOOTSTRAP_LICENCE_REVIEW_ID)
        db.add(licence)
    licence.source_document_id = source.id
    licence.source_version_id = version.id
    licence.licence_url = BOOTSTRAP_SOURCE_URL
    licence.allowed_use = True
    licence.allowed_storage = True
    licence.allowed_redistribution = False
    licence.allowed_ai_processing = True
    licence.reviewed_by = "system-bootstrap"
    licence.reviewed_at = BOOTSTRAP_RETRIEVED_AT
    licence.review_status = "approved"
    db.flush()

    created_rule_ids = []
    for spec in _bootstrap_rule_specs():
        if _ensure_bootstrap_rule(db, source, version, spec):
            created_rule_ids.append(spec["rule_row_id"])

    guidance_created = []
    for spec in _bootstrap_guidance_specs():
        if _ensure_bootstrap_guidance_source(db, spec):
            guidance_created.append(spec["source_version_id"])

    db.flush()
    return {
        "created": created,
        "updated": bool(created_rule_ids) or version_created or bool(guidance_created),
        "source_document_id": source.id,
        "source_version_id": version.id,
        "source_version_ids": [version.id, *[spec["source_version_id"] for spec in _bootstrap_guidance_specs()]],
        "rule_row_id": BOOTSTRAP_STREET_SETBACK_RULE_ROW_ID,
        "rule_row_ids": [spec["rule_row_id"] for spec in _bootstrap_rule_specs()],
    }


def _bootstrap_rule_specs() -> list[dict[str, Any]]:
    return [
        {
            "clause_id": BOOTSTRAP_STREET_SETBACK_CLAUSE_ID,
            "clause_ref": "Table C / 3.3",
            "heading": "Minimum street setback",
            "page_number": 111,
            "text": BOOTSTRAP_STREET_SETBACK_TEXT,
            "start_anchor": "Table C",
            "disposition_id": BOOTSTRAP_STREET_SETBACK_DISPOSITION_ID,
            "disposition_rationale": (
                "Short excerpt contains a deterministic primary street setback threshold for R30."
            ),
            "rule_row_id": BOOTSTRAP_STREET_SETBACK_RULE_ROW_ID,
            "rule_key": "front_setback",
            "operator": ">=",
            "value": {"min_value": 4.0, "density_code": "R30", "street_type": "primary"},
            "unit": "m",
            "condition_text": "R30 primary street",
            "chunk_id": BOOTSTRAP_STREET_SETBACK_CHUNK_ID,
            "citation_id": BOOTSTRAP_STREET_SETBACK_CITATION_ID,
        },
        {
            "clause_id": BOOTSTRAP_SITE_COVER_CLAUSE_ID,
            "clause_ref": "C3.1.1",
            "heading": "Site cover",
            "page_number": 89,
            "text": BOOTSTRAP_SITE_COVER_TEXT,
            "start_anchor": "C3.1.1",
            "disposition_id": BOOTSTRAP_SITE_COVER_DISPOSITION_ID,
            "disposition_rationale": (
                "Short excerpt contains a deterministic maximum site cover threshold for R30."
            ),
            "rule_row_id": BOOTSTRAP_SITE_COVER_RULE_ROW_ID,
            "rule_key": "site_cover",
            "operator": "<=",
            "value": {"max_percent": 60.0, "density_code": "R30"},
            "unit": "percent",
            "condition_text": "R30 site cover",
            "chunk_id": BOOTSTRAP_SITE_COVER_CHUNK_ID,
            "citation_id": BOOTSTRAP_SITE_COVER_CITATION_ID,
        },
        {
            "clause_id": BOOTSTRAP_OPEN_SPACE_CLAUSE_ID,
            "clause_ref": "Table B",
            "heading": "Primary controls - open space",
            "page_number": 43,
            "text": BOOTSTRAP_OPEN_SPACE_TEXT,
            "start_anchor": "Table B",
            "disposition_id": BOOTSTRAP_OPEN_SPACE_DISPOSITION_ID,
            "disposition_rationale": (
                "Short excerpt contains deterministic minimum open space and outdoor living thresholds for R30."
            ),
            "rule_row_id": BOOTSTRAP_OPEN_SPACE_RULE_ROW_ID,
            "rule_key": "open_space",
            "operator": ">=",
            "value": {"min_percent": 45.0, "density_code": "R30", "dwelling_type": "single_house"},
            "unit": "percent",
            "condition_text": "R30 single house open space",
            "chunk_id": BOOTSTRAP_OPEN_SPACE_CHUNK_ID,
            "citation_id": BOOTSTRAP_OPEN_SPACE_CITATION_ID,
        },
        {
            "clause_id": BOOTSTRAP_OUTDOOR_LIVING_CLAUSE_ID,
            "clause_ref": "C1.1 / Table B",
            "heading": "Outdoor living area",
            "page_number": 24,
            "text": BOOTSTRAP_OUTDOOR_LIVING_TEXT,
            "start_anchor": "C1.1",
            "disposition_id": BOOTSTRAP_OUTDOOR_LIVING_DISPOSITION_ID,
            "disposition_rationale": (
                "Short excerpt contains deterministic minimum area and dimension thresholds for R30 outdoor living."
            ),
            "rule_row_id": BOOTSTRAP_OUTDOOR_LIVING_RULE_ROW_ID,
            "rule_key": "outdoor_living_area",
            "operator": ">=",
            "value": {
                "density_code": "R30",
                "dwelling_type": "single_house",
                "values": [
                    {"key": "outdoor_living_area_m2", "min_value": 24.0, "unit": "m2"},
                    {"key": "outdoor_living_min_dimension_m", "min_value": 4.0, "unit": "m"},
                ],
            },
            "unit": "mixed",
            "condition_text": "R30 single house outdoor living area",
            "chunk_id": BOOTSTRAP_OUTDOOR_LIVING_CHUNK_ID,
            "citation_id": BOOTSTRAP_OUTDOOR_LIVING_CITATION_ID,
        },
    ]


def _ensure_bootstrap_rule(
    db: Session,
    source: SourceDocument,
    version: SourceVersion,
    spec: dict[str, Any],
) -> bool:
    created = False

    clause = db.get(Clause, spec["clause_id"])
    if clause is None:
        clause = Clause(id=spec["clause_id"])
        db.add(clause)
        created = True
    clause.source_version_id = version.id
    clause.clause_id = spec["clause_ref"]
    clause.heading = spec["heading"]
    clause.page_number = spec["page_number"]
    clause.text = spec["text"]
    clause.normalized_text = normalize_text(spec["text"])
    clause.start_anchor = spec["start_anchor"]
    clause.text_sha256 = hash_text(spec["text"])
    db.flush()

    disposition = db.get(ClauseDisposition, spec["disposition_id"])
    if disposition is None:
        disposition = ClauseDisposition(id=spec["disposition_id"])
        db.add(disposition)
        created = True
    disposition.clause_id = clause.id
    disposition.disposition = "rule_bearing"
    disposition.rationale = spec["disposition_rationale"]
    disposition.reviewer = "system-bootstrap"

    rule = db.get(RuleRow, spec["rule_row_id"])
    if rule is None:
        rule = RuleRow(id=spec["rule_row_id"])
        db.add(rule)
        created = True
    rule.rule_key = spec["rule_key"]
    rule.operator = spec["operator"]
    rule.value_json = to_json(spec["value"])
    rule.unit = spec["unit"]
    rule.condition_text = spec["condition_text"]
    rule.quote = spec["text"]
    rule.clause_id = clause.id
    rule.source_version_id = version.id
    rule.lifecycle_status = "approved"
    rule.approved_by = "system-bootstrap"
    rule.approved_at = BOOTSTRAP_RETRIEVED_AT

    chunk = db.get(SourceChunk, spec["chunk_id"])
    if chunk is None:
        chunk = SourceChunk(id=spec["chunk_id"])
        db.add(chunk)
        created = True
    chunk.source_version_id = version.id
    chunk.clause_id = clause.id
    chunk.heading = clause.heading
    chunk.page_number = clause.page_number
    chunk.text = spec["text"]
    chunk.token_count = len(spec["text"].split())
    db.flush()

    citation = Citation(
        source_document_id=source.id,
        source_title=source.title,
        source_version_id=version.id,
        version_label=version.version_label,
        effective_date=version.effective_date,
        retrieved_at=version.retrieved_at,
        clause_id=clause.clause_id,
        heading=clause.heading,
        page_number=clause.page_number,
        canonical_url=source.canonical_url,
        quote=spec["text"],
    )
    source_citation = db.get(SourceCitation, spec["citation_id"])
    if source_citation is None:
        source_citation = SourceCitation(id=spec["citation_id"])
        db.add(source_citation)
        created = True
    source_citation.source_chunk_id = chunk.id
    source_citation.source_version_id = version.id
    source_citation.clause_id = clause.id
    source_citation.citation_json = to_json(citation.model_dump(mode="json"))

    return created


def _bootstrap_guidance_specs() -> list[dict[str, Any]]:
    return [
        {
            "source_document_id": "src_bootstrap_solar_access_guidance",
            "source_version_id": BOOTSTRAP_SOLAR_GUIDANCE_VERSION_ID,
            "licence_review_id": "slr_bootstrap_solar_access_guidance",
            "clause_id": "cl_bootstrap_solar_access_guidance",
            "disposition_id": "cdisp_bootstrap_solar_access_guidance",
            "chunk_id": "chk_bootstrap_solar_access_guidance",
            "citation_id": "cit_bootstrap_solar_access_guidance",
            "title": "4.1 Solar and daylight access - Demonstrating solar access (PDF, 1.69MB)",
            "url": "https://www.wa.gov.au/system/files/2021-06/DWA-4-1-Solar-and-daylight-access-Demonstrating-solar-access.pdf",
            "version_label": "anchor-only",
            "clause_ref": "4",
            "heading": "Solar and daylight access",
            "page_number": 86,
            "text": (
                "Solar and daylight access. The following diagrams are an example of how solar access "
                "can be demonstrated."
            ),
        },
        {
            "source_document_id": "src_bootstrap_natural_ventilation_guidance",
            "source_version_id": BOOTSTRAP_NATURAL_VENTILATION_GUIDANCE_VERSION_ID,
            "licence_review_id": "slr_bootstrap_natural_ventilation_guidance",
            "clause_id": "cl_bootstrap_natural_ventilation_guidance",
            "disposition_id": "cdisp_bootstrap_natural_ventilation_guidance",
            "chunk_id": "chk_bootstrap_natural_ventilation_guidance",
            "citation_id": "cit_bootstrap_natural_ventilation_guidance",
            "title": "4.2 Natural ventilation - Optimal orientation for natural ventilation (PDF, 1013.78KB)",
            "url": "https://www.wa.gov.au/system/files/2021-06/DWA-4-2-Natural-ventilation-Optimal-orientation-for-natural-ventilation.pdf",
            "version_label": "anchor-only",
            "clause_ref": "4.2",
            "heading": "Natural ventilation",
            "page_number": 64,
            "text": (
                "Natural ventilation orientation guidance for single aspect apartments identifies 0 to 45 "
                "degrees of the prevailing cooling wind as fair orientation and 45 to 90 degrees as optimum "
                "orientation. Orientation for natural ventilation should consider location and site context."
            ),
        },
        {
            "source_document_id": "src_bootstrap_average_side_setback_guidance",
            "source_version_id": BOOTSTRAP_SIDE_SETBACK_GUIDANCE_VERSION_ID,
            "licence_review_id": "slr_bootstrap_average_side_setback_guidance",
            "clause_id": "cl_bootstrap_average_side_setback_guidance",
            "disposition_id": "cdisp_bootstrap_average_side_setback_guidance",
            "chunk_id": "chk_bootstrap_average_side_setback_guidance",
            "citation_id": "cit_bootstrap_average_side_setback_guidance",
            "title": "2.4 Side and rear setbacks - Calculating average side setbacks (PDF, 935.76KB)",
            "url": "https://www.wa.gov.au/system/files/2021-06/DWA-2-4-Side-and-rear-setbacks-Calculating-average-side-setbacks.pdf",
            "version_label": "anchor-only",
            "clause_ref": "3",
            "heading": "Calculating average side setbacks",
            "page_number": 3,
            "text": (
                "Average side setback. The diagram below provides a method of calculating the average side setback."
            ),
        },
        {
            "source_document_id": "src_bootstrap_bushfire_bal_basic_guidance",
            "source_version_id": BOOTSTRAP_BUSHFIRE_BAL_BASIC_GUIDANCE_VERSION_ID,
            "licence_review_id": "slr_bootstrap_bushfire_bal_basic_guidance",
            "clause_id": "cl_bootstrap_bushfire_bal_basic_guidance",
            "disposition_id": "cdisp_bootstrap_bushfire_bal_basic_guidance",
            "chunk_id": "chk_bootstrap_bushfire_bal_basic_guidance",
            "citation_id": "cit_bootstrap_bushfire_bal_basic_guidance",
            "title": "Bushfires: BAL Assessment (Basic) Report",
            "url": "https://www.wa.gov.au/system/files/2021-06/BF-BAL_Assessment_Report.pdf",
            "authority": "Western Australian Government",
            "source_type": "bushfire_guidance",
            "licence_notes": (
                "Short public WA Government bushfire planning form excerpt used to verify source-cited "
                "retrieval bootstrap. Not a substitute for AS 3959, BCA, BAL assessor, or building surveyor review."
            ),
            "version_label": "anchor-only",
            "clause_ref": "BAL Assessment (Basic) Report",
            "heading": "BAL Assessment (Basic) Report",
            "page_number": 1,
            "text": (
                "Planning in Bushfire Prone Areas BAL Assessment (Basic) Report requires the assessor to "
                "determine the Fire Danger Index, determine whether bushfire prone vegetation is within "
                "100 metres of the proposed building, determine the horizontal distance to the nearest "
                "bushfire prone vegetation, determine the slope of the land under that vegetation, and "
                "determine the Bushfire Attack Level (BAL) for the proposed building or development. The "
                "report says if the BAL is BAL-LOW the report may be used to support a relevant application; "
                "if the BAL is not BAL-LOW, this report should not be used. Supporting information can include "
                "site plans, photos, aerial photography, and other design documents and specifications as "
                "evidence that the site is not within 100 metres of bushfire prone vegetation."
            ),
        },
        {
            "source_document_id": "src_bootstrap_rcodes_vol2_a4_guidance",
            "source_version_id": BOOTSTRAP_VOL2_A4_GUIDANCE_VERSION_ID,
            "licence_review_id": "slr_bootstrap_rcodes_vol2_a4_guidance",
            "clause_id": "cl_bootstrap_rcodes_vol2_a4_guidance",
            "disposition_id": "cdisp_bootstrap_rcodes_vol2_a4_guidance",
            "chunk_id": "chk_bootstrap_rcodes_vol2_a4_guidance",
            "citation_id": "cit_bootstrap_rcodes_vol2_a4_guidance",
            "title": "R-Codes Vol.2 - A4 Design development guidance (DOCX, 17.54KB)",
            "url": "https://www.wa.gov.au/system/files/2021-06/SPP-7-3-Vol-2-A4-Design-development-guidance.docx",
            "version_label": "anchor-only",
            "clause_ref": "A4",
            "heading": "Design development guidance",
            "page_number": None,
            "text": (
                "It includes a list of basic information that should be provided by the applicant for design "
                "review prior to development application."
            ),
        },
        {
            "source_document_id": "src_bootstrap_rcodes_vol2_a5_guidance",
            "source_version_id": BOOTSTRAP_VOL2_A5_GUIDANCE_VERSION_ID,
            "licence_review_id": "slr_bootstrap_rcodes_vol2_a5_guidance",
            "clause_id": "cl_bootstrap_rcodes_vol2_a5_guidance",
            "disposition_id": "cdisp_bootstrap_rcodes_vol2_a5_guidance",
            "chunk_id": "chk_bootstrap_rcodes_vol2_a5_guidance",
            "citation_id": "cit_bootstrap_rcodes_vol2_a5_guidance",
            "title": "R-Codes Vol.2 - A5 Development application guidance (DOCX, 17.6KB)",
            "url": "https://www.wa.gov.au/system/files/2021-06/SPP-7-3-Vol-2-A5-Development-application-guidance.docx",
            "version_label": "anchor-only",
            "clause_ref": "A5",
            "heading": "Development application guidance",
            "page_number": None,
            "text": (
                "This guidance assists proponents in formulating the appropriate materials when submitting "
                "a development application."
            ),
        },
    ]


def _ensure_bootstrap_guidance_source(db: Session, spec: dict[str, Any]) -> bool:
    if _existing_citable_guidance_version(db, spec):
        return _delete_bootstrap_guidance_source(db, spec)

    created = False

    source = db.get(SourceDocument, spec["source_document_id"])
    if source is None:
        source = SourceDocument(id=spec["source_document_id"])
        db.add(source)
        created = True
    source.title = spec["title"]
    source.jurisdiction = spec.get("jurisdiction", "WA")
    source.authority = spec.get("authority", "Department of Planning, Lands and Heritage")
    source.source_type = spec.get("source_type", "r_code")
    source.canonical_url = spec["url"]
    source.licence_notes = spec.get(
        "licence_notes",
        "Short public WA Government R-Codes guidance excerpt used to verify source-cited retrieval bootstrap. "
        "Not a substitute for full source review.",
    )
    source.access_type = "public"
    source.scrape_allowed = False
    source.is_active = True
    db.flush()

    version = db.get(SourceVersion, spec["source_version_id"])
    if version is None:
        version = SourceVersion(id=spec["source_version_id"])
        db.add(version)
        created = True
    version.source_document_id = source.id
    version.version_label = spec["version_label"]
    version.effective_date = None
    version.published_date = None
    version.retrieved_at = BOOTSTRAP_RETRIEVED_AT
    version.content_sha256 = hash_text(spec["text"])
    version.raw_text = spec["text"]
    version.parse_status = "ok"
    version.review_status = "accepted"
    version.reviewed_by = "system-bootstrap"
    version.reviewed_at = BOOTSTRAP_RETRIEVED_AT
    db.flush()

    licence = db.get(SourceLicenceReview, spec["licence_review_id"])
    if licence is None:
        licence = SourceLicenceReview(id=spec["licence_review_id"])
        db.add(licence)
        created = True
    licence.source_document_id = source.id
    licence.source_version_id = version.id
    licence.licence_url = source.canonical_url
    licence.allowed_use = True
    licence.allowed_storage = True
    licence.allowed_redistribution = False
    licence.allowed_ai_processing = True
    licence.reviewed_by = "system-bootstrap"
    licence.reviewed_at = BOOTSTRAP_RETRIEVED_AT
    licence.review_status = "approved"
    db.flush()

    clause = db.get(Clause, spec["clause_id"])
    if clause is None:
        clause = Clause(id=spec["clause_id"])
        db.add(clause)
        created = True
    clause.source_version_id = version.id
    clause.clause_id = spec["clause_ref"]
    clause.heading = spec["heading"]
    clause.page_number = spec["page_number"]
    clause.text = spec["text"]
    clause.normalized_text = normalize_text(spec["text"])
    clause.start_anchor = spec["clause_ref"]
    clause.text_sha256 = hash_text(spec["text"])
    db.flush()

    disposition = db.get(ClauseDisposition, spec["disposition_id"])
    if disposition is None:
        disposition = ClauseDisposition(id=spec["disposition_id"])
        db.add(disposition)
        created = True
    disposition.clause_id = clause.id
    disposition.disposition = "procedural"
    disposition.rationale = "Short guidance excerpt supports retrieval only and does not encode a deterministic rule."
    disposition.reviewer = "system-bootstrap"

    chunk = db.get(SourceChunk, spec["chunk_id"])
    if chunk is None:
        chunk = SourceChunk(id=spec["chunk_id"])
        db.add(chunk)
        created = True
    chunk.source_version_id = version.id
    chunk.clause_id = clause.id
    chunk.heading = clause.heading
    chunk.page_number = clause.page_number
    chunk.text = spec["text"]
    chunk.token_count = len(spec["text"].split())
    db.flush()

    citation = Citation(
        source_document_id=source.id,
        source_title=source.title,
        source_version_id=version.id,
        version_label=version.version_label,
        effective_date=version.effective_date,
        retrieved_at=version.retrieved_at,
        clause_id=clause.clause_id,
        heading=clause.heading,
        page_number=clause.page_number,
        canonical_url=source.canonical_url,
        quote=spec["text"],
    )
    source_citation = db.get(SourceCitation, spec["citation_id"])
    if source_citation is None:
        source_citation = SourceCitation(id=spec["citation_id"])
        db.add(source_citation)
        created = True
    source_citation.source_chunk_id = chunk.id
    source_citation.source_version_id = version.id
    source_citation.clause_id = clause.id
    source_citation.citation_json = to_json(citation.model_dump(mode="json"))

    return created


def _existing_citable_guidance_version(db: Session, spec: dict[str, Any]) -> SourceVersion | None:
    rows = db.execute(
        select(SourceVersion)
        .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
        .where(
            SourceDocument.canonical_url == spec["url"],
            SourceDocument.id != spec["source_document_id"],
            SourceVersion.is_superseded.is_(False),
        )
        .order_by(SourceVersion.reviewed_at.desc(), SourceVersion.created_at.desc())
    ).scalars()
    for version in rows:
        if source_version_can_support_citable_retrieval(db, version.id):
            return version
    return None


def _delete_bootstrap_guidance_source(db: Session, spec: dict[str, Any]) -> bool:
    deleted = False
    for model, row_id in [
        (SourceCitation, spec["citation_id"]),
        (SourceChunk, spec["chunk_id"]),
        (ClauseDisposition, spec["disposition_id"]),
        (Clause, spec["clause_id"]),
        (SourceLicenceReview, spec["licence_review_id"]),
        (SourceVersion, spec["source_version_id"]),
    ]:
        row = db.get(model, row_id)
        if row is not None:
            db.delete(row)
            deleted = True
            db.flush()

    source = db.get(SourceDocument, spec["source_document_id"])
    if source is not None:
        remaining_version = db.scalar(
            select(SourceVersion.id).where(SourceVersion.source_document_id == source.id).limit(1)
        )
        if remaining_version is None:
            db.delete(source)
            deleted = True
            db.flush()
    return deleted

"""Conservative in-memory document parser for V3 document contract endpoints."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePath
from typing import Any
from uuid import uuid4


MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
TEXT_MEDIA_TYPES = {
    "text/plain",
    "text/csv",
    "text/markdown",
    "application/json",
    "application/xml",
    "text/xml",
}
DXF_MEDIA_TYPES = {"application/dxf", "application/x-dxf", "image/vnd.dxf"}
DOCX_MEDIA_TYPES = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
PDF_MEDIA_TYPES = {"application/pdf"}
IMAGE_PREFIXES = ("image/",)
IFC_MEDIA_TYPES = {"application/ifc", "application/x-step", "model/ifc"}
SAMPLE_PACK_CONTENT = b"""Lot area: 450 m2
Footprint: 218 m2
Open space: 180 m2
Front setback: 4.5 m
Garage width: 5.4 m
Boundary wall length: 0 m
"""
SAMPLE_EXPECTED_FACTS = {
    "lot area": (450.0, "m2"),
    "building footprint": (218.0, "m2"),
    "open space": (180.0, "m2"),
    "front setback": (4.5, "m"),
    "garage width": (5.4, "m"),
    "boundary wall length": (0.0, "m"),
}


class DocumentReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    HUMAN_CONFIRMED = "human_confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ParserCapability:
    media_type: str
    parser_name: str
    support_status: str
    notes: str


@dataclass(frozen=True)
class DocumentPage:
    id: str
    document_id: str
    page_number: int
    text: str
    parser_name: str
    parser_version: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentFact:
    id: str
    document_id: str
    fact_type: str
    label: str
    value: Any
    numeric_value: float | None
    unit: str | None
    confidence: float
    review_status: DocumentReviewStatus
    source: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    org_id: str
    project_id: str
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    parser_name: str
    parser_version: str
    parse_status: str
    uploaded_by_user_id: str
    uploaded_at: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentParseResult:
    document: DocumentRecord
    pages: tuple[DocumentPage, ...]
    facts: tuple[DocumentFact, ...]


class DocumentNotFoundError(KeyError):
    """Raised when a document is unknown to the in-memory library."""


class DocumentParser:
    """Extract reviewable document facts without producing compliance verdicts."""

    version = "v0.1"

    def capabilities(self) -> tuple[ParserCapability, ...]:
        return (
            ParserCapability("text/plain", "plain_text_parser", "active", "Text and simple numeric facts."),
            ParserCapability("text/csv", "csv_text_parser", "active", "CSV rows are flattened to text."),
            ParserCapability("application/dxf", "dxf_text_parser", "active", "DXF-like text dimensions and layers."),
            ParserCapability("application/pdf", "pdf_text_parser", "active", "Text extraction only; no raster measurement."),
            ParserCapability("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx_text_parser", "active", "Paragraph text extraction."),
            ParserCapability("model/ifc", "ifc_text_parser", "preview", "IFC quantities are review-gated."),
            ParserCapability("image/*", "image_ocr_queue", "blocked_without_calibration", "OCR/raster measurements require explicit calibration."),
        )

    def parse(
        self,
        *,
        document_id: str,
        filename: str,
        media_type: str,
        content: bytes,
    ) -> tuple[str, str, str, tuple[DocumentPage, ...], tuple[DocumentFact, ...], dict[str, Any]]:
        normalized_media_type = _normalize_media_type(media_type, filename)
        parser_name = _parser_name(normalized_media_type, filename)
        text, extraction_notes = _extract_text(normalized_media_type, filename, content)
        pages = _pages(document_id, text, parser_name, self.version, extraction_notes)
        facts = _facts(document_id, text, parser_name, normalized_media_type)
        parse_status = "parsed" if text.strip() or facts else "needs_more_info"
        metadata = {
            "extraction_notes": extraction_notes,
            "measurement_policy": "Measurements are advisory pending automated validation.",
            "raster_measurement_policy": "Raster/PDF/image measurements are not compliance-ready without calibration.",
        }
        return normalized_media_type, parser_name, parse_status, pages, facts, metadata


class InMemoryDocumentLibrary:
    """Small in-memory document library for PR8 contract development and live demos."""

    def __init__(self, parser: DocumentParser | None = None) -> None:
        self.parser = parser or DocumentParser()
        self.documents: dict[str, DocumentRecord] = {}
        self.pages: dict[str, tuple[DocumentPage, ...]] = {}
        self.facts: dict[str, tuple[DocumentFact, ...]] = {}

    def upload(
        self,
        *,
        org_id: str,
        project_id: str,
        user_id: str,
        filename: str,
        media_type: str,
        content: bytes,
    ) -> DocumentParseResult:
        if not content:
            raise ValueError("document content is required")
        if len(content) > MAX_DOCUMENT_BYTES:
            raise ValueError("document exceeds the 15 MB parser limit")
        safe_filename = _safe_filename(filename)
        document_id = f"doc_{uuid4().hex}"
        sha256 = hashlib.sha256(content).hexdigest()
        parsed_media_type, parser_name, parse_status, pages, facts, metadata = self.parser.parse(
            document_id=document_id,
            filename=safe_filename,
            media_type=media_type,
            content=content,
        )
        record = DocumentRecord(
            id=document_id,
            org_id=org_id,
            project_id=project_id,
            filename=safe_filename,
            media_type=parsed_media_type,
            size_bytes=len(content),
            sha256=sha256,
            parser_name=parser_name,
            parser_version=self.parser.version,
            parse_status=parse_status,
            uploaded_by_user_id=user_id,
            uploaded_at=datetime.now(UTC),
            metadata=metadata,
        )
        self.documents[document_id] = record
        self.pages[document_id] = pages
        self.facts[document_id] = facts
        return DocumentParseResult(record, pages, facts)

    def get_document(self, document_id: str) -> DocumentRecord:
        try:
            return self.documents[document_id]
        except KeyError as exc:
            raise DocumentNotFoundError(document_id) from exc

    def get_pages(self, document_id: str) -> tuple[DocumentPage, ...]:
        self.get_document(document_id)
        return self.pages.get(document_id, ())

    def get_facts(self, document_id: str) -> tuple[DocumentFact, ...]:
        self.get_document(document_id)
        return self.facts.get(document_id, ())

    def review_fact(
        self,
        *,
        document_id: str,
        fact_id: str,
        review_status: DocumentReviewStatus,
        reviewed_by: str,
        note: str | None = None,
    ) -> DocumentFact:
        facts = list(self.get_facts(document_id))
        for index, fact in enumerate(facts):
            if fact.id == fact_id:
                reviewed = DocumentFact(
                    id=fact.id,
                    document_id=fact.document_id,
                    fact_type=fact.fact_type,
                    label=fact.label,
                    value=fact.value,
                    numeric_value=fact.numeric_value,
                    unit=fact.unit,
                    confidence=fact.confidence,
                    review_status=review_status,
                    source=fact.source,
                    metadata={
                        **fact.metadata,
                        "reviewed_by": reviewed_by,
                        "review_note": note,
                        "reviewed_at": datetime.now(UTC).isoformat(),
                    },
                )
                facts[index] = reviewed
                self.facts[document_id] = tuple(facts)
                return reviewed
        raise DocumentNotFoundError(fact_id)


def sample_parser_accuracy_report() -> dict[str, Any]:
    """Run the fixed canary pack through the parser and report deterministic coverage."""

    library = InMemoryDocumentLibrary()
    result = library.upload(
        org_id="org_demo_accuracy",
        project_id="project_demo_accuracy",
        user_id="system_demo_accuracy",
        filename="m1-canary-site-plan.txt",
        media_type="text/plain",
        content=SAMPLE_PACK_CONTENT,
    )
    extracted = {
        fact.label: {"numeric_value": fact.numeric_value, "unit": fact.unit}
        for fact in result.facts
    }
    matched: list[str] = []
    missing: list[str] = []
    mismatched: list[dict[str, Any]] = []
    for label, (expected_value, expected_unit) in SAMPLE_EXPECTED_FACTS.items():
        actual = extracted.get(label)
        if actual is None:
            missing.append(label)
            continue
        actual_value = actual["numeric_value"]
        actual_unit = actual["unit"]
        if (
            isinstance(actual_value, int | float)
            and abs(float(actual_value) - expected_value) < 0.0001
            and actual_unit == expected_unit
        ):
            matched.append(label)
        else:
            mismatched.append(
                {
                    "label": label,
                    "expected": {"numeric_value": expected_value, "unit": expected_unit},
                    "actual": actual,
                }
            )
    expected_count = len(SAMPLE_EXPECTED_FACTS)
    extracted_count = len(extracted)
    matched_count = len(matched)
    return {
        "demo_fixture_status": "passed" if matched_count == expected_count and not mismatched else "failed",
        "beta_status": "not_beta_ready",
        "reason": "The canary parser check passed, but real-project beta needs a broader fixture set and automated validation workflow.",
        "expected_fact_count": expected_count,
        "extracted_fact_count": extracted_count,
        "matched_fact_count": matched_count,
        "recall": matched_count / expected_count,
        "precision": matched_count / extracted_count if extracted_count else 0.0,
        "matched": matched,
        "missing": missing,
        "mismatched": mismatched,
        "blocked_for_beta": [
            "real PDF/DOCX/DXF/IFC fixture pack",
            "per-field precision/recall report across real samples",
            "automated validation workflow connected to persistence",
            "no image/PDF/raster measurement without explicit calibration",
        ],
    }


def _normalize_media_type(media_type: str, filename: str) -> str:
    lowered = (media_type or "").split(";")[0].strip().lower()
    suffix = PurePath(filename).suffix.lower()
    if lowered:
        return lowered
    return {
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".md": "text/markdown",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".dxf": "application/dxf",
        ".ifc": "model/ifc",
    }.get(suffix, "application/octet-stream")


def _parser_name(media_type: str, filename: str) -> str:
    suffix = PurePath(filename).suffix.lower()
    if media_type in DXF_MEDIA_TYPES or suffix == ".dxf":
        return "draftcheck.dxf_text_parser"
    if media_type in PDF_MEDIA_TYPES or suffix == ".pdf":
        return "draftcheck.pdf_text_parser"
    if media_type in DOCX_MEDIA_TYPES or suffix == ".docx":
        return "draftcheck.docx_text_parser"
    if media_type in IFC_MEDIA_TYPES or suffix == ".ifc":
        return "draftcheck.ifc_text_parser"
    if media_type.startswith(IMAGE_PREFIXES):
        return "draftcheck.image_ocr_queue"
    if media_type == "text/csv" or suffix == ".csv":
        return "draftcheck.csv_text_parser"
    return "draftcheck.plain_text_parser"


def _extract_text(media_type: str, filename: str, content: bytes) -> tuple[str, list[str]]:
    suffix = PurePath(filename).suffix.lower()
    notes: list[str] = []
    if media_type in PDF_MEDIA_TYPES or suffix == ".pdf":
        text = _extract_pdf_text(content)
        notes.append("pdf_text_only_no_raster_measurements")
        return text, notes
    if media_type in DOCX_MEDIA_TYPES or suffix == ".docx":
        text = _extract_docx_text(content)
        notes.append("docx_paragraph_text")
        return text, notes
    if media_type.startswith(IMAGE_PREFIXES):
        notes.append("image_ocr_requires_calibration")
        return "", notes
    decoded = _decode_text(content)
    if media_type == "text/csv" or suffix == ".csv":
        notes.append("csv_rows_flattened")
        return _flatten_csv(decoded), notes
    if media_type in IFC_MEDIA_TYPES or suffix == ".ifc":
        notes.append("ifc_quantity_preview_review_required")
    if media_type in DXF_MEDIA_TYPES or suffix == ".dxf":
        notes.append("dxf_text_entities_review_required")
    return decoded, notes


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return _decode_text(content)
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception:
        return _decode_text(content)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(content: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        return _decode_text(content)
    try:
        doc = Document(io.BytesIO(content))
    except Exception:
        return _decode_text(content)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _flatten_csv(text: str) -> str:
    rows = csv.reader(io.StringIO(text))
    return "\n".join(" | ".join(cell.strip() for cell in row if cell.strip()) for row in rows)


def _pages(
    document_id: str,
    text: str,
    parser_name: str,
    parser_version: str,
    notes: list[str],
) -> tuple[DocumentPage, ...]:
    if not text.strip():
        return ()
    chunks = [chunk.strip() for chunk in re.split(r"\f+|\n\s*---page---\s*\n", text) if chunk.strip()]
    if not chunks:
        chunks = [text.strip()]
    return tuple(
        DocumentPage(
            id=f"page_{document_id}_{index}",
            document_id=document_id,
            page_number=index,
            text=chunk,
            parser_name=parser_name,
            parser_version=parser_version,
            metadata={"notes": notes},
        )
        for index, chunk in enumerate(chunks, start=1)
    )


def _facts(document_id: str, text: str, parser_name: str, media_type: str) -> tuple[DocumentFact, ...]:
    facts: list[DocumentFact] = []
    lower_text = text.lower()
    for label, patterns, unit in (
        ("lot area", (r"lot\s+area[:\s]+([0-9]+(?:\.[0-9]+)?)\s*(m2|sqm)?",), "m2"),
        ("building footprint", (r"(?:building\s+)?footprint[:\s]+([0-9]+(?:\.[0-9]+)?)\s*(m2|sqm)?",), "m2"),
        ("open space", (r"open\s+space[:\s]+([0-9]+(?:\.[0-9]+)?)\s*(m2|sqm)?",), "m2"),
        ("front setback", (r"(?:front|primary)\s+setback[:\s]+([0-9]+(?:\.[0-9]+)?)\s*(m|metres?)?",), "m"),
        ("garage width", (r"garage\s+width[:\s]+([0-9]+(?:\.[0-9]+)?)\s*(m|metres?)?",), "m"),
        ("boundary wall length", (r"boundary\s+wall(?:\s+length)?[:\s]+([0-9]+(?:\.[0-9]+)?)\s*(m|metres?)?",), "m"),
    ):
        match = _first_match(patterns, lower_text)
        if match:
            value = float(match.group(1))
            facts.append(
                _fact(
                    document_id=document_id,
                    label=label,
                    fact_type="drawing_measurement",
                    value=value,
                    unit=unit,
                    parser_name=parser_name,
                    method="text_measurement_pattern",
                    confidence=0.72,
                )
            )
    facts.extend(_dxf_facts(document_id, text, parser_name))
    facts.extend(_ifc_facts(document_id, text, parser_name, media_type))
    return tuple(_dedupe_facts(facts))


def _first_match(patterns: tuple[str, ...], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match
    return None


def _dxf_facts(document_id: str, text: str, parser_name: str) -> list[DocumentFact]:
    facts: list[DocumentFact] = []
    if "a-dimensions" not in text.lower() and "dimension" not in text.lower():
        return facts
    for index, value in enumerate(re.findall(r"\b(?:DIMENSION|LINE_LENGTH|MEASUREMENT)[:=\s]+([0-9]+(?:\.[0-9]+)?)", text, flags=re.I), start=1):
        facts.append(
            _fact(
                document_id=document_id,
                label=f"dxf dimension {index}",
                fact_type="drawing_dimension",
                value=float(value),
                unit="m",
                parser_name=parser_name,
                method="dxf_text_dimension_entity",
                confidence=0.68,
            )
        )
    return facts


def _ifc_facts(document_id: str, text: str, parser_name: str, media_type: str) -> list[DocumentFact]:
    if media_type not in IFC_MEDIA_TYPES and ".ifc" not in text[:200].lower():
        return []
    facts: list[DocumentFact] = []
    for index, value in enumerate(re.findall(r"IFCQUANTITYAREA\([^)]*?,\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.I), start=1):
        facts.append(
            _fact(
                document_id=document_id,
                label=f"ifc area quantity {index}",
                fact_type="model_quantity",
                value=float(value),
                unit="m2",
                parser_name=parser_name,
                method="ifc_quantity_area_preview",
                confidence=0.55,
            )
        )
    return facts


def _fact(
    *,
    document_id: str,
    label: str,
    fact_type: str,
    value: float,
    unit: str,
    parser_name: str,
    method: str,
    confidence: float,
) -> DocumentFact:
    return DocumentFact(
        id=f"fact_{uuid4().hex}",
        document_id=document_id,
        fact_type=fact_type,
        label=label,
        value={"value": value, "unit": unit},
        numeric_value=value,
        unit=unit,
        confidence=confidence,
        review_status=DocumentReviewStatus.PENDING_REVIEW,
        source=parser_name,
        metadata={
            "method": method,
            "measurement_compliance_ready": False,
            "measurement_readiness_reason": "human promotion required before compliance use",
        },
    )


def _dedupe_facts(facts: list[DocumentFact]) -> list[DocumentFact]:
    seen: set[tuple[str, float | None, str | None]] = set()
    deduped: list[DocumentFact] = []
    for fact in facts:
        key = (fact.label, fact.numeric_value, fact.unit)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)
    return deduped


def _safe_filename(filename: str) -> str:
    name = PurePath(filename or "upload.bin").name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name or "upload.bin"

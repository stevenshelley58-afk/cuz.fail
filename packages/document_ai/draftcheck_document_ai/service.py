from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import (
    CheckResult,
    DocumentChunk,
    DocumentPage,
    ExtractedDocumentFact,
    ExtractedMeasurement,
    Project,
    ProjectDocument,
)
from draftcheck_document_ai.facts import DocumentFactCandidate, extract_fact_candidates


DRAWING_QA_KEYWORDS = {
    "title_block": ["title block", "project", "drawing no", "sheet"],
    "revision": ["revision", "rev"],
    "scale": ["scale", "1:"],
    "north_point": ["north", "nominated north"],
    "dimensions": ["dimension", "mm", "metres"],
    "levels": ["ffl", "ngl", "natural ground", "finished floor"],
    "site_coverage": ["site cover", "site coverage"],
    "open_space": ["open space"],
    "parking": ["parking", "garage", "carport"],
}

UNCALIBRATED_DRAWING_CONTEXT_TERMS = (
    "uncalibrated",
    "not calibrated",
    "calibration missing",
    "raster",
    "ocr",
    "pdf extraction",
    "pdf-derived",
    "pdf derived",
)

DRAWING_MEASUREMENT_CONTEXT_TERMS = (
    "dimension",
    "dimension measurement",
    "line length",
    "polyline length",
    "scale inferred",
    "scaled from",
)


class DocumentAnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def analyze_document(self, project_id: str, document_id: str) -> list[CheckResult]:
        doc = self.db.get(ProjectDocument, document_id)
        if not doc or doc.project_id != project_id:
            raise KeyError("Document not found")
        project = self.db.get(Project, project_id)
        if not project:
            raise KeyError("Project not found")
        as_of_date = project.as_of_date or project.lodgement_date or "unknown"
        assessment_basis = project.assessment_basis
        text = f"{doc.title}\n{doc.text_content}".lower()
        results: list[CheckResult] = []
        for key, terms in DRAWING_QA_KEYWORDS.items():
            detected = any(term in text for term in terms)
            status = "needs_human_review" if detected else "missing_info"
            result = CheckResult(
                project_id=project_id,
                check_key=f"drawing_qa_{key}",
                label=f"Drawing QA: {key.replace('_', ' ')}",
                category="drawing_qa",
                status=status,
                as_of_date=as_of_date,
                assessment_basis=assessment_basis,
                requirement=f"Detected plan set should show {key.replace('_', ' ')} where applicable.",
                proposed="Detected" if detected else "Not detected in extracted text.",
                evidence_refs_json=to_json([document_id]),
                citations_json=to_json([]),
                assumptions_json=to_json(["Text extraction is incomplete for many drawings. Visual review required."]),
                missing_information_json=to_json([] if detected else [key.replace("_", " ")]),
                confidence=0.55 if detected else 0.25,
                requires_human_review=True,
                created_by_model="document-keyword-qa",
                prompt_version="drawing-qa-v1",
            )
            self.db.add(result)
            results.append(result)
        doc.analysis_status = "completed"
        facts = self.extract_facts_for_document(project_id, document_id)
        record_audit(
            self.db,
            action="document.analyzed",
            target_type="project_document",
            target_id=document_id,
            project_id=project_id,
            metadata={"qa_results": len(results), "facts_extracted": len(facts)},
        )
        return results

    def extract_facts_for_document(self, project_id: str, document_id: str) -> list[dict]:
        doc = self.db.get(ProjectDocument, document_id)
        if not doc or doc.project_id != project_id:
            raise KeyError("Document not found")

        self.db.query(ExtractedDocumentFact).filter(
            ExtractedDocumentFact.document_id == document_id
        ).delete()
        self.db.query(ExtractedMeasurement).filter(
            ExtractedMeasurement.project_id == project_id,
            ExtractedMeasurement.evidence_ref.like(f"document:{document_id}:%"),
        ).delete()

        facts: list[dict] = []
        for page in self._pages(doc):
            for candidate in extract_fact_candidates(page.text_content):
                measurement_readiness = _measurement_readiness(candidate)
                fact = ExtractedDocumentFact(
                    project_id=project_id,
                    document_id=document_id,
                    page_number=page.page_number,
                    fact_type=candidate.fact_type,
                    label=candidate.label,
                    value_text=candidate.value_text,
                    numeric_value=candidate.numeric_value,
                    unit=candidate.unit,
                    source_text=candidate.source_text,
                    confidence=candidate.confidence,
                    metadata_json=to_json(
                        {
                            "measurement_key": candidate.measurement_key,
                            "measurement_compliance_ready": measurement_readiness["ready"],
                            "measurement_readiness_reason": measurement_readiness["reason"],
                        }
                    ),
                )
                self.db.add(fact)
                self.db.flush()
                if (
                    candidate.measurement_key
                    and candidate.numeric_value is not None
                    and measurement_readiness["ready"]
                ):
                    self.db.add(
                        ExtractedMeasurement(
                            project_id=project_id,
                            key=candidate.measurement_key,
                            value=candidate.numeric_value,
                            unit=candidate.unit or "unknown",
                            source="document_extraction",
                            confidence=candidate.confidence,
                            evidence_ref=f"document:{document_id}:page:{page.page_number}:fact:{fact.id}",
                        )
                    )
                facts.append(_fact_to_dict(fact))

        record_audit(
            self.db,
            action="document.facts_extracted",
            target_type="project_document",
            target_id=document_id,
            project_id=project_id,
            metadata={"facts_extracted": len(facts)},
        )
        return facts

    def list_facts(self, project_id: str, document_id: str | None = None) -> list[dict]:
        stmt = select(ExtractedDocumentFact).where(ExtractedDocumentFact.project_id == project_id)
        if document_id:
            stmt = stmt.where(ExtractedDocumentFact.document_id == document_id)
        rows = self.db.scalars(stmt.order_by(ExtractedDocumentFact.created_at.desc())).all()
        return [_fact_to_dict(row) for row in rows]

    def search_project_documents(self, project_id: str, query: str, limit: int = 10) -> list[dict]:
        terms = [term.lower() for term in query.split() if len(term) >= 3]
        if not terms:
            return []
        rows = self.db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.project_id == project_id)
            .order_by(DocumentChunk.created_at.desc())
        ).all()
        scored: list[tuple[float, DocumentChunk]] = []
        for chunk in rows:
            haystack = chunk.text.lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score / len(terms), chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "chunk_id": chunk.id,
                "score": score,
                "text": chunk.text,
                "evidence_ref": f"document:{chunk.document_id}:page:{chunk.page_number}:chunk:{chunk.id}",
                "metadata": from_json(chunk.metadata_json, {}),
            }
            for score, chunk in scored[:limit]
        ]

    def pages_for_document(self, project_id: str, document_id: str) -> list[dict]:
        doc = self.db.get(ProjectDocument, document_id)
        if not doc or doc.project_id != project_id:
            raise KeyError("Document not found")
        pages = self.db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        ).all()
        if not pages:
            return [{"page_number": 1, "text_content": doc.text_content, "image_object_key": None}]
        return [
            {
                "id": page.id,
                "page_number": page.page_number,
                "text_content": page.text_content,
                "image_object_key": page.image_object_key,
            }
            for page in pages
        ]

    def _pages(self, doc: ProjectDocument) -> list[DocumentPage]:
        pages = self.db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.page_number)
        ).all()
        if pages:
            return list(pages)
        fallback = DocumentPage(document_id=doc.id, page_number=1, text_content=doc.text_content)
        return [fallback]

    def classify_documents(self, project_id: str) -> list[dict]:
        docs = self.db.scalars(select(ProjectDocument).where(ProjectDocument.project_id == project_id)).all()
        return [{"document_id": doc.id, "detected_type": _classify(doc.title, doc.text_content)} for doc in docs]


def _classify(title: str, text: str) -> str:
    blob = f"{title} {text}".lower()
    for key in ["site plan", "floor plan", "elevation", "section", "shadow", "survey", "energy", "bal", "rfi"]:
        if key in blob:
            return key.replace(" ", "_")
    if "council" in blob or "request for information" in blob:
        return "council_rfi"
    return "unknown"


def _measurement_readiness(candidate: DocumentFactCandidate) -> dict[str, str | bool]:
    if not candidate.measurement_key or candidate.numeric_value is None:
        return {"ready": False, "reason": "not_a_project_measurement"}
    if candidate.fact_type == "drawing_dimension":
        return {"ready": False, "reason": "drawing_dimension_fact_only"}
    source = candidate.source_text.lower()
    has_uncalibrated_context = any(term in source for term in UNCALIBRATED_DRAWING_CONTEXT_TERMS)
    has_drawing_measurement_context = any(term in source for term in DRAWING_MEASUREMENT_CONTEXT_TERMS)
    has_explicit_calibration = "calibrated" in source and "uncalibrated" not in source
    if has_uncalibrated_context and has_drawing_measurement_context and not has_explicit_calibration:
        return {"ready": False, "reason": "uncalibrated_raster_or_pdf_drawing_measurement"}
    return {"ready": True, "reason": "measurement_candidate_ready"}


def _fact_to_dict(row: ExtractedDocumentFact) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "document_id": row.document_id,
        "page_number": row.page_number,
        "fact_type": row.fact_type,
        "label": row.label,
        "value_text": row.value_text,
        "numeric_value": row.numeric_value,
        "unit": row.unit,
        "source_text": row.source_text,
        "confidence": row.confidence,
        "metadata": from_json(row.metadata_json, {}),
        "created_at": row.created_at,
    }

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, hash_text, to_json
from draftcheck_core.models import (
    DocumentChunk,
    DocumentPage,
    ExtractedMeasurement,
    HumanSignoff,
    Project,
    ProjectDocument,
    Property,
)
from draftcheck_shared.schemas import (
    DocumentCreate,
    MeasurementCreate,
    ProjectCreate,
    ProjectUpdate,
    PropertyUpsert,
    SignoffCreate,
)


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, payload: ProjectCreate) -> Project:
        project = Project(**payload.model_dump(), status="active")
        self.db.add(project)
        self.db.flush()
        record_audit(
            self.db,
            action="project.created",
            target_type="project",
            target_id=project.id,
            actor_id=payload.created_by,
            project_id=project.id,
            metadata={"local_government": project.local_government, "stage": project.stage},
        )
        return project

    def list_projects(self) -> list[Project]:
        return list(self.db.scalars(select(Project).order_by(Project.created_at.desc())))

    def get_project(self, project_id: str) -> Project:
        project = self.db.get(Project, project_id)
        if not project:
            raise KeyError("Project not found")
        return project

    def update_project(self, project_id: str, payload: ProjectUpdate) -> Project:
        project = self.get_project(project_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, key, value)
        record_audit(
            self.db,
            action="project.updated",
            target_type="project",
            target_id=project_id,
            project_id=project_id,
            metadata=payload.model_dump(exclude_unset=True),
        )
        return project

    def delete_project(self, project_id: str) -> None:
        project = self.get_project(project_id)
        project.status = "deleted"
        record_audit(
            self.db,
            action="project.deleted",
            target_type="project",
            target_id=project_id,
            project_id=project_id,
        )

    def upsert_property(self, project_id: str, payload: PropertyUpsert) -> Property:
        self.get_project(project_id)
        prop = self.db.scalar(select(Property).where(Property.project_id == project_id))
        if not prop:
            prop = Property(project_id=project_id, address=payload.address)
            self.db.add(prop)
        prop.address = payload.address
        prop.zoning = payload.zoning
        prop.lot_area_m2 = payload.lot_area_m2
        prop.overlays_json = to_json(payload.overlays)
        prop.planning_scheme = payload.planning_scheme
        record_audit(
            self.db,
            action="property.upserted",
            target_type="property",
            target_id=prop.id,
            project_id=project_id,
            metadata={"overlays": payload.overlays, "lot_area_m2": payload.lot_area_m2},
        )
        return prop

    def get_property(self, project_id: str) -> Property | None:
        self.get_project(project_id)
        return self.db.scalar(select(Property).where(Property.project_id == project_id))

    def add_document(self, project_id: str, payload: DocumentCreate) -> ProjectDocument:
        self.get_project(project_id)
        doc = ProjectDocument(
            project_id=project_id,
            document_type=payload.document_type,
            title=payload.title,
            filename=payload.filename,
            content_type=payload.content_type,
            text_content=payload.text_content,
            content_sha256=hash_text(payload.text_content or payload.title),
            parse_status="ok" if payload.text_content else "metadata_only",
            metadata_json=to_json(payload.metadata),
        )
        self.db.add(doc)
        self.db.flush()
        self._replace_document_pages(doc.id, [payload.text_content] if payload.text_content else [])
        record_audit(
            self.db,
            action="document.uploaded",
            target_type="project_document",
            target_id=doc.id,
            project_id=project_id,
            metadata={"document_type": doc.document_type, "content_sha256": doc.content_sha256},
        )
        return doc

    def add_extracted_document(
        self,
        project_id: str,
        *,
        document_type: str,
        title: str,
        filename: str | None,
        content_type: str,
        raw_object_key: str,
        content_sha256: str,
        pages: list[str],
        metadata: dict | None = None,
    ) -> ProjectDocument:
        self.get_project(project_id)
        text_content = "\n".join(page for page in pages if page).strip()
        doc = ProjectDocument(
            project_id=project_id,
            document_type=document_type,
            title=title,
            filename=filename,
            content_type=content_type,
            raw_object_key=raw_object_key,
            text_content=text_content,
            content_sha256=content_sha256,
            parse_status="ok" if text_content else "partial",
            metadata_json=to_json(metadata or {}),
        )
        self.db.add(doc)
        self.db.flush()
        self._replace_document_pages(doc.id, pages)
        record_audit(
            self.db,
            action="document.uploaded",
            target_type="project_document",
            target_id=doc.id,
            project_id=project_id,
            metadata={
                "document_type": doc.document_type,
                "content_sha256": doc.content_sha256,
                "raw_object_key": raw_object_key,
                "page_count": len(pages),
            },
        )
        return doc

    def _replace_document_pages(self, document_id: str, pages: list[str]) -> None:
        doc = self.db.get(ProjectDocument, document_id)
        if not doc:
            raise KeyError("Document not found")
        self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        self.db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete()
        for index, page_text in enumerate(pages, start=1):
            page = DocumentPage(
                document_id=document_id,
                page_number=index,
                text_content=page_text,
            )
            self.db.add(page)
            self.db.flush()
            for chunk_index, chunk in enumerate(_chunk_text(page_text), start=1):
                self.db.add(
                    DocumentChunk(
                        project_id=doc.project_id,
                        document_id=document_id,
                        page_id=page.id,
                        page_number=index,
                        chunk_index=chunk_index,
                        text=chunk,
                        token_count=max(1, int(len(chunk.split()) * 1.25)),
                        metadata_json=to_json({"source": "project_document", "page_number": index}),
                    )
                )

    def list_documents(self, project_id: str) -> list[ProjectDocument]:
        self.get_project(project_id)
        return list(
            self.db.scalars(
                select(ProjectDocument)
                .where(ProjectDocument.project_id == project_id)
                .order_by(ProjectDocument.created_at.desc())
            )
        )

    def get_document(self, project_id: str, document_id: str) -> ProjectDocument:
        doc = self.db.get(ProjectDocument, document_id)
        if not doc or doc.project_id != project_id:
            raise KeyError("Document not found")
        return doc

    def add_measurement(self, project_id: str, payload: MeasurementCreate) -> ExtractedMeasurement:
        self.get_project(project_id)
        measurement = ExtractedMeasurement(project_id=project_id, **payload.model_dump())
        self.db.add(measurement)
        self.db.flush()
        record_audit(
            self.db,
            action="measurement.created",
            target_type="extracted_measurement",
            target_id=measurement.id,
            project_id=project_id,
            metadata=payload.model_dump(),
        )
        return measurement

    def list_measurements(self, project_id: str) -> list[ExtractedMeasurement]:
        self.get_project(project_id)
        return list(
            self.db.scalars(
                select(ExtractedMeasurement).where(ExtractedMeasurement.project_id == project_id)
            )
        )

    def create_signoff(self, project_id: str, payload: SignoffCreate) -> HumanSignoff:
        self.get_project(project_id)
        signoff = HumanSignoff(project_id=project_id, **payload.model_dump())
        self.db.add(signoff)
        self.db.flush()
        record_audit(
            self.db,
            action="human_signoff.created",
            target_type=payload.target_type,
            target_id=payload.target_id,
            actor_id=payload.signed_by,
            project_id=project_id,
            metadata={"status": payload.status, "notes": payload.notes},
        )
        return signoff


def property_to_dict(prop: Property) -> dict:
    return {
        "id": prop.id,
        "project_id": prop.project_id,
        "address": prop.address,
        "zoning": prop.zoning,
        "lot_area_m2": prop.lot_area_m2,
        "overlays": from_json(prop.overlays_json, []),
        "planning_scheme": prop.planning_scheme,
        "created_at": prop.created_at,
        "updated_at": prop.updated_at,
    }


def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for sentence in text.replace("\n", " ").split(". "):
        candidate = f"{current}. {sentence}".strip(". ") if current else sentence
        if current and len(candidate) > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks

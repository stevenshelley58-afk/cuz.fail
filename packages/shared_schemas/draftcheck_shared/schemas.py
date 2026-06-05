from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

CheckStatus = Literal[
    "likely_pass",
    "likely_fail",
    "missing_info",
    "needs_human_review",
    "not_applicable",
]


class ApiError(BaseModel):
    detail: str
    code: str = "api_error"


class Citation(BaseModel):
    source_document_id: str
    source_title: str
    source_version_id: str
    version_label: str | None = None
    effective_date: str | None = None
    retrieved_at: datetime
    clause_id: str | None = None
    heading: str | None = None
    page_number: int | None = None
    canonical_url: str | None = None
    quote: str = Field(default="", max_length=2000)


class SourceDocumentCreate(BaseModel):
    title: str
    jurisdiction: str = "WA"
    authority: str
    local_government: str | None = None
    source_type: str
    canonical_url: str | None = None
    licence_notes: str = ""
    access_type: str = "public"
    scrape_allowed: bool = True
    content: str | None = None
    version_label: str | None = None
    effective_date: str | None = None
    published_date: str | None = None
    retrieved_at: datetime | None = None
    parse_status: str = "ok"
    raw_object_key: str | None = None
    parsed_object_key: str | None = None


class SourceDocumentRead(BaseModel):
    id: str
    title: str
    jurisdiction: str
    authority: str
    local_government: str | None
    source_type: str
    canonical_url: str | None
    licence_notes: str
    access_type: str
    scrape_allowed: bool
    is_active: bool
    created_at: datetime


class SourceVersionRead(BaseModel):
    id: str
    source_document_id: str
    version_label: str | None
    effective_date: str | None
    published_date: str | None
    retrieved_at: datetime
    content_sha256: str
    is_superseded: bool
    parse_status: str


class ManifestImportRequest(BaseModel):
    manifest_yaml: str | None = None
    entries: list[SourceDocumentCreate] | None = None


class HermesCorpusImportRequest(BaseModel):
    inventory_jsonl: str | None = None
    inventory_path: str | None = None
    corpus_root: str | None = None

    @model_validator(mode="after")
    def validate_inventory_source(self) -> "HermesCorpusImportRequest":
        has_inline_inventory = bool(self.inventory_jsonl and self.inventory_jsonl.strip())
        has_inventory_path = bool(self.inventory_path and self.inventory_path.strip())
        if has_inline_inventory == has_inventory_path:
            raise ValueError("Provide exactly one of inventory_jsonl or inventory_path")
        return self


class SourceChunkResult(BaseModel):
    chunk_id: str
    text: str
    score: float
    citation: Citation


class AskRequest(BaseModel):
    question: str
    source_filters: dict[str, Any] = Field(default_factory=dict)


class StandardAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    source_version_ids: list[str]
    assumptions: list[str]
    missing_information: list[str]
    confidence: float
    human_review_required: bool
    risk_level: Literal["low", "medium", "high"]
    status: CheckStatus | Literal["unsupported"]


class ProjectCreate(BaseModel):
    project_name: str = "Untitled project"
    client_name: str | None = None
    address: str
    local_government: str
    lot_plan: str | None = None
    project_type: str
    stage: str
    r_code_density: str | None = None
    ncc_edition: str | None = None
    created_by: str = "dev-user"


class ProjectUpdate(BaseModel):
    project_name: str | None = None
    client_name: str | None = None
    status: str | None = None
    stage: str | None = None
    r_code_density: str | None = None
    ncc_edition: str | None = None


class ProjectRead(ProjectCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class PropertyUpsert(BaseModel):
    address: str
    zoning: str | None = None
    lot_area_m2: float | None = None
    overlays: list[str] = Field(default_factory=list)
    planning_scheme: str | None = None


class PropertyRead(PropertyUpsert):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    document_type: str
    title: str
    filename: str | None = None
    content_type: str = "text/plain"
    text_content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRead(BaseModel):
    id: str
    project_id: str
    document_type: str
    title: str
    filename: str | None
    content_type: str
    raw_object_key: str | None = None
    parse_status: str
    analysis_status: str
    content_sha256: str | None
    created_at: datetime


class MeasurementCreate(BaseModel):
    key: str
    value: float
    unit: str
    source: str = "manual"
    confidence: float = 1.0
    evidence_ref: str | None = None


class CheckResultRead(BaseModel):
    id: str
    check_key: str
    label: str
    category: str
    status: CheckStatus
    requirement: str
    proposed: str
    evidence_refs: list[str]
    citations: list[Citation]
    assumptions: list[str]
    missing_information: list[str]
    confidence: float
    requires_human_review: bool
    created_at: datetime


class ComplianceMatrix(BaseModel):
    project_id: str
    check_run_id: str
    status: str
    source_version_ids: list[str]
    results: list[CheckResultRead]
    liability_notice: str


class RfiParseRequest(BaseModel):
    text: str | None = None
    document_id: str | None = None


class RfiItemRead(BaseModel):
    id: str
    item_number: int
    issue_summary: str
    requested_action: str
    relevant_drawing_sheet: str | None
    due_date: str | None
    source_requirement_candidates: list[Citation]
    priority: str
    status: str
    missing_evidence: list[str]


class ResponseDraftRead(BaseModel):
    id: str
    project_id: str
    title: str
    draft_text: str
    content: dict[str, Any]
    confidence: float
    assumptions: list[str]
    missing_information: list[str]
    citations: list[Citation]
    liability_notice: str
    requires_human_review: bool
    created_at: datetime


class ExportRequest(BaseModel):
    format: Literal["json", "docx", "xlsx", "html", "csv"] = "json"
    sections: list[str] = Field(default_factory=lambda: ["compliance_matrix", "rfi_response"])
    created_by: str = "dev-user"


class ExportManifest(BaseModel):
    id: str
    project_id: str
    export_type: str
    format: str
    status: str
    object_key: str | None
    file_sha256: str | None
    manifest: dict[str, Any]
    created_at: datetime


class SignoffCreate(BaseModel):
    target_type: str
    target_id: str
    status: Literal["approved_for_export", "rejected", "needs_revision"]
    signed_by: str
    notes: str | None = None


class JobStatus(BaseModel):
    id: str
    job_type: str
    status: str
    correlation_id: str
    project_id: str | None
    source_version_id: str | None
    provider: str
    model: str | None
    remote_job_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from draftcheck_core.database import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("usr"))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="designer", nullable=False)


class Organisation(Base, TimestampMixin):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("org"))
    name: Mapped[str] = mapped_column(String, nullable=False)


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("prj"))
    organisation_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"))
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    client_name: Mapped[str | None] = mapped_column(String)
    address: Mapped[str] = mapped_column(String, nullable=False)
    local_government: Mapped[str] = mapped_column(String, nullable=False)
    lot_plan: Mapped[str | None] = mapped_column(String)
    project_type: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str] = mapped_column(String, nullable=False)
    r_code_density: Mapped[str | None] = mapped_column(String)
    ncc_edition: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_by: Mapped[str] = mapped_column(String, default="dev-user", nullable=False)

    property: Mapped["Property | None"] = relationship(back_populates="project", uselist=False)
    documents: Mapped[list["ProjectDocument"]] = relationship(back_populates="project")


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("pty"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    zoning: Mapped[str | None] = mapped_column(String)
    lot_area_m2: Mapped[float | None] = mapped_column(Float)
    overlays_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    planning_scheme: Mapped[str | None] = mapped_column(String)

    project: Mapped[Project] = relationship(back_populates="property")


class LocalGovernment(Base, TimestampMixin):
    __tablename__ = "local_governments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("lga"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    website_url: Mapped[str | None] = mapped_column(String)
    planning_scheme_url: Mapped[str | None] = mapped_column(String)


class PlanningOverlay(Base, TimestampMixin):
    __tablename__ = "planning_overlays"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ovr"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    overlay_type: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String)
    detected_by: Mapped[str] = mapped_column(String, default="manual", nullable=False)


class ProjectDocument(Base, TimestampMixin):
    __tablename__ = "project_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("doc"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str | None] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String, default="text/plain", nullable=False)
    raw_object_key: Mapped[str | None] = mapped_column(String)
    text_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_sha256: Mapped[str | None] = mapped_column(String)
    parse_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    analysis_status: Mapped[str] = mapped_column(String, default="not_started", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    project: Mapped[Project] = relationship(back_populates="documents")


class DocumentPage(Base, TimestampMixin):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("pg"))
    document_id: Mapped[str] = mapped_column(ForeignKey("project_documents.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_object_key: Mapped[str | None] = mapped_column(String)


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("dchk"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("project_documents.id"), nullable=False)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("document_pages.id"))
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class ExtractedDocumentFact(Base, TimestampMixin):
    __tablename__ = "extracted_document_facts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("fact"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("project_documents.id"), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    fact_type: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    value_text: Mapped[str] = mapped_column(String, nullable=False)
    numeric_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class DocumentAsset(Base, TimestampMixin):
    __tablename__ = "document_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("asset"))
    document_id: Mapped[str] = mapped_column(ForeignKey("project_documents.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String, nullable=False)
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    content_sha256: Mapped[str | None] = mapped_column(String)


class SourceDocument(Base, TimestampMixin):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("src"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String, default="WA", nullable=False)
    authority: Mapped[str] = mapped_column(String, nullable=False)
    local_government: Mapped[str | None] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String)
    licence_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    access_type: Mapped[str] = mapped_column(String, default="public", nullable=False)
    scrape_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    versions: Mapped[list["SourceVersion"]] = relationship(back_populates="source_document")


class SourceVersion(Base, TimestampMixin):
    __tablename__ = "source_versions"
    __table_args__ = (UniqueConstraint("source_document_id", "content_sha256"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("sv"))
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), nullable=False)
    version_label: Mapped[str | None] = mapped_column(String)
    effective_date: Mapped[str | None] = mapped_column(String)
    published_date: Mapped[str | None] = mapped_column(String)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String, nullable=False)
    raw_object_key: Mapped[str | None] = mapped_column(String)
    parsed_object_key: Mapped[str | None] = mapped_column(String)
    superseded_by_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    is_superseded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parse_status: Mapped[str] = mapped_column(String, default="ok", nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    source_document: Mapped[SourceDocument] = relationship(back_populates="versions")


class Clause(Base, TimestampMixin):
    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cl"))
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    clause_id: Mapped[str] = mapped_column(String, nullable=False)
    heading: Mapped[str | None] = mapped_column(String)
    parent_clause_id: Mapped[str | None] = mapped_column(String)
    page_number: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_anchor: Mapped[str] = mapped_column(String, nullable=False)
    end_anchor: Mapped[str | None] = mapped_column(String)
    text_sha256: Mapped[str] = mapped_column(String, nullable=False)


class SourceChunk(Base, TimestampMixin):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("chk"))
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id"), nullable=False)
    heading: Mapped[str | None] = mapped_column(String)
    page_number: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_ref: Mapped[str | None] = mapped_column(String)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SourceCitation(Base, TimestampMixin):
    __tablename__ = "source_citations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cit"))
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id"), nullable=False)
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id"), nullable=False)
    citation_json: Mapped[str] = mapped_column(Text, nullable=False)


class SourceFetchLog(Base, TimestampMixin):
    __tablename__ = "source_fetch_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("fetch"))
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"))
    url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime)
    content_sha256: Mapped[str | None] = mapped_column(String)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class SourceUpdateEvent(Base, TimestampMixin):
    __tablename__ = "source_update_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("sue"))
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class CheckDefinition(Base, TimestampMixin):
    __tablename__ = "check_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("chkdef"))
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    requirement_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    source_query: Mapped[str] = mapped_column(String, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CheckRun(Base, TimestampMixin):
    __tablename__ = "check_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("run"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String, default="draftcheck-wa-core-v0.1", nullable=False)
    source_version_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)


class CheckResult(Base, TimestampMixin):
    __tablename__ = "check_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("res"))
    check_run_id: Mapped[str | None] = mapped_column(ForeignKey("check_runs.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    check_key: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    requirement: Mapped[str] = mapped_column(Text, default="", nullable=False)
    proposed: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    citations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    missing_information_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_model: Mapped[str] = mapped_column(String, default="deterministic", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, default="none", nullable=False)


class ExtractedMeasurement(Base, TimestampMixin):
    __tablename__ = "extracted_measurements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("meas"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, default="manual", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String)


class Assumption(Base, TimestampMixin):
    __tablename__ = "assumptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("asm"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, default="system", nullable=False)


class RfiItem(Base, TimestampMixin):
    __tablename__ = "rfi_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rfi"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("project_documents.id"))
    item_number: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    requested_action: Mapped[str] = mapped_column(Text, nullable=False)
    relevant_drawing_sheet: Mapped[str | None] = mapped_column(String)
    due_date: Mapped[str | None] = mapped_column(String)
    source_requirement_candidates_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    priority: Mapped[str] = mapped_column(String, default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    missing_evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("task"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    rfi_item_id: Mapped[str | None] = mapped_column(ForeignKey("rfi_items.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    priority: Mapped[str] = mapped_column(String, default="medium", nullable=False)


class ResponseDraft(Base, TimestampMixin):
    __tablename__ = "response_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rsp"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    missing_information_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    citations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_by_model: Mapped[str] = mapped_column(String, default="mock-provider", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, default="rfi-response-v1", nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Export(Base, TimestampMixin):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("exp"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    export_type: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="created", nullable=False)
    object_key: Mapped[str | None] = mapped_column(String)
    file_sha256: Mapped[str | None] = mapped_column(String)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_by: Mapped[str] = mapped_column(String, default="dev-user", nullable=False)


class HumanSignoff(Base, TimestampMixin):
    __tablename__ = "human_signoffs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("sig"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    signed_by: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("aud"))
    actor_id: Mapped[str] = mapped_column(String, default="system", nullable=False)
    project_id: Mapped[str | None] = mapped_column(String)
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class BackgroundJob(Base, TimestampMixin):
    __tablename__ = "background_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("job"))
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String)
    source_version_id: Mapped[str | None] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String, default="local", nullable=False)
    model: Mapped[str | None] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    remote_job_id: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text)


class JobTrace(Base, TimestampMixin):
    __tablename__ = "job_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("trace"))
    job_id: Mapped[str] = mapped_column(ForeignKey("background_jobs.id"), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String)
    source_version_id: Mapped[str | None] = mapped_column(String)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    artifacts_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

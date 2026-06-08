from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
    as_of_date: Mapped[str | None] = mapped_column(String)
    lodgement_date: Mapped[str | None] = mapped_column(String)
    assessment_basis: Mapped[str] = mapped_column(String, default="current_rules", nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_by: Mapped[str] = mapped_column(String, default="dev-user", nullable=False)

    property: Mapped["Property | None"] = relationship(back_populates="project", uselist=False)
    documents: Mapped[list["ProjectDocument"]] = relationship(back_populates="project")


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("pty"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    address_profile_id: Mapped[str | None] = mapped_column(ForeignKey("address_profiles.id"))
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


class ProjectProposal(Base, TimestampMixin):
    __tablename__ = "project_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("pp"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    proposal_type: Mapped[str | None] = mapped_column(String)
    dwelling_type: Mapped[str | None] = mapped_column(String)
    building_class: Mapped[str | None] = mapped_column(String)
    work_type: Mapped[str | None] = mapped_column(String)
    occupancy_class: Mapped[str | None] = mapped_column(String)
    new_or_existing: Mapped[str | None] = mapped_column(String)
    lot_type: Mapped[str | None] = mapped_column(String)
    primary_street_confirmed: Mapped[bool | None] = mapped_column(Boolean)
    secondary_street_confirmed: Mapped[bool | None] = mapped_column(Boolean)
    source: Mapped[str] = mapped_column(String, default="user_confirmed", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class SpatialDataset(Base, TimestampMixin):
    __tablename__ = "spatial_datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("sds"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    version_label: Mapped[str | None] = mapped_column(String)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime)
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class Parcel(Base, TimestampMixin):
    __tablename__ = "parcels"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("par"))
    lot_plan: Mapped[str | None] = mapped_column(String)
    local_government: Mapped[str | None] = mapped_column(String)
    area_m2: Mapped[float | None] = mapped_column(Float)
    spatial_dataset_id: Mapped[str | None] = mapped_column(ForeignKey("spatial_datasets.id"))
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    geom_wkt: Mapped[str | None] = mapped_column(Text)


class AddressPoint(Base, TimestampMixin):
    __tablename__ = "address_points"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("apt"))
    gnaf_pid: Mapped[str | None] = mapped_column(String)
    address: Mapped[str] = mapped_column(String, nullable=False)
    lon: Mapped[float | None] = mapped_column(Float)
    lat: Mapped[float | None] = mapped_column(Float)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"))
    spatial_dataset_id: Mapped[str | None] = mapped_column(ForeignKey("spatial_datasets.id"))
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    geom_wkt: Mapped[str | None] = mapped_column(Text)


class PlanningLayerFeature(Base, TimestampMixin):
    __tablename__ = "planning_layer_features"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("plf"))
    layer_type: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str | None] = mapped_column(String)
    label: Mapped[str] = mapped_column(String, nullable=False)
    spatial_dataset_id: Mapped[str | None] = mapped_column(ForeignKey("spatial_datasets.id"))
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    geom_wkt: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class LocalGovernmentBoundary(Base, TimestampMixin):
    __tablename__ = "local_government_boundaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("lgb"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    spatial_dataset_id: Mapped[str | None] = mapped_column(ForeignKey("spatial_datasets.id"))
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    geom_wkt: Mapped[str | None] = mapped_column(Text)


class AddressProfile(Base, TimestampMixin):
    __tablename__ = "address_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ap"))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    input_address: Mapped[str] = mapped_column(String, nullable=False)
    formatted_address: Mapped[str] = mapped_column(String, nullable=False)
    resolution_status: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, default="low", nullable=False)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"))
    local_government: Mapped[str | None] = mapped_column(String)
    lot_plan: Mapped[str | None] = mapped_column(String)
    resolver_sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    dataset_version_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    issues_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    as_of_date: Mapped[str | None] = mapped_column(String)
    assessment_basis: Mapped[str] = mapped_column(String, default="current_rules", nullable=False)


class AddressFact(Base, TimestampMixin):
    __tablename__ = "address_facts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("af"))
    address_profile_id: Mapped[str] = mapped_column(ForeignKey("address_profiles.id"), nullable=False)
    fact_type: Mapped[str] = mapped_column(String, nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String, default="low", nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    spatial_dataset_id: Mapped[str | None] = mapped_column(ForeignKey("spatial_datasets.id"))
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    planning_layer_feature_id: Mapped[str | None] = mapped_column(ForeignKey("planning_layer_features.id"))
    effective_from: Mapped[str | None] = mapped_column(String)
    effective_to: Mapped[str | None] = mapped_column(String)
    stale_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_status: Mapped[str] = mapped_column(String, default="pending_review", nullable=False)


class LocalGovernmentFact(Base, TimestampMixin):
    __tablename__ = "local_government_facts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("lgf"))
    address_profile_id: Mapped[str] = mapped_column(ForeignKey("address_profiles.id"), nullable=False)
    local_government: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, default="low", nullable=False)
    spatial_dataset_id: Mapped[str | None] = mapped_column(ForeignKey("spatial_datasets.id"))
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    review_status: Mapped[str] = mapped_column(String, default="pending_review", nullable=False)


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
    review_status: Mapped[str] = mapped_column(String, default="pending_review", nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    source_document: Mapped[SourceDocument] = relationship(back_populates="versions")


class SourceArtifact(Base, TimestampMixin):
    __tablename__ = "source_artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("sart"))
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    object_key: Mapped[str | None] = mapped_column(String)
    content_sha256: Mapped[str] = mapped_column(String, nullable=False)
    parser_name: Mapped[str | None] = mapped_column(String)
    parser_version: Mapped[str | None] = mapped_column(String)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class SourceLicenceReview(Base, TimestampMixin):
    __tablename__ = "source_licence_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("slr"))
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    licence_url: Mapped[str | None] = mapped_column(String)
    allowed_use: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_storage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_redistribution: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_ai_processing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    restricted_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str] = mapped_column(String, default="system", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_status: Mapped[str] = mapped_column(String, default="pending_review", nullable=False)


class SourceSupersession(Base, TimestampMixin):
    __tablename__ = "source_supersessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ssup"))
    from_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    to_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class SourceReference(Base, TimestampMixin):
    __tablename__ = "source_references"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("sref"))
    from_source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    to_source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    to_external_citation: Mapped[str | None] = mapped_column(Text)
    relation: Mapped[str] = mapped_column(String, nullable=False)


class Clause(Base, TimestampMixin):
    __tablename__ = "clauses"
    __table_args__ = (Index("ix_clauses_source_version_clause", "source_version_id", "clause_id"),)

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


class ClauseReference(Base, TimestampMixin):
    __tablename__ = "clause_references"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("clref"))
    from_clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id"), nullable=False)
    to_clause_id: Mapped[str | None] = mapped_column(ForeignKey("clauses.id"))
    to_external_citation: Mapped[str | None] = mapped_column(Text)
    relation: Mapped[str] = mapped_column(String, nullable=False)


class ClauseDisposition(Base, TimestampMixin):
    __tablename__ = "clause_dispositions"
    __table_args__ = (Index("ix_clause_dispositions_clause_created", "clause_id", "created_at", "id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("cdisp"))
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id"), nullable=False)
    disposition: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewer: Mapped[str] = mapped_column(String, default="system", nullable=False)


class RuleExtractionCandidate(Base, TimestampMixin):
    __tablename__ = "rule_extraction_candidates"
    __table_args__ = (
        Index("ix_rule_extraction_candidates_clause_created", "clause_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rec"))
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    clause_id: Mapped[str | None] = mapped_column(ForeignKey("clauses.id"))
    rule_key: Mapped[str] = mapped_column(String, nullable=False)
    operator: Mapped[str | None] = mapped_column(String)
    value_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    unit: Mapped[str | None] = mapped_column(String)
    condition_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quote: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extractor_name: Mapped[str] = mapped_column(String, default="deterministic", nullable=False)
    extractor_version: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="candidate", nullable=False)
    review_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class RuleRow(Base, TimestampMixin):
    __tablename__ = "rule_rows"
    __table_args__ = (Index("ix_rule_rows_clause_created", "clause_id", "created_at", "id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rule"))
    rule_key: Mapped[str] = mapped_column(String, nullable=False)
    operator: Mapped[str | None] = mapped_column(String)
    value_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    unit: Mapped[str | None] = mapped_column(String)
    condition_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id"), nullable=False)
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String, default="pending_review", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)


class RuleToClause(Base, TimestampMixin):
    __tablename__ = "rule_to_clauses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rtc"))
    rule_row_id: Mapped[str] = mapped_column(ForeignKey("rule_rows.id"), nullable=False)
    clause_id: Mapped[str] = mapped_column(ForeignKey("clauses.id"), nullable=False)
    relation: Mapped[str] = mapped_column(String, default="provenance", nullable=False)


class RuleOverride(Base, TimestampMixin):
    __tablename__ = "rule_overrides"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rovr"))
    overriding_rule_id: Mapped[str] = mapped_column(ForeignKey("rule_rows.id"), nullable=False)
    overridden_rule_id: Mapped[str] = mapped_column(ForeignKey("rule_rows.id"), nullable=False)
    scope_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)


class RuleCarveout(Base, TimestampMixin):
    __tablename__ = "rule_carveouts"
    __table_args__ = (Index("ix_rule_carveouts_clause_created", "clause_id", "created_at", "id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rcar"))
    rule_row_id: Mapped[str] = mapped_column(ForeignKey("rule_rows.id"), nullable=False)
    condition_text: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    clause_id: Mapped[str | None] = mapped_column(ForeignKey("clauses.id"))


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


class SourceChunkEmbedding(Base, TimestampMixin):
    __tablename__ = "source_chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("source_chunk_id", "provider", "model"),
        Index("ix_source_chunk_embeddings_chunk", "source_chunk_id"),
        Index("ix_source_chunk_embeddings_source_version", "source_version_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("emb"))
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id"), nullable=False)
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_versions.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)


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
    as_of_date: Mapped[str] = mapped_column(String, nullable=False)
    assessment_basis: Mapped[str] = mapped_column(String, default="current_rules", nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String, default="draftcheck-wa-core-v0.1", nullable=False)
    source_version_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)


class ResolvedRule(Base, TimestampMixin):
    __tablename__ = "resolved_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("rr"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    address_profile_id: Mapped[str | None] = mapped_column(ForeignKey("address_profiles.id"))
    rule_row_id: Mapped[str | None] = mapped_column(String)
    as_of_date: Mapped[str] = mapped_column(String, nullable=False)
    assessment_basis: Mapped[str] = mapped_column(String, default="current_rules", nullable=False)
    applies_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    overridden_rule_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String, default="unsupported", nullable=False)
    citations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)


class CheckResult(Base, TimestampMixin):
    __tablename__ = "check_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("res"))
    check_run_id: Mapped[str | None] = mapped_column(ForeignKey("check_runs.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    check_key: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[str] = mapped_column(String, nullable=False)
    assessment_basis: Mapped[str] = mapped_column(String, default="current_rules", nullable=False)
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


class DecisionTrace(Base, TimestampMixin):
    __tablename__ = "decision_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("dt"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    check_result_id: Mapped[str | None] = mapped_column(ForeignKey("check_results.id"))
    inputs_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    formula: Mapped[str] = mapped_column(Text, default="", nullable=False)
    comparison: Mapped[str] = mapped_column(Text, default="", nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)
    rule_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    resolved_rule_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    measurement_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    citation_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    unit_conversions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    rounding_policy: Mapped[str] = mapped_column(String, default="no rounding before comparison", nullable=False)
    tolerance: Mapped[str | None] = mapped_column(String)
    input_sources_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    applicability_trace_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    precedence_trace_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    engine_version: Mapped[str] = mapped_column(String, default="draftcheck-compliance-v0.1", nullable=False)
    rule_snapshot_hash: Mapped[str | None] = mapped_column(String)
    measurement_snapshot_hash: Mapped[str | None] = mapped_column(String)


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


class ReviewQueueItem(Base, TimestampMixin):
    __tablename__ = "review_queue_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("revq"))
    queue: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("source_versions.id"))
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    blocking_level: Mapped[str] = mapped_column(String, default="blocking", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    assignee: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    priority: Mapped[str] = mapped_column(String, default="medium", nullable=False)


class GoldenEvalCase(Base, TimestampMixin):
    __tablename__ = "golden_eval_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("gec"))
    track: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    input_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    expected_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    source_version_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String, default="dev-user", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class GoldenEvalRun(Base, TimestampMixin):
    __tablename__ = "golden_eval_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ger"))
    track: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    case_results_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String)
    model_version: Mapped[str | None] = mapped_column(String)
    engine_version: Mapped[str] = mapped_column(String, default="draftcheck-evals-v0.1", nullable=False)
    run_by: Mapped[str] = mapped_column(String, default="dev-user", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


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

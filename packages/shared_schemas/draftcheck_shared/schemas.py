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
    "unsupported",
]

Confidence = Literal["high", "medium", "low"]
AddressResolutionStatus = Literal["resolved", "missing_info", "needs_human_review", "unsupported"]
AssessmentBasis = Literal["current_rules", "lodged_date", "custom_date"]
ReviewQueueName = Literal[
    "source_review",
    "rule_review",
    "spatial_ambiguity_review",
    "drawing_extraction_review",
    "conflict_review",
    "licence_review",
    "eval_failure_review",
]
ReviewBlockingLevel = Literal["blocking", "non_blocking", "advisory"]
ReviewQueueStatus = Literal["open", "in_progress", "resolved", "dismissed"]
EvalTrack = Literal["rule_extraction", "spatial_resolution", "retrieval", "drawing_extraction", "compliance"]


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
    review_status: Literal["accepted", "rejected", "pending_review"] = "pending_review"
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
    review_status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class ManifestImportRequest(BaseModel):
    manifest_yaml: str | None = None
    entries: list[SourceDocumentCreate] | None = None


class HermesCorpusImportRequest(BaseModel):
    inventory_jsonl: str | None = None
    inventory_path: str | None = None
    corpus_root: str | None = None
    request_acceptance: bool = False

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
    question: str = ""
    message: str | None = None
    source_filters: dict[str, Any] = Field(default_factory=dict)
    filters: dict[str, Any] | None = None
    messages: list[dict[str, Any]] | None = None

    @model_validator(mode="before")
    @classmethod
    def _accept_chat_message_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("source_filters") is None:
                data = {**data, "source_filters": {}}
            if data.get("filters") is None:
                data = {**data, "filters": None}
            if not data.get("question") and data.get("message"):
                data = {**data, "question": data["message"]}
            if not data.get("question") and isinstance(data.get("messages"), list):
                for message in reversed(data["messages"]):
                    if not isinstance(message, dict):
                        continue
                    if message.get("role") == "assistant":
                        continue
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        data = {**data, "question": content}
                        break
            if not data.get("source_filters") and data.get("filters"):
                data = {**data, "source_filters": data["filters"]}
        return data

    @model_validator(mode="after")
    def _require_question_text(self) -> "AskRequest":
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("question is required")
        return self


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
    as_of_date: str | None = None
    lodgement_date: str | None = None
    assessment_basis: AssessmentBasis = "current_rules"
    created_by: str = "dev-user"


class ProjectUpdate(BaseModel):
    project_name: str | None = None
    client_name: str | None = None
    status: str | None = None
    stage: str | None = None
    r_code_density: str | None = None
    ncc_edition: str | None = None
    as_of_date: str | None = None
    lodgement_date: str | None = None
    assessment_basis: AssessmentBasis | None = None


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
    address_profile_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectProposalUpsert(BaseModel):
    proposal_type: str | None = None
    dwelling_type: str | None = None
    building_class: str | None = None
    work_type: str | None = None
    occupancy_class: str | None = None
    new_or_existing: str | None = None
    lot_type: str | None = None
    primary_street_confirmed: bool | None = None
    secondary_street_confirmed: bool | None = None
    source: Literal["user_confirmed", "inferred_from_drawing", "imported"] = "user_confirmed"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ProjectProposalRead(ProjectProposalUpsert):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime


class AddressFactInput(BaseModel):
    fact_type: str
    value_json: dict[str, Any]
    confidence: Confidence = "low"
    method: str
    spatial_dataset_id: str | None = None
    source_version_id: str | None = None
    planning_layer_feature_id: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    review_status: str = "pending_review"


class AddressResolveRequest(BaseModel):
    address: str
    as_of_date: str | None = None
    assessment_basis: AssessmentBasis = "current_rules"
    facts: list[AddressFactInput] = Field(default_factory=list)


class AddressSuggestionRead(BaseModel):
    address: str
    formatted_address: str
    local_government: str | None = None
    lot_plan: str | None = None
    parcel_id: str | None = None
    confidence: Confidence
    source: str


class AddressFactRead(AddressFactInput):
    id: str
    address_profile_id: str
    stale_at: datetime | None = None
    created_at: datetime


class AddressProfileRead(BaseModel):
    id: str
    project_id: str | None = None
    input_address: str
    formatted_address: str
    resolution_status: AddressResolutionStatus
    confidence: Confidence
    parcel_id: str | None = None
    local_government: str | None = None
    lot_plan: str | None = None
    resolver_sources: list[str]
    dataset_version_ids: list[str]
    issues: list[str]
    as_of_date: str | None
    assessment_basis: AssessmentBasis
    facts: list[AddressFactRead] = Field(default_factory=list)
    planning: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class PropertyResolveRequest(BaseModel):
    address: str | None = None
    as_of_date: str | None = None
    assessment_basis: AssessmentBasis | None = None
    facts: list[AddressFactInput] = Field(default_factory=list)


class PropertyProfileRead(BaseModel):
    project_id: str
    property: PropertyRead | None = None
    address_profile: AddressProfileRead | None = None
    proposal: ProjectProposalRead | None = None
    issues: list[str] = Field(default_factory=list)


class ResolvedRulesRequest(BaseModel):
    address_profile_id: str | None = None
    as_of_date: str | None = None
    assessment_basis: AssessmentBasis | None = None


class ResolvedRuleRead(BaseModel):
    id: str
    project_id: str
    address_profile_id: str | None
    rule_row_id: str | None
    as_of_date: str
    assessment_basis: AssessmentBasis
    applies_reason: str
    overridden_rule_ids: list[str]
    status: CheckStatus
    citations: list[Citation]
    created_at: datetime


class ResolvedRulesResponse(BaseModel):
    project_id: str
    address_profile_id: str | None
    as_of_date: str
    assessment_basis: AssessmentBasis
    status: CheckStatus
    resolved_rules: list[ResolvedRuleRead]
    issues: list[str]


class RuleRowRead(BaseModel):
    id: str
    rule_key: str
    operator: str | None
    value: dict[str, Any]
    unit: str | None
    condition_text: str
    quote: str
    clause_id: str
    source_version_id: str
    lifecycle_status: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RuleExtractionCandidateRead(BaseModel):
    id: str
    source_version_id: str
    clause_id: str | None
    rule_key: str
    operator: str | None
    value: dict[str, Any]
    unit: str | None
    condition_text: str
    quote: str
    extractor_name: str
    extractor_version: str | None = None
    status: Literal["candidate", "pending_review", "rejected"]
    review_notes: str
    created_at: datetime
    updated_at: datetime


class RuleExtractionRunResponse(BaseModel):
    source_document_id: str
    source_version_id: str
    extractor_name: str
    extractor_version: str
    clauses_scanned: int
    dispositions_created: int
    candidates_created: int
    candidates_existing: int
    candidates: list[RuleExtractionCandidateRead]


class RuleCandidatePromotionRequest(BaseModel):
    reviewed_by: str = "dev-user"
    notes: str = ""


class RuleCandidateReviewRequest(BaseModel):
    status: Literal["candidate", "pending_review", "rejected"]
    reviewed_by: str = "dev-user"
    notes: str = ""


ClauseDispositionValue = Literal["rule_bearing", "definition", "procedural", "informational", "manual_review"]


class ClauseDispositionRead(BaseModel):
    id: str
    clause_id: str
    disposition: ClauseDispositionValue
    rationale: str
    reviewer: str
    created_at: datetime
    updated_at: datetime


class ClauseRead(BaseModel):
    id: str
    source_version_id: str
    clause_id: str
    heading: str | None = None
    parent_clause_id: str | None = None
    page_number: int | None = None
    text: str
    start_anchor: str
    end_anchor: str | None = None
    text_sha256: str
    latest_disposition: ClauseDispositionRead | None = None


class ClauseDispositionReviewRequest(BaseModel):
    disposition: ClauseDispositionValue
    rationale: str = ""
    reviewed_by: str = "dev-user"


RuleCoverageStatus = Literal[
    "covered",
    "not_rule_bearing",
    "needs_clause_disposition",
    "needs_manual_review",
    "candidate_not_promoted",
    "rule_not_approved",
    "missing_rule_row",
]


class RuleCoverageAuditItem(BaseModel):
    source_document_id: str
    source_title: str
    source_version_id: str
    version_label: str | None = None
    effective_date: str | None = None
    is_superseded: bool
    clause_row_id: str
    clause_id: str
    heading: str | None = None
    quote: str
    normative_language_detected: bool
    disposition: str | None = None
    disposition_id: str | None = None
    rule_row_ids: list[str]
    active_rule_row_ids: list[str]
    rule_lifecycle_statuses: dict[str, int]
    rule_candidate_ids: list[str]
    rule_candidate_statuses: dict[str, int]
    status: RuleCoverageStatus
    review_required: bool
    recommended_action: str


class RuleCoverageAuditResponse(BaseModel):
    source_version_id: str | None = None
    include_superseded: bool
    only_gaps: bool
    total_clauses: int
    gap_count: int
    summary: dict[str, int]
    items: list[RuleCoverageAuditItem]


NoOrphanAuditStatus = Literal[
    "ok",
    "missing_disposition",
    "invalid_informational_normative",
    "exception_language_orphan",
    "pending_rule_review",
    "quote_anchor_mismatch",
    "unclaimed_numeric_token",
]


class NoOrphanAuditItem(BaseModel):
    source_version_id: str
    clause_row_id: str
    clause_id: str
    heading: str | None = None
    quote: str
    status: NoOrphanAuditStatus
    blocking: bool
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str


class NoOrphanAuditResponse(BaseModel):
    source_version_id: str | None = None
    total_clauses: int
    blocking_count: int
    summary: dict[str, int]
    items: list[NoOrphanAuditItem]


class RuleReviewRequest(BaseModel):
    lifecycle_status: Literal["auto_accepted", "approved", "pending_review", "rejected", "stale", "superseded"]
    reviewed_by: str = "dev-user"


class SourceReviewRequest(BaseModel):
    review_status: Literal["accepted", "rejected", "pending_review"]
    source_version_id: str | None = None
    reviewed_by: str = "dev-user"
    notes: str = ""


class SourceAcceptanceGateCheck(BaseModel):
    name: str
    status: Literal["pass", "warning", "fail"]
    blocking: bool
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class SourceAcceptanceGateRead(BaseModel):
    source_document_id: str
    source_version_id: str
    review_status: str
    status: Literal["pass", "blocked"]
    can_support_retrieval: bool
    blocking_reasons: list[str]
    checks: list[SourceAcceptanceGateCheck]
    enqueued_review_item_ids: list[str] = Field(default_factory=list)


class SourceReviewQueueReconciliationRead(BaseModel):
    source_document_id: str
    source_version_id: str
    resolved_item_ids: list[str]
    still_open_item_ids: list[str]
    current_blocker_keys: list[dict[str, str]]
    gate: SourceAcceptanceGateRead


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
    decision_trace_id: str | None = None
    rule_ids: list[str] = Field(default_factory=list)
    resolved_rule_ids: list[str] = Field(default_factory=list)
    measurement_ids: list[str] = Field(default_factory=list)
    check_key: str
    label: str
    category: str
    status: CheckStatus
    as_of_date: str
    assessment_basis: AssessmentBasis
    requirement: str
    proposed: str
    evidence_refs: list[str]
    citations: list[Citation]
    assumptions: list[str]
    missing_information: list[str]
    confidence: float
    requires_human_review: bool
    created_at: datetime


class DecisionTraceRead(BaseModel):
    id: str
    project_id: str
    check_result_id: str | None
    inputs: dict[str, Any]
    formula: str
    comparison: str
    result: CheckStatus
    rule_ids: list[str]
    resolved_rule_ids: list[str]
    measurement_ids: list[str]
    citation_ids: list[dict[str, Any]]
    unit_conversions: list[dict[str, Any]]
    rounding_policy: str
    tolerance: str | None
    input_sources: list[dict[str, Any]]
    applicability_trace: dict[str, Any]
    precedence_trace: dict[str, Any]
    engine_version: str
    rule_snapshot_hash: str | None
    measurement_snapshot_hash: str | None
    created_at: datetime


class ComplianceMatrix(BaseModel):
    project_id: str
    check_run_id: str
    status: str
    as_of_date: str
    assessment_basis: AssessmentBasis
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


class ReviewQueueItemCreate(BaseModel):
    queue: ReviewQueueName
    target_type: str
    target_id: str
    reason: str
    blocking_level: ReviewBlockingLevel = "blocking"
    evidence: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str
    project_id: str | None = None
    source_version_id: str | None = None
    assignee: str | None = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"


class ReviewQueueItemPatch(BaseModel):
    status: ReviewQueueStatus | None = None
    assignee: str | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    evidence: dict[str, Any] | None = None
    suggested_action: str | None = None
    reviewed_by: str = "dev-user"


class ReviewQueueItemRead(BaseModel):
    id: str
    queue: ReviewQueueName
    project_id: str | None
    source_version_id: str | None
    target_type: str
    target_id: str
    reason: str
    blocking_level: ReviewBlockingLevel
    evidence: dict[str, Any]
    suggested_action: str
    assignee: str | None
    status: ReviewQueueStatus
    priority: str
    created_at: datetime
    updated_at: datetime


class GoldenEvalCaseCreate(BaseModel):
    track: EvalTrack
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    source_version_ids: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_by: str = "dev-user"
    notes: str = ""


class GoldenEvalCaseRead(GoldenEvalCaseCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class GoldenEvalRunRequest(BaseModel):
    track: EvalTrack | None = None
    commit_sha: str | None = None
    model_version: str | None = None
    run_by: str = "dev-user"


class GoldenEvalRunRead(BaseModel):
    id: str
    track: EvalTrack | None
    status: str
    passed: bool
    case_count: int
    passed_count: int
    failed_count: int
    metrics: dict[str, Any]
    case_results: list[dict[str, Any]]
    commit_sha: str | None
    model_version: str | None
    engine_version: str
    run_by: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OpsDashboardRead(BaseModel):
    generated_at: datetime
    sources: dict[str, Any]
    rules: dict[str, Any]
    spatial: dict[str, Any]
    jobs: dict[str, Any]
    compliance: dict[str, Any]
    evals: dict[str, Any]
    review_queues: dict[str, Any]
    backups: dict[str, Any]
    release_gate: dict[str, Any]
    issues: list[str]
    health_signals: list[str]


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

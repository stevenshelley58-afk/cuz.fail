from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.service import LIABILITY_NOTICE, ComplianceService
from draftcheck_compliance.resolved_rules import ResolvedRuleService
from draftcheck_compliance.rule_audits import RuleAuditService
from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.address_service import AddressResolutionService
from draftcheck_core.audit import list_audit_events, record_audit
from draftcheck_core.auth import get_current_auth_context
from draftcheck_core.config import get_settings
from draftcheck_core.database import get_db
from draftcheck_core.evals import GoldenEvalService
from draftcheck_core.hermes import HermesAdapter
from draftcheck_core.json_utils import from_json
from draftcheck_core.models import (
    BackgroundJob,
    CheckRun,
    CheckResult,
    DecisionTrace,
    HumanSignoff,
    Project,
    ProjectDocument,
    ReviewQueueItem,
    SourceDocument,
    SourceVersion,
)
from draftcheck_core.object_storage import get_upload_storage
from draftcheck_core.ops import OpsDashboardService
from draftcheck_core.project_service import ProjectService, property_to_dict
from draftcheck_core.review_queue import ReviewQueueService
from draftcheck_core.source_governance import SourceGovernanceService
from draftcheck_document_ai.rfi import RfiService
from draftcheck_document_ai.extraction import extract_pages_from_bytes, extract_text_from_bytes
from draftcheck_document_ai.service import DocumentAnalysisService
from draftcheck_document_ai.upload_security import (
    safe_upload_filename,
    upload_object_key,
    validate_uploaded_document,
)
from draftcheck_export.service import ExportService
from draftcheck_ingestion.service import SourceIngestionService
from draftcheck_retrieval.chat import GroundedChatService
from draftcheck_retrieval.service import RetrievalService
from draftcheck_scraper.lawful_fetcher import fetch_public_content
from draftcheck_shared.schemas import (
    AskRequest,
    ChatReply,
    AddressProfileRead,
    AddressResolveRequest,
    AddressSuggestionRead,
    CheckResultRead,
    ClauseDispositionReviewRequest,
    ClauseRead,
    DecisionTraceRead,
    DocumentCreate,
    DocumentRead,
    ExportManifest,
    ExportRequest,
    GoldenEvalCaseCreate,
    GoldenEvalCaseRead,
    GoldenEvalRunRead,
    GoldenEvalRunRequest,
    HermesCorpusImportRequest,
    JobStatus,
    ManifestImportRequest,
    MeasurementCreate,
    NoOrphanAuditResponse,
    OpsDashboardRead,
    ProjectCreate,
    ProjectProposalRead,
    ProjectProposalUpsert,
    ProjectRead,
    ProjectUpdate,
    PropertyProfileRead,
    PropertyRead,
    PropertyResolveRequest,
    PropertyUpsert,
    ResolvedRulesRequest,
    ResolvedRulesResponse,
    ResponseDraftRead,
    RfiItemRead,
    RfiParseRequest,
    RuleCandidatePromotionRequest,
    RuleCandidateReviewRequest,
    RuleCoverageAuditResponse,
    RuleExtractionCandidateRead,
    RuleExtractionRunResponse,
    RuleReviewRequest,
    RuleRowRead,
    ReviewQueueItemCreate,
    ReviewQueueItemPatch,
    ReviewQueueItemRead,
    SignoffCreate,
    SourceAcceptanceGateRead,
    SourceChunkResult,
    SourceDocumentCreate,
    SourceDocumentRead,
    SourceReviewQueueReconciliationRead,
    SourceReviewRequest,
    SourceVersionRead,
    StandardAnswer,
)

router = APIRouter()

CHECK_STATUSES = {
    "likely_pass",
    "likely_fail",
    "missing_info",
    "needs_human_review",
    "not_applicable",
    "unsupported",
}
PATCHABLE_CHECK_STATUSES = {"missing_info", "needs_human_review", "unsupported"}


@router.post("/auth/dev-login")
def dev_login() -> dict[str, Any]:
    settings = get_settings()
    if settings.require_durable_database or settings.require_durable_object_storage:
        raise HTTPException(status_code=404, detail="Development login is disabled for durable deployments")
    return {"access_token": "dev-token", "token_type": "bearer", "user": {"id": "dev-user", "role": "designer"}}


@router.get("/me")
def me() -> dict[str, str]:
    return {"id": "dev-user", "email": "dev@example.local", "role": "designer"}


@router.post("/address/resolve", response_model=AddressProfileRead)
def resolve_address(payload: AddressResolveRequest, db: Session = Depends(get_db)) -> AddressProfileRead:
    profile = AddressResolutionService(db).resolve_address(payload)
    db.commit()
    return profile


@router.get("/address/autocomplete", response_model=list[AddressSuggestionRead])
@router.get("/address/suggestions", response_model=list[AddressSuggestionRead])
def autocomplete_address(
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[AddressSuggestionRead]:
    return AddressResolutionService(db).suggest_addresses(q, limit=limit)


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    project = ProjectService(db).create_project(payload)
    db.commit()
    return _project_read(project)


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return [_project_read(project) for project in ProjectService(db).list_projects()]


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectRead:
    return _project_read(ProjectService(db).get_project(project_id))


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)) -> ProjectRead:
    project = ProjectService(db).update_project(project_id, payload)
    db.commit()
    return _project_read(project)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    ProjectService(db).delete_project(project_id)
    db.commit()
    return {"status": "deleted"}


@router.put("/projects/{project_id}/property", response_model=PropertyRead)
def upsert_property(project_id: str, payload: PropertyUpsert, db: Session = Depends(get_db)) -> dict:
    prop = ProjectService(db).upsert_property(project_id, payload)
    db.commit()
    return property_to_dict(prop)


@router.get("/projects/{project_id}/property", response_model=PropertyRead | None)
def get_property(project_id: str, db: Session = Depends(get_db)) -> dict | None:
    prop = ProjectService(db).get_property(project_id)
    return property_to_dict(prop) if prop else None


@router.post("/projects/{project_id}/property/resolve", response_model=PropertyProfileRead)
def resolve_project_property(
    project_id: str,
    payload: PropertyResolveRequest | None = None,
    db: Session = Depends(get_db),
) -> PropertyProfileRead:
    ProjectService(db).get_project(project_id)
    profile = AddressResolutionService(db).resolve_project_property(
        project_id,
        payload or PropertyResolveRequest(),
    )
    db.commit()
    return profile


@router.get("/projects/{project_id}/property/profile", response_model=PropertyProfileRead)
def get_property_profile(project_id: str, db: Session = Depends(get_db)) -> PropertyProfileRead:
    ProjectService(db).get_project(project_id)
    return AddressResolutionService(db).property_profile(project_id)


@router.put("/projects/{project_id}/proposal", response_model=ProjectProposalRead)
def upsert_project_proposal(
    project_id: str,
    payload: ProjectProposalUpsert,
    db: Session = Depends(get_db),
) -> ProjectProposalRead:
    proposal = ProjectService(db).upsert_proposal(project_id, payload)
    db.commit()
    return _proposal_read(proposal)


@router.get("/projects/{project_id}/proposal", response_model=ProjectProposalRead | None)
def get_project_proposal(project_id: str, db: Session = Depends(get_db)) -> ProjectProposalRead | None:
    proposal = ProjectService(db).get_proposal(project_id)
    return _proposal_read(proposal) if proposal else None


@router.post("/projects/{project_id}/documents", response_model=DocumentRead)
def add_document(project_id: str, payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentRead:
    doc = ProjectService(db).add_document(project_id, payload)
    if payload.text_content:
        DocumentAnalysisService(db).extract_facts_for_document(project_id, doc.id)
    db.commit()
    return _document_read(doc)


@router.post("/projects/{project_id}/documents/upload", response_model=DocumentRead)
async def upload_document(
    project_id: str,
    document_type: str = Form(...),
    title: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    ProjectService(db).get_project(project_id)
    settings = get_settings()
    content = await file.read(settings.upload_max_bytes + 1)
    filename = safe_upload_filename(file.filename)
    validated = validate_uploaded_document(
        content,
        declared_content_type=file.content_type or "application/octet-stream",
        filename=filename,
        max_bytes=settings.upload_max_bytes,
    )
    content_type = validated.content_type
    stored = get_upload_storage().put_bytes(
        upload_object_key(project_id=project_id, filename=filename, content=validated.content),
        validated.content,
    )
    extraction_content_type = f"{content_type}; filename={filename}"
    pages = extract_pages_from_bytes(validated.content, extraction_content_type)
    doc = ProjectService(db).add_extracted_document(
        project_id,
        document_type=document_type,
        title=title or filename,
        filename=filename,
        content_type=content_type,
        raw_object_key=stored.object_key,
        content_sha256=stored.content_sha256,
        pages=pages,
        metadata={
            "byte_size": stored.byte_size,
            "upload_filename": filename,
            "detected_content_type": validated.detected_type,
        },
    )
    DocumentAnalysisService(db).extract_facts_for_document(project_id, doc.id)
    db.commit()
    return _document_read(doc)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
def list_documents(project_id: str, db: Session = Depends(get_db)) -> list[DocumentRead]:
    return [_document_read(doc) for doc in ProjectService(db).list_documents(project_id)]


@router.get("/projects/{project_id}/documents/{document_id}", response_model=DocumentRead)
def get_document(project_id: str, document_id: str, db: Session = Depends(get_db)) -> DocumentRead:
    return _document_read(ProjectService(db).get_document(project_id, document_id))


@router.post("/projects/{project_id}/documents/{document_id}/analyze", response_model=list[CheckResultRead])
def analyze_document(project_id: str, document_id: str, db: Session = Depends(get_db)) -> list[CheckResultRead]:
    ProjectService(db).get_document(project_id, document_id)
    rows = DocumentAnalysisService(db).analyze_document(project_id, document_id)
    db.commit()
    return [_check_result_read(row) for row in rows]


@router.get("/projects/{project_id}/documents/{document_id}/pages")
def document_pages(project_id: str, document_id: str, db: Session = Depends(get_db)) -> list[dict]:
    ProjectService(db).get_document(project_id, document_id)
    return DocumentAnalysisService(db).pages_for_document(project_id, document_id)


@router.get("/projects/{project_id}/documents/{document_id}/facts")
def document_facts(project_id: str, document_id: str, db: Session = Depends(get_db)) -> list[dict]:
    ProjectService(db).get_document(project_id, document_id)
    return DocumentAnalysisService(db).list_facts(project_id, document_id)


@router.get("/projects/{project_id}/document-search")
def search_project_documents(
    project_id: str,
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict]:
    ProjectService(db).get_project(project_id)
    return DocumentAnalysisService(db).search_project_documents(project_id, q, limit)


@router.post("/sources/manifest/import")
def import_manifest(payload: ManifestImportRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = SourceIngestionService(db)
    if payload.manifest_yaml:
        results = service.import_manifest_yaml(payload.manifest_yaml)
    else:
        results = service.import_entries(payload.entries or [])
    db.commit()
    return {"results": [result.__dict__ for result in results]}


@router.post("/sources/hermes-corpus/import")
def import_hermes_corpus(payload: HermesCorpusImportRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    inventory_jsonl = payload.inventory_jsonl
    corpus_root = Path(payload.corpus_root).expanduser().resolve() if payload.corpus_root else None
    if payload.inventory_path:
        inventory_path = Path(payload.inventory_path).expanduser().resolve()
        try:
            inventory_jsonl = inventory_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise HTTPException(status_code=400, detail=f"Unable to read inventory_path: {exc}") from exc
        corpus_root = corpus_root or inventory_path.parent

    result = SourceIngestionService(db).import_hermes_corpus(
        inventory_jsonl=inventory_jsonl or "",
        corpus_root=corpus_root,
        request_acceptance=payload.request_acceptance,
    )
    db.commit()
    return result.to_dict()


@router.post("/sources/seed")
def seed_source(payload: SourceDocumentCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = SourceIngestionService(db).ingest_source(payload)
    db.commit()
    return result.__dict__


@router.post("/sources/ingest")
async def ingest_source(payload: SourceDocumentCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.canonical_url and not payload.content:
        if not payload.scrape_allowed:
            raise HTTPException(status_code=400, detail="scrape_allowed is false for this source")
        fetched = await fetch_public_content(
            payload.canonical_url,
            licence_notes=payload.licence_notes,
            access_type=payload.access_type,
        )
        extracted_text = extract_text_from_bytes(fetched.content, fetched.content_type)
        payload = payload.model_copy(update={"content": extracted_text})
    result = SourceIngestionService(db).ingest_source(payload)
    db.commit()
    return result.__dict__


@router.get("/sources", response_model=list[SourceDocumentRead])
def list_sources(db: Session = Depends(get_db)) -> list[SourceDocumentRead]:
    sources = db.scalars(select(SourceDocument).order_by(SourceDocument.title)).all()
    return [_source_read(source) for source in sources]


@router.get("/sources/fetch-logs")
def fetch_logs(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(BackgroundJob).order_by(BackgroundJob.created_at.desc())).all()
    return [{"id": row[0].id, "job_type": row[0].job_type, "status": row[0].status} for row in rows]


@router.get("/sources/{source_id}", response_model=SourceDocumentRead)
def get_source(source_id: str, db: Session = Depends(get_db)) -> SourceDocumentRead:
    source = db.get(SourceDocument, source_id)
    if not source:
        raise KeyError("Source not found")
    return _source_read(source)


@router.get("/sources/{source_id}/versions", response_model=list[SourceVersionRead])
def source_versions(source_id: str, db: Session = Depends(get_db)) -> list[SourceVersionRead]:
    versions = db.scalars(
        select(SourceVersion)
        .where(SourceVersion.source_document_id == source_id)
        .order_by(SourceVersion.retrieved_at.desc())
    ).all()
    return [_version_read(version) for version in versions]


@router.get(
    "/sources/{source_id}/versions/{source_version_id}/acceptance-gate",
    response_model=SourceAcceptanceGateRead,
)
def source_acceptance_gate(
    source_id: str,
    source_version_id: str,
    enqueue_review_items: bool = False,
    db: Session = Depends(get_db),
) -> SourceAcceptanceGateRead:
    result = SourceGovernanceService(db).acceptance_gate(
        source_id,
        source_version_id,
        enqueue_review_items=enqueue_review_items,
    )
    if enqueue_review_items:
        db.commit()
    return result


@router.post(
    "/sources/{source_id}/versions/{source_version_id}/review-queue/reconcile",
    response_model=SourceReviewQueueReconciliationRead,
)
def reconcile_source_version_review_queue(
    source_id: str,
    source_version_id: str,
    reviewed_by: str = "dev-user",
    db: Session = Depends(get_db),
) -> SourceReviewQueueReconciliationRead:
    result = SourceGovernanceService(db).reconcile_source_version_review_queue(
        source_id,
        source_version_id,
        reviewed_by=reviewed_by,
    )
    db.commit()
    return result


@router.post(
    "/sources/{source_id}/versions/{source_version_id}/rules/extract",
    response_model=RuleExtractionRunResponse,
)
def extract_source_version_rules(
    source_id: str,
    source_version_id: str,
    db: Session = Depends(get_db),
) -> RuleExtractionRunResponse:
    result = RuleGovernanceService(db).extract_source_version_rules(
        source_version_id,
        source_document_id=source_id,
    )
    db.commit()
    return result


@router.post("/sources/{source_id}/review", response_model=SourceAcceptanceGateRead)
def review_source_version(
    source_id: str,
    payload: SourceReviewRequest,
    db: Session = Depends(get_db),
) -> SourceAcceptanceGateRead:
    result = SourceGovernanceService(db).review_source(source_id, payload)
    db.commit()
    return result


@router.post("/sources/{source_id}/refresh", response_model=JobStatus)
def refresh_source(source_id: str, db: Session = Depends(get_db)) -> JobStatus:
    source = db.get(SourceDocument, source_id)
    if not source:
        raise KeyError("Source not found")
    job = HermesAdapter(db).enqueue_source_freshness_audit({"source_document_id": source_id, "url": source.canonical_url})
    db.commit()
    return job


@router.get("/source-chunks/search", response_model=list[SourceChunkResult])
def search_chunks(q: str = Query(...), db: Session = Depends(get_db)) -> list[SourceChunkResult]:
    return RetrievalService(db).search(q)


@router.post("/checks/definitions/import")
def import_check_definitions(payload: dict[str, str], db: Session = Depends(get_db)) -> dict[str, Any]:
    yaml_text = payload.get("manifest_yaml") or payload.get("yaml") or ""
    definitions = ComplianceService(db).load_check_definitions_yaml(yaml_text)
    db.commit()
    return {"imported": len(definitions), "keys": [definition.key for definition in definitions]}


@router.get("/rules", response_model=list[RuleRowRead])
def list_rule_rows(
    source_version_id: str | None = None,
    lifecycle_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[RuleRowRead]:
    return RuleGovernanceService(db).list_rule_rows(
        source_version_id=source_version_id,
        lifecycle_status=lifecycle_status,
    )


@router.get("/clauses/{clause_row_id}", response_model=ClauseRead)
def get_clause(
    clause_row_id: str,
    db: Session = Depends(get_db),
) -> ClauseRead:
    return RuleGovernanceService(db).get_clause(clause_row_id)


@router.post("/clauses/{clause_row_id}/disposition", response_model=ClauseRead)
def review_clause_disposition(
    clause_row_id: str,
    payload: ClauseDispositionReviewRequest,
    db: Session = Depends(get_db),
) -> ClauseRead:
    result = RuleGovernanceService(db).review_clause_disposition(clause_row_id, payload)
    db.commit()
    return result


@router.get("/rules/candidates", response_model=list[RuleExtractionCandidateRead])
def list_rule_candidates(
    source_version_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[RuleExtractionCandidateRead]:
    return RuleGovernanceService(db).list_rule_candidates(
        source_version_id=source_version_id,
        status=status,
    )


@router.post("/rules/candidates/{candidate_id}/promote", response_model=RuleRowRead)
def promote_rule_candidate(
    candidate_id: str,
    payload: RuleCandidatePromotionRequest | None = None,
    db: Session = Depends(get_db),
) -> RuleRowRead:
    result = RuleGovernanceService(db).promote_rule_candidate(
        candidate_id,
        payload or RuleCandidatePromotionRequest(),
    )
    db.commit()
    return result


@router.post("/rules/candidates/{candidate_id}/review", response_model=RuleExtractionCandidateRead)
def review_rule_candidate(
    candidate_id: str,
    payload: RuleCandidateReviewRequest,
    db: Session = Depends(get_db),
) -> RuleExtractionCandidateRead:
    result = RuleGovernanceService(db).review_rule_candidate(candidate_id, payload)
    db.commit()
    return result


@router.get("/rules/coverage-audit", response_model=RuleCoverageAuditResponse)
def audit_rule_coverage(
    source_version_id: str | None = None,
    include_superseded: bool = False,
    only_gaps: bool = True,
    db: Session = Depends(get_db),
) -> RuleCoverageAuditResponse:
    return RuleGovernanceService(db).coverage_audit(
        source_version_id=source_version_id,
        include_superseded=include_superseded,
        only_gaps=only_gaps,
    )


@router.get("/rules/no-orphan-audit", response_model=NoOrphanAuditResponse)
def audit_rule_orphans(
    source_version_id: str | None = None,
    db: Session = Depends(get_db),
) -> NoOrphanAuditResponse:
    return RuleAuditService(db).no_orphan_audit(source_version_id=source_version_id)


@router.post("/rules/{rule_row_id}/review", response_model=RuleRowRead)
def review_rule_row(
    rule_row_id: str,
    payload: RuleReviewRequest,
    db: Session = Depends(get_db),
) -> RuleRowRead:
    result = RuleGovernanceService(db).review_rule_row(rule_row_id, payload)
    db.commit()
    return result


@router.post("/ask-source-library", response_model=StandardAnswer)
def ask_source_library(payload: AskRequest, db: Session = Depends(get_db)) -> StandardAnswer:
    return RetrievalService(db).ask(payload.question, payload.source_filters)


@router.post("/ask", response_model=StandardAnswer)
@router.post("/chat", response_model=StandardAnswer)
def ask_chat(payload: AskRequest, db: Session = Depends(get_db)) -> StandardAnswer:
    return RetrievalService(db).ask(payload.question, payload.source_filters)


@router.post("/projects/{project_id}/ask-source", response_model=StandardAnswer)
def ask_project_source(project_id: str, payload: AskRequest, db: Session = Depends(get_db)) -> StandardAnswer:
    project = ProjectService(db).get_project(project_id)
    return RetrievalService(db).ask(payload.question, _project_source_filters(project, payload))


@router.post("/assistant", response_model=ChatReply)
def assistant_chat(payload: AskRequest, db: Session = Depends(get_db)) -> ChatReply:
    """Grounded conversational assistant.

    Uses the configured chat model, grounded in approved sources when relevant
    chunks exist; otherwise a general helpful reply (never inventing regulatory
    specifics). Falls back to the deterministic engine when no live model is set.
    """
    return GroundedChatService(db).reply(payload.question, payload.source_filters)


@router.post("/projects/{project_id}/assistant", response_model=ChatReply)
def assistant_project_chat(
    project_id: str, payload: AskRequest, db: Session = Depends(get_db)
) -> ChatReply:
    project = ProjectService(db).get_project(project_id)
    return GroundedChatService(db).reply(payload.question, _project_source_filters(project, payload))


@router.post("/projects/{project_id}/ask", response_model=StandardAnswer)
@router.post("/projects/{project_id}/chat", response_model=StandardAnswer)
def ask_project_chat(project_id: str, payload: AskRequest, db: Session = Depends(get_db)) -> StandardAnswer:
    project = ProjectService(db).get_project(project_id)
    return _project_context_chat_answer(project, payload, db)


def _project_source_filters(project: Project, payload: AskRequest) -> dict[str, Any]:
    filters = dict(payload.source_filters or {})
    filters.setdefault("local_government", project.local_government)
    return filters


def _project_context_chat_answer(project: Project, payload: AskRequest, db: Session) -> StandardAnswer:
    results = ComplianceService(db).list_latest_run_results(project.id)
    matched = _matching_project_check_results(payload.question, results)
    if matched:
        return _targeted_project_check_answer(matched)

    if not results:
        if not _looks_like_project_status_question(payload.question):
            return _project_source_library_chat_answer(
                project,
                payload,
                db,
                deterministic_missing=[
                    "No completed compliance run exists for this project.",
                    "The cited source-library result has not verified this project's facts, measurements, or drawings.",
                ],
            )
        return StandardAnswer(
            answer=(
                "No completed deterministic compliance run exists for this project yet. "
                "Resolve the address/profile, confirm proposal facts, add measurements, approve applicable "
                "resolved rules, then run project checks before treating chat as project-specific evidence."
            ),
            citations=[],
            source_version_ids=[],
            assumptions=[
                "Project chat can only summarize stored deterministic project evidence.",
                "Human signoff is required before any export is treated as submission-ready.",
            ],
            missing_information=[
                "No completed compliance run exists for this project.",
                "Resolved address/profile, proposal facts, measurements, and approved resolved rules are required.",
            ],
            confidence=0.0,
            human_review_required=True,
            risk_level="high",
            status="missing_info",
        )

    if not _looks_like_project_status_question(payload.question):
        return _project_source_library_chat_answer(
            project,
            payload,
            db,
            deterministic_missing=[
                "No matching deterministic check result was found for the question.",
                "The cited source-library result has not been evaluated against the latest project compliance run.",
            ],
        )

    return _project_compliance_summary_answer(results)


def _project_source_library_chat_answer(
    project: Project,
    payload: AskRequest,
    db: Session,
    *,
    deterministic_missing: list[str],
) -> StandardAnswer:
    source_answer = RetrievalService(db).ask(payload.question, _project_source_filters(project, payload))
    if source_answer.citations:
        answer = (
            "Source-library result for this project scope, not a deterministic project compliance result:\n"
            f"{source_answer.answer}"
        )
    else:
        answer = (
            "No deterministic project evidence matched this question. "
            "The approved source library also cannot support a cited answer:\n"
            f"{source_answer.answer}"
        )
    return StandardAnswer(
        answer=answer,
        citations=source_answer.citations,
        source_version_ids=source_answer.source_version_ids,
        assumptions=_unique_chat_items(
            [
                "Project source lookup is scoped by the project local government where available.",
                "This answer does not verify project facts, measurements, drawings, approvals, or council interpretation.",
                *source_answer.assumptions,
                "Human signoff is required before any export is treated as submission-ready.",
            ]
        ),
        missing_information=_unique_chat_items(
            [
                *deterministic_missing,
                *source_answer.missing_information,
                "Run deterministic project checks before treating this as project-specific evidence.",
                "Human signoff is required before any export is treated as submission-ready.",
            ]
        ),
        confidence=source_answer.confidence,
        human_review_required=True,
        risk_level=source_answer.risk_level,
        status=source_answer.status,
    )


def _looks_like_project_status_question(question: str) -> bool:
    lowered = question.lower()
    tokens = set(_chat_tokens(question))
    if re.search(r"\b(?:my|our)\b", lowered):
        return True
    if tokens & {
        "allow",
        "allowed",
        "approval",
        "approved",
        "build",
        "comply",
        "complies",
        "fail",
        "pass",
        "permit",
    }:
        return True
    return any(
        marker in lowered
        for marker in [
            "application",
            "check",
            "checks",
            "compliance",
            "complies",
            "comply",
            "design",
            "drawing",
            "drawings",
            "issue",
            "issues",
            "project",
            "proposal",
            "result",
            "results",
            "status",
            "submission",
        ]
    )


def _matching_project_check_results(
    question: str,
    results: list[CheckResultRead],
) -> list[CheckResultRead]:
    lowered = _normalized_chat_text(question)
    tokens = set(_chat_tokens(question))
    matched: list[CheckResultRead] = []
    for result in results:
        labels = {
            _normalized_chat_text(result.check_key.replace("_", " ")),
            _normalized_chat_text(result.label),
        }
        if any(label and label in lowered for label in labels):
            matched.append(result)
            continue
        key_tokens = set(_chat_tokens(result.check_key.replace("_", " ")))
        label_tokens = set(_chat_tokens(result.label))
        if key_tokens and key_tokens.issubset(tokens):
            matched.append(result)
            continue
        if label_tokens and label_tokens.issubset(tokens):
            matched.append(result)
    return matched


def _targeted_project_check_answer(results: list[CheckResultRead]) -> StandardAnswer:
    if len(results) == 1:
        result = results[0]
        lines = [
            f"Latest deterministic compliance run result for {result.label}: {result.status}.",
            f"Requirement: {result.requirement or 'not available'}.",
            f"Proposed: {result.proposed or 'not evaluated'}.",
        ]
        if result.decision_trace_id:
            lines.append(f"Decision trace: {result.decision_trace_id}.")
        if result.evidence_refs:
            lines.append(f"Evidence refs: {'; '.join(result.evidence_refs[:5])}.")
        if result.missing_information:
            lines.append(f"Missing information: {'; '.join(result.missing_information[:5])}.")
        lines.append(
            "This does not assert final compliance; human signoff is required before submission use."
        )
        citations = list(result.citations)
        return StandardAnswer(
            answer="\n".join(lines),
            citations=citations,
            source_version_ids=_source_version_ids(citations),
            assumptions=[
                "This answer summarizes the latest stored deterministic check result only.",
                "Human signoff is required before any export is treated as submission-ready.",
            ],
            missing_information=_project_answer_missing_information(result.missing_information),
            confidence=result.confidence,
            human_review_required=True,
            risk_level=_risk_level_for_results(results),
            status=result.status,
        )

    return _project_compliance_summary_answer(results, heading="Matching latest deterministic check results")


def _project_compliance_summary_answer(
    results: list[CheckResultRead],
    *,
    heading: str = "The latest deterministic compliance run does not establish final project compliance",
) -> StandardAnswer:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    summary = ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))
    blocking = sorted(
        [
            result
            for result in results
            if result.status in {"likely_fail", "missing_info", "needs_human_review", "unsupported"}
        ],
        key=lambda result: (_project_status_priority(result.status), result.label),
    )[:5]
    lines = [
        f"{heading}.",
        f"Latest status counts: {summary}.",
    ]
    if blocking:
        lines.append("Key blocking items:")
        lines.extend(f"- {result.label}: {result.status} ({_first_missing_or_proposed(result)})" for result in blocking)
    lines.append("Human signoff is required before any export is treated as submission-ready.")

    cited_results = blocking if blocking else results
    citations = _dedupe_project_chat_citations(cited_results)
    return StandardAnswer(
        answer="\n".join(lines),
        citations=citations,
        source_version_ids=_source_version_ids(citations),
        assumptions=[
            "This answer summarizes the latest stored deterministic compliance run only.",
            "Project-specific facts, measurements, and approved resolved rules remain authoritative over chat text.",
        ],
        missing_information=_project_summary_missing_information(results),
        confidence=max((result.confidence for result in results), default=0.0),
        human_review_required=True,
        risk_level=_risk_level_for_results(results),
        status=_summary_status(results),
    )


def _first_missing_or_proposed(result: CheckResultRead) -> str:
    if result.missing_information:
        return result.missing_information[0]
    return result.proposed or "not evaluated"


def _combined_missing_information(results: list[CheckResultRead]) -> list[str]:
    combined: list[str] = []
    seen: set[str] = set()
    for result in results:
        for item in result.missing_information:
            if item in seen:
                continue
            seen.add(item)
            combined.append(item)
            if len(combined) >= 12:
                return combined
    return combined


def _project_summary_missing_information(results: list[CheckResultRead]) -> list[str]:
    combined = _combined_missing_information(results)
    if combined:
        return combined
    return _project_answer_missing_information([])


def _project_answer_missing_information(items: list[str]) -> list[str]:
    missing = list(items)
    signoff_requirement = "Human signoff is required before any export is treated as submission-ready."
    if signoff_requirement not in missing:
        missing.append(signoff_requirement)
    return missing


def _unique_chat_items(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _dedupe_project_chat_citations(results: list[CheckResultRead]) -> list[Any]:
    citations: list[Any] = []
    seen: set[tuple[Any, ...]] = set()
    for result in results:
        for citation in result.citations:
            key = (
                _citation_value(citation, "source_version_id"),
                _citation_value(citation, "clause_id"),
                _citation_value(citation, "heading"),
                _citation_value(citation, "page_number"),
            )
            if key in seen:
                continue
            seen.add(key)
            citations.append(citation)
    return citations


def _source_version_ids(citations: list[Any]) -> list[str]:
    return sorted(
        {
            str(source_version_id)
            for citation in citations
            if (source_version_id := _citation_value(citation, "source_version_id"))
        }
    )


def _citation_value(citation: Any, field: str) -> Any:
    if isinstance(citation, dict):
        return citation.get(field)
    return getattr(citation, field, None)


def _summary_status(results: list[CheckResultRead]) -> str:
    statuses = {result.status for result in results}
    for status in (
        "likely_fail",
        "needs_human_review",
        "missing_info",
        "unsupported",
    ):
        if status in statuses:
            return status
    return "needs_human_review"


def _risk_level_for_results(results: list[CheckResultRead]) -> str:
    statuses = {result.status for result in results}
    if statuses & {"likely_fail", "missing_info", "unsupported"}:
        return "high"
    return "medium"


def _project_status_priority(status: str) -> int:
    return {
        "likely_fail": 0,
        "needs_human_review": 1,
        "missing_info": 2,
        "unsupported": 3,
        "likely_pass": 4,
        "not_applicable": 5,
    }.get(status, 6)


def _normalized_chat_text(text_value: str) -> str:
    return " ".join(_chat_tokens(text_value))


def _chat_tokens(text_value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text_value.lower())


@router.post("/projects/{project_id}/resolved-rules", response_model=ResolvedRulesResponse)
def resolve_project_rules(
    project_id: str,
    payload: ResolvedRulesRequest,
    db: Session = Depends(get_db),
) -> ResolvedRulesResponse:
    ProjectService(db).get_project(project_id)
    result = ResolvedRuleService(db).resolve_for_project(project_id, payload)
    db.commit()
    return result


@router.post("/projects/{project_id}/compliance/run")
@router.post(
    "/projects/{project_id}/checks/run",
    deprecated=True,
)
def run_checks(project_id: str, db: Session = Depends(get_db)):
    ProjectService(db).get_project(project_id)
    matrix = ComplianceService(db).run_checks(project_id)
    db.commit()
    return matrix


@router.get("/projects/{project_id}/checks", response_model=list[CheckResultRead])
@router.get("/projects/{project_id}/compliance", response_model=list[CheckResultRead])
def list_checks(project_id: str, db: Session = Depends(get_db)) -> list[CheckResultRead]:
    ProjectService(db).get_project(project_id)
    return ComplianceService(db).list_results(project_id)


@router.get(
    "/projects/{project_id}/checks/{check_result_id}/decision-trace",
    response_model=DecisionTraceRead,
)
def get_check_decision_trace(
    project_id: str,
    check_result_id: str,
    db: Session = Depends(get_db),
) -> DecisionTraceRead:
    ProjectService(db).get_project(project_id)
    trace = ComplianceService(db).get_decision_trace(project_id, check_result_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Decision trace not found")
    return _decision_trace_read(trace)


@router.patch("/projects/{project_id}/checks/{check_result_id}", response_model=CheckResultRead)
def patch_check_result(
    project_id: str,
    check_result_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> CheckResultRead:
    ProjectService(db).get_project(project_id)
    result = db.get(CheckResult, check_result_id)
    if not result or result.project_id != project_id:
        raise KeyError("Check result not found")
    if {"status", "proposed"} & set(payload) and ComplianceService(db).get_decision_trace(project_id, check_result_id):
        raise HTTPException(
            status_code=400,
            detail="Check results with a DecisionTrace cannot be manually edited; resolve review items or rerun checks.",
        )
    if "status" in payload:
        status = payload["status"]
        if status not in CHECK_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid check status")
        if status not in PATCHABLE_CHECK_STATUSES:
            raise HTTPException(
                status_code=400,
                detail="Deterministic compliance statuses must be produced by the rule engine",
            )
        result.status = status
    if "proposed" in payload:
        result.proposed = payload["proposed"]
    record_audit(
        db,
        action="check_result.updated",
        target_type="check_result",
        target_id=result.id,
        project_id=project_id,
        metadata=payload,
    )
    db.commit()
    return _check_result_read(result)


@router.get("/projects/{project_id}/compliance/matrix")
def compliance_matrix(project_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return _compliance_matrix_payload(project_id, db)


@router.get(
    "/projects/{project_id}/compliance-matrix",
    deprecated=True,
)
def compliance_matrix_deprecated(project_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return _compliance_matrix_payload(project_id, db)


def _compliance_matrix_payload(project_id: str, db: Session) -> dict[str, Any]:
    project = ProjectService(db).get_project(project_id)
    check_run = db.scalar(
        select(CheckRun)
        .where(CheckRun.project_id == project_id)
        .order_by(CheckRun.created_at.desc())
    )
    if not check_run:
        return {
            "project_id": project_id,
            "check_run_id": None,
            "status": "not_run",
            "as_of_date": project.as_of_date or project.lodgement_date or "unknown",
            "assessment_basis": project.assessment_basis,
            "source_version_ids": [],
            "requires_human_signoff": True,
            "liability_notice": LIABILITY_NOTICE,
            "results": [],
        }
    results = [
        result.model_dump(mode="json")
        for result in ComplianceService(db).list_results_for_run(project_id, check_run.id)
    ]
    source_version_ids = sorted(
        {
            citation["source_version_id"]
            for result in results
            for citation in result.get("citations", [])
            if citation.get("source_version_id")
        }
    )
    return {
        "project_id": project_id,
        "check_run_id": check_run.id,
        "status": check_run.status,
        "as_of_date": check_run.as_of_date,
        "assessment_basis": check_run.assessment_basis,
        "source_version_ids": source_version_ids,
        "requires_human_signoff": True,
        "liability_notice": LIABILITY_NOTICE,
        "results": results,
    }


@router.post("/projects/{project_id}/measurements")
def add_measurement(project_id: str, payload: MeasurementCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    measurement = ProjectService(db).add_measurement(project_id, payload)
    db.commit()
    return {
        "id": measurement.id,
        "project_id": measurement.project_id,
        "key": measurement.key,
        "value": measurement.value,
        "unit": measurement.unit,
        "source": measurement.source,
        "confidence": measurement.confidence,
        "evidence_ref": measurement.evidence_ref,
    }


@router.get("/projects/{project_id}/measurements")
def list_measurements(project_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [
        {
            "id": measurement.id,
            "key": measurement.key,
            "value": measurement.value,
            "unit": measurement.unit,
            "source": measurement.source,
            "confidence": measurement.confidence,
            "evidence_ref": measurement.evidence_ref,
        }
        for measurement in ProjectService(db).list_measurements(project_id)
    ]


@router.post("/projects/{project_id}/rfi/parse", response_model=list[RfiItemRead])
@router.post("/projects/{project_id}/rfi/analyse", response_model=list[RfiItemRead])
def parse_rfi(project_id: str, payload: RfiParseRequest, db: Session = Depends(get_db)) -> list[RfiItemRead]:
    ProjectService(db).get_project(project_id)
    items = RfiService(db).parse_rfi(project_id, text=payload.text, document_id=payload.document_id)
    HermesAdapter(db).enqueue_rfi_analysis_job(project_id, {"rfi_item_count": len(items)})
    db.commit()
    return items


@router.get("/projects/{project_id}/rfi/items", response_model=list[RfiItemRead])
@router.get("/projects/{project_id}/rfi", response_model=list[RfiItemRead])
def list_rfi(project_id: str, db: Session = Depends(get_db)) -> list[RfiItemRead]:
    ProjectService(db).get_project(project_id)
    return RfiService(db).list_items(project_id)


@router.patch("/projects/{project_id}/rfi/items/{rfi_item_id}", response_model=RfiItemRead)
def patch_rfi(project_id: str, rfi_item_id: str, payload: dict[str, Any], db: Session = Depends(get_db)) -> RfiItemRead:
    ProjectService(db).get_project(project_id)
    item = next((row for row in RfiService(db).list_items(project_id) if row.id == rfi_item_id), None)
    if not item:
        raise KeyError("RFI item not found")
    record_audit(db, action="rfi.updated", target_type="rfi_item", target_id=rfi_item_id, project_id=project_id, metadata=payload)
    db.commit()
    return item


@router.post("/projects/{project_id}/rfi/draft-response", response_model=ResponseDraftRead)
@router.post("/projects/{project_id}/responses/generate", response_model=ResponseDraftRead)
def draft_response(project_id: str, db: Session = Depends(get_db)) -> ResponseDraftRead:
    ProjectService(db).get_project(project_id)
    draft = RfiService(db).generate_response(project_id)
    HermesAdapter(db).enqueue_council_pack_job(project_id, {"response_draft_id": draft.id})
    db.commit()
    return draft


@router.get("/projects/{project_id}/responses", response_model=list[ResponseDraftRead])
def list_responses(project_id: str, db: Session = Depends(get_db)) -> list[ResponseDraftRead]:
    ProjectService(db).get_project(project_id)
    return RfiService(db).list_responses(project_id)


@router.post("/projects/{project_id}/exports", response_model=ExportManifest)
@router.post("/projects/{project_id}/exports/response-pack", response_model=ExportManifest)
def create_export(project_id: str, payload: ExportRequest | None = None, db: Session = Depends(get_db)) -> ExportManifest:
    ProjectService(db).get_project(project_id)
    payload = payload or ExportRequest()
    export = ExportService(db).create_export(
        project_id,
        format=payload.format,
        sections=payload.sections,
        created_by=payload.created_by,
    )
    db.commit()
    return export


@router.get("/projects/{project_id}/exports", response_model=list[ExportManifest])
def list_exports(project_id: str, db: Session = Depends(get_db)) -> list[ExportManifest]:
    ProjectService(db).get_project(project_id)
    return ExportService(db).list_exports(project_id)


@router.get("/projects/{project_id}/exports/{export_id}", response_model=ExportManifest)
def get_export(project_id: str, export_id: str, db: Session = Depends(get_db)) -> ExportManifest:
    ProjectService(db).get_project(project_id)
    return ExportService(db).get_export(project_id, export_id)


@router.get("/projects/{project_id}/exports/{export_id}/download")
def download_export(project_id: str, export_id: str, db: Session = Depends(get_db)) -> Response:
    ProjectService(db).get_project(project_id)
    service = ExportService(db)
    manifest = service.get_export(project_id, export_id)
    content, filename = service.export_file_bytes(project_id, export_id)
    media_type = _export_media_type(manifest.format)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "content-disposition": f'attachment; filename="{filename}"',
            "x-draftcheck-export-id": export_id,
            "x-draftcheck-human-signoff-status": str(manifest.manifest.get("human_signoff_status", "required")),
            "x-draftcheck-submission-ready": (
                "true" if manifest.manifest.get("submission_ready") is True else "false"
            ),
        },
    )


@router.post("/projects/{project_id}/signoffs")
def create_signoff(project_id: str, payload: SignoffCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    signoff = ProjectService(db).create_signoff(project_id, payload)
    db.commit()
    return _signoff_read(signoff)


@router.get("/projects/{project_id}/signoffs")
def list_signoffs(project_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    ProjectService(db).get_project(project_id)
    rows = db.scalars(select(HumanSignoff).where(HumanSignoff.project_id == project_id)).all()
    return [_signoff_read(row) for row in rows]


@router.post("/review-queues", response_model=ReviewQueueItemRead)
def create_review_queue_item(
    payload: ReviewQueueItemCreate,
    db: Session = Depends(get_db),
) -> ReviewQueueItemRead:
    if payload.project_id:
        ProjectService(db).get_project(payload.project_id)
    elif get_current_auth_context():
        raise KeyError("Project not found")
    item = ReviewQueueService(db).enqueue(payload)
    db.commit()
    return item


@router.get("/review-queues", response_model=list[ReviewQueueItemRead])
def list_review_queue_items(
    queue: str | None = None,
    status: str | None = "open",
    project_id: str | None = None,
    source_version_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[ReviewQueueItemRead]:
    if project_id:
        ProjectService(db).get_project(project_id)
        return ReviewQueueService(db).list_items(
            queue=queue,
            status=status,
            project_id=project_id,
            source_version_id=source_version_id,
        )
    items = ReviewQueueService(db).list_items(
        queue=queue,
        status=status,
        source_version_id=source_version_id,
    )
    visible_project_ids = _tenant_visible_project_ids(db)
    if visible_project_ids is None:
        return items
    return [item for item in items if item.project_id in visible_project_ids]


@router.patch("/review-queues/{item_id}", response_model=ReviewQueueItemRead)
def update_review_queue_item(
    item_id: str,
    payload: ReviewQueueItemPatch,
    db: Session = Depends(get_db),
) -> ReviewQueueItemRead:
    item = db.get(ReviewQueueItem, item_id)
    if not item:
        raise KeyError("Review queue item not found")
    if item.project_id:
        ProjectService(db).get_project(item.project_id)
    elif get_current_auth_context():
        raise KeyError("Review queue item not found")
    item = ReviewQueueService(db).update_item(item_id, payload)
    db.commit()
    return item


@router.get("/ops/dashboard", response_model=OpsDashboardRead)
def ops_dashboard(db: Session = Depends(get_db)) -> OpsDashboardRead:
    return OpsDashboardService(db).dashboard()


@router.post("/evals/cases", response_model=GoldenEvalCaseRead)
def create_golden_eval_case(
    payload: GoldenEvalCaseCreate,
    db: Session = Depends(get_db),
) -> GoldenEvalCaseRead:
    case = GoldenEvalService(db).create_case(payload)
    db.commit()
    return case


@router.get("/evals/cases", response_model=list[GoldenEvalCaseRead])
def list_golden_eval_cases(
    track: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> list[GoldenEvalCaseRead]:
    return GoldenEvalService(db).list_cases(track=track, active_only=active_only)


@router.post("/evals/run", response_model=GoldenEvalRunRead)
def run_golden_evals(
    payload: GoldenEvalRunRequest | None = None,
    db: Session = Depends(get_db),
) -> GoldenEvalRunRead:
    run = GoldenEvalService(db).run(payload or GoldenEvalRunRequest())
    db.commit()
    return run


@router.get("/evals/runs/{run_id}", response_model=GoldenEvalRunRead)
def get_golden_eval_run(run_id: str, db: Session = Depends(get_db)) -> GoldenEvalRunRead:
    return GoldenEvalService(db).get_run(run_id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatus:
    job = HermesAdapter(db).poll_job_status(job_id)
    db.commit()
    return job


@router.post("/jobs/{job_id}/retry", response_model=JobStatus)
def retry_job(job_id: str, db: Session = Depends(get_db)) -> JobStatus:
    job = HermesAdapter(db).retry_failed_job(job_id)
    db.commit()
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> JobStatus:
    job = HermesAdapter(db).cancel_job(job_id)
    db.commit()
    return job


@router.get("/jobs/{job_id}/traces")
def job_traces(job_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return HermesAdapter(db).list_traces(job_id)


@router.get("/audit")
def audit(project_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    if project_id:
        ProjectService(db).get_project(project_id)
        return list_audit_events(db, project_id)
    visible_project_ids = _tenant_visible_project_ids(db)
    if visible_project_ids is None:
        return list_audit_events(db)
    events = [
        event
        for visible_project_id in visible_project_ids
        for event in list_audit_events(db, visible_project_id)
    ]
    return sorted(events, key=lambda event: event["created_at"], reverse=True)


def _tenant_visible_project_ids(db: Session) -> set[str] | None:
    auth_context = get_current_auth_context()
    if not auth_context:
        return None
    return set(
        db.scalars(
            select(Project.id).where(Project.created_by == auth_context.tenant_id)
        )
    )


def _project_read(project: Project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        project_name=project.project_name,
        client_name=project.client_name,
        address=project.address,
        local_government=project.local_government,
        lot_plan=project.lot_plan,
        project_type=project.project_type,
        stage=project.stage,
        r_code_density=project.r_code_density,
        ncc_edition=project.ncc_edition,
        as_of_date=project.as_of_date,
        lodgement_date=project.lodgement_date,
        assessment_basis=project.assessment_basis,  # type: ignore[arg-type]
        created_by=project.created_by,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _proposal_read(row) -> ProjectProposalRead:
    return ProjectProposalRead(
        id=row.id,
        project_id=row.project_id,
        proposal_type=row.proposal_type,
        dwelling_type=row.dwelling_type,
        building_class=row.building_class,
        work_type=row.work_type,
        occupancy_class=row.occupancy_class,
        new_or_existing=row.new_or_existing,
        lot_type=row.lot_type,
        primary_street_confirmed=row.primary_street_confirmed,
        secondary_street_confirmed=row.secondary_street_confirmed,
        source=row.source,  # type: ignore[arg-type]
        confidence=row.confidence,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _document_read(doc: ProjectDocument) -> DocumentRead:
    return DocumentRead(
        id=doc.id,
        project_id=doc.project_id,
        document_type=doc.document_type,
        title=doc.title,
        filename=doc.filename,
        content_type=doc.content_type,
        raw_object_key=doc.raw_object_key,
        parse_status=doc.parse_status,
        analysis_status=doc.analysis_status,
        content_sha256=doc.content_sha256,
        created_at=doc.created_at,
    )


def _source_read(source: SourceDocument) -> SourceDocumentRead:
    return SourceDocumentRead(
        id=source.id,
        title=source.title,
        jurisdiction=source.jurisdiction,
        authority=source.authority,
        local_government=source.local_government,
        source_type=source.source_type,
        canonical_url=source.canonical_url,
        licence_notes=source.licence_notes,
        access_type=source.access_type,
        scrape_allowed=source.scrape_allowed,
        is_active=source.is_active,
        created_at=source.created_at,
    )


def _version_read(version: SourceVersion) -> SourceVersionRead:
    return SourceVersionRead(
        id=version.id,
        source_document_id=version.source_document_id,
        version_label=version.version_label,
        effective_date=version.effective_date,
        published_date=version.published_date,
        retrieved_at=version.retrieved_at,
        content_sha256=version.content_sha256,
        is_superseded=version.is_superseded,
        parse_status=version.parse_status,
        review_status=version.review_status,
        reviewed_by=version.reviewed_by,
        reviewed_at=version.reviewed_at,
    )


def _check_result_read(row: CheckResult) -> CheckResultRead:
    return CheckResultRead(
        id=row.id,
        check_key=row.check_key,
        label=row.label,
        category=row.category,
        status=row.status,  # type: ignore[arg-type]
        as_of_date=row.as_of_date,
        assessment_basis=row.assessment_basis,  # type: ignore[arg-type]
        requirement=row.requirement,
        proposed=row.proposed,
        evidence_refs=from_json(row.evidence_refs_json, []),
        citations=from_json(row.citations_json, []),
        assumptions=from_json(row.assumptions_json, []),
        missing_information=from_json(row.missing_information_json, []),
        confidence=row.confidence,
        requires_human_review=row.requires_human_review,
        created_at=row.created_at,
    )


def _decision_trace_read(row: DecisionTrace) -> DecisionTraceRead:
    return DecisionTraceRead(
        id=row.id,
        project_id=row.project_id,
        check_result_id=row.check_result_id,
        inputs=from_json(row.inputs_json, {}),
        formula=row.formula,
        comparison=row.comparison,
        result=row.result,  # type: ignore[arg-type]
        rule_ids=from_json(row.rule_ids_json, []),
        resolved_rule_ids=from_json(row.resolved_rule_ids_json, []),
        measurement_ids=from_json(row.measurement_ids_json, []),
        citation_ids=from_json(row.citation_ids_json, []),
        unit_conversions=from_json(row.unit_conversions_json, []),
        rounding_policy=row.rounding_policy,
        tolerance=row.tolerance,
        input_sources=from_json(row.input_sources_json, []),
        applicability_trace=from_json(row.applicability_trace_json, {}),
        precedence_trace=from_json(row.precedence_trace_json, {}),
        engine_version=row.engine_version,
        rule_snapshot_hash=row.rule_snapshot_hash,
        measurement_snapshot_hash=row.measurement_snapshot_hash,
        created_at=row.created_at,
    )


def _signoff_read(row: HumanSignoff) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "status": row.status,
        "signed_by": row.signed_by,
        "notes": row.notes,
        "created_at": row.created_at,
    }


def _export_media_type(format_value: str) -> str:
    return {
        "json": "application/json",
        "csv": "text/csv",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "html": "text/html",
    }.get(format_value, "application/octet-stream")

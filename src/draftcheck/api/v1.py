"""V3 API contract surface.

PR2 freezes the `/api/v1` surface from `docs/MASTER_REBUILD_PLAN.md` section 6.1.
Product endpoints return RFC 9457-style 501 responses until their owning PR
implements them; routers mounted here replace the matching stubs as waves land.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from draftcheck.api.address import router as address_router
from draftcheck.api.auth import router as auth_router
from draftcheck.api.documents import router as documents_router
from draftcheck.api.sources import create_sources_router


contract_router = APIRouter()
router = contract_router


def create_v1_router() -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(auth_router)
    api_router.include_router(address_router)
    api_router.include_router(create_sources_router())
    api_router.include_router(documents_router)
    api_router.include_router(contract_router)
    return api_router


def _stub(name: str) -> None:
    raise NotImplementedError(f"{name} is a V3 contract stub")


@router.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "draftcheck-api", "version": "0.1.0"}


@router.get("/ready", tags=["ops"])
def ready() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "draftcheck-api",
        "checks": {"app": "ok", "config": "ok"},
    }


@router.get("/projects", tags=["projects"])
def list_projects() -> None:
    _stub("projects.list")


@router.post("/projects", tags=["projects"])
def create_project(payload: dict[str, Any]) -> None:
    _stub("projects.create")


@router.get("/projects/{project_id}", tags=["projects"])
def get_project(project_id: str) -> None:
    _stub("projects.get")


@router.patch("/projects/{project_id}", tags=["projects"])
def update_project(project_id: str, payload: dict[str, Any]) -> None:
    _stub("projects.update")


@router.delete("/projects/{project_id}", tags=["projects"])
def delete_project(project_id: str) -> None:
    _stub("projects.delete")


@router.put("/projects/{project_id}/proposal", tags=["projects"])
def put_project_proposal(project_id: str, payload: dict[str, Any]) -> None:
    _stub("projects.proposal")


@router.get("/rules/clauses", tags=["rules"])
def list_clauses() -> None:
    _stub("rules.clauses")


@router.get("/rules/clauses/{clause_id}", tags=["rules"])
def get_clause(clause_id: str) -> None:
    _stub("rules.clause")


@router.get("/rules/candidates", tags=["rules"])
def list_rule_candidates() -> None:
    _stub("rules.candidates")


@router.post("/rules/candidates/{candidate_id}/promote", tags=["rules"])
def promote_rule_candidate(candidate_id: str, payload: dict[str, Any]) -> None:
    _stub("rules.candidate_promote")


@router.post("/rules/candidates/{candidate_id}/reject", tags=["rules"])
def reject_rule_candidate(candidate_id: str, payload: dict[str, Any]) -> None:
    _stub("rules.candidate_reject")


@router.get("/rules", tags=["rules"])
def list_rules() -> None:
    _stub("rules.list")


@router.post("/rules/{rule_id}/review", tags=["rules"])
def review_rule(rule_id: str, payload: dict[str, Any]) -> None:
    _stub("rules.review")


@router.get("/rules/coverage-audit", tags=["rules"])
def rule_coverage_audit() -> None:
    _stub("rules.coverage_audit")


@router.post("/compliance/projects/{project_id}/run", tags=["compliance"])
def run_project_compliance(project_id: str, payload: dict[str, Any]) -> None:
    _stub("compliance.run")


@router.get("/compliance/projects/{project_id}/matrix", tags=["compliance"])
def get_project_compliance_matrix(project_id: str) -> None:
    _stub("compliance.matrix")


@router.post("/compliance/results/{result_id}/override", tags=["compliance"])
def override_compliance_result(result_id: str, payload: dict[str, Any]) -> None:
    _stub("compliance.override")


@router.post("/rfi/projects/{project_id}/parse", tags=["rfi"])
def parse_project_rfi(project_id: str, payload: dict[str, Any]) -> None:
    _stub("rfi.parse")


@router.get("/rfi/projects/{project_id}/items", tags=["rfi"])
def get_project_rfi_items(project_id: str) -> None:
    _stub("rfi.items")


@router.post("/rfi/items/{item_id}/draft-response", tags=["rfi"])
def draft_rfi_response(item_id: str, payload: dict[str, Any]) -> None:
    _stub("rfi.draft_response")


@router.get("/rfi/drafts/{draft_id}", tags=["rfi"])
def get_rfi_draft(draft_id: str) -> None:
    _stub("rfi.draft")


@router.post("/exports", tags=["exports"])
def create_export(payload: dict[str, Any]) -> None:
    _stub("exports.create")


@router.get("/exports", tags=["exports"])
def list_exports() -> None:
    _stub("exports.list")


@router.get("/exports/{export_id}/download", tags=["exports"])
def download_export(export_id: str) -> None:
    _stub("exports.download")


@router.post("/signoffs", tags=["signoffs"])
def create_signoff(payload: dict[str, Any]) -> None:
    _stub("signoffs.create")


@router.get("/signoffs/projects/{project_id}", tags=["signoffs"])
def list_project_signoffs(project_id: str) -> None:
    _stub("signoffs.project")


@router.get("/reviews", tags=["reviews"])
def list_reviews() -> None:
    _stub("reviews.list")


@router.post("/reviews/{review_id}/resolve", tags=["reviews"])
def resolve_review(review_id: str, payload: dict[str, Any]) -> None:
    _stub("reviews.resolve")


@router.get("/agent/jobs", tags=["agent"])
def list_agent_jobs() -> None:
    _stub("agent.jobs")


@router.post("/agent/jobs/{job_id}/retry", tags=["agent"])
def retry_agent_job(job_id: str) -> None:
    _stub("agent.job_retry")


@router.post("/agent/jobs/{job_id}/cancel", tags=["agent"])
def cancel_agent_job(job_id: str) -> None:
    _stub("agent.job_cancel")


@router.get("/agent/traces", tags=["agent"])
def list_agent_traces() -> None:
    _stub("agent.traces")


@router.get("/agent/memory", tags=["agent"])
def list_agent_memory() -> None:
    _stub("agent.memory")


@router.put("/agent/memory/{memory_id}", tags=["agent"])
def update_agent_memory(memory_id: str, payload: dict[str, Any]) -> None:
    _stub("agent.memory_update")


@router.get("/agent/skills", tags=["agent"])
def list_agent_skills() -> None:
    _stub("agent.skills")


@router.get("/agent/skills/{skill_id}/diff", tags=["agent"])
def get_agent_skill_diff(skill_id: str) -> None:
    _stub("agent.skill_diff")


@router.post("/agent/skills/{skill_id}/activate", tags=["agent"])
def activate_agent_skill(skill_id: str, payload: dict[str, Any]) -> None:
    _stub("agent.skill_activate")


@router.get("/agent/evals", tags=["agent"])
def list_agent_evals() -> None:
    _stub("agent.evals")


@router.post("/agent/evals/run", tags=["agent"])
def run_agent_evals(payload: dict[str, Any]) -> None:
    _stub("agent.evals_run")


@router.get("/ops/dashboard", tags=["ops"])
def ops_dashboard() -> None:
    _stub("ops.dashboard")


router = create_v1_router()

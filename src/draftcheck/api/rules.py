"""Read-only rules and candidates API router for Stage 3.

Invariants:
  - No approve button.  lifecycle_status='approved' is NEVER written here.
  - review endpoints only allow 'pending_review' or 'rejected'.
  - Mutation endpoints (POST .../review) verify the caller has role=owner (operator).
  - Rule INSERT is not exposed; rules are created by the extraction job only.
  - Read endpoints (GET) do not require auth so they don't shadow contract stubs.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field

from draftcheck.api.auth import get_current_session
from draftcheck.domain.identity import ActiveSession
from draftcheck.domain.rules.service import (
    get_candidate,
    get_rule,
    list_candidates,
    list_rules,
    reject_candidate,
    reject_rule,
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_version_id: UUID
    clause_id: UUID
    candidate_id: UUID | None
    rule_key: str
    rule_type: str
    pathway: str
    lifecycle_status: str
    operator: str | None
    value_json: dict[str, Any]
    unit: str | None
    condition_json: dict[str, Any]
    quote: str
    extractor_model: str | None
    skill_version_id: str | None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_version_id: UUID
    clause_id: UUID
    rule_key: str | None
    rule_type: str
    operator: str | None
    value_json: dict[str, Any]
    unit: str | None
    condition_json: dict[str, Any]
    quote: str
    confidence: float | None
    review_status: str
    extraction_group_id: UUID | None
    extraction_pass: int | None
    validator_results_json: dict[str, Any]
    auto_promoted_at: Any  # datetime | None


class CandidateReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: str = Field(
        description="Must be 'pending_review' or 'rejected'.",
        pattern="^(pending_review|rejected)$",
    )


class RuleReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lifecycle_status: str = Field(
        description="Must be 'approved' or 'rejected'.",
        pattern="^(approved|rejected)$",
    )
    reason: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _require_operator(active_session: ActiveSession) -> None:
    """Raise 403 if the session user is not an operator-level role (owner)."""
    if str(active_session.user.role) != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="operator role required",
        )


def _get_db_session():
    """Yield a SQLAlchemy session if DATABASE_URL is configured, else raise 503."""
    from draftcheck.db.engine import database_url_from_env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = database_url_from_env()
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database not configured",
        )
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=dict[str, Any])
def list_rules_endpoint(
    lifecycle_status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List rules, optionally filtered by lifecycle_status."""
    from draftcheck.db.engine import database_url_from_env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = database_url_from_env()
    if not database_url:
        return {"items": [], "count": 0}

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        rules = list_rules(db, lifecycle_status=lifecycle_status, limit=limit, offset=offset)
        items = [jsonable_encoder(RuleOut.model_validate(r)) for r in rules]
    engine.dispose()
    return {"items": items, "count": len(items)}


@router.get("/candidates", response_model=dict[str, Any])
def list_candidates_endpoint(
    clause_id: UUID | None = Query(default=None),
    review_status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List rule candidates, optionally filtered by clause_id and review_status."""
    from draftcheck.db.engine import database_url_from_env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = database_url_from_env()
    if not database_url:
        return {"items": [], "count": 0}

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        candidates = list_candidates(
            db,
            clause_id=clause_id,
            review_status=review_status,
            limit=limit,
            offset=offset,
        )
        items = [jsonable_encoder(CandidateOut.model_validate(c)) for c in candidates]
    engine.dispose()
    return {"items": items, "count": len(items)}


@router.get("/candidates/{candidate_id}", response_model=dict[str, Any])
def get_candidate_endpoint(candidate_id: UUID) -> dict[str, Any]:
    """Get a single candidate with validator_results_json and clause info."""
    from draftcheck.db.engine import database_url_from_env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = database_url_from_env()
    if not database_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database not configured")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        candidate = get_candidate(candidate_id, db)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
        out = jsonable_encoder(CandidateOut.model_validate(candidate))
        # Include clause info.
        from draftcheck.db.models import Clause

        clause = db.get(Clause, candidate.clause_id)
        if clause:
            out["clause"] = {
                "id": str(clause.id),
                "clause_key": clause.clause_key,
                "disposition": clause.disposition,
                "text": clause.text[:500],
            }
    engine.dispose()
    return out


@router.post("/candidates/{candidate_id}/review", response_model=dict[str, Any])
def review_candidate_endpoint(
    candidate_id: UUID,
    payload: CandidateReviewPayload,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Set review_status to 'pending_review' or 'rejected' (operator only)."""
    _require_operator(active_session)

    from draftcheck.db.engine import database_url_from_env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = database_url_from_env()
    if not database_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database not configured")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        candidate = get_candidate(candidate_id, db)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")

        if payload.review_status == "rejected":
            try:
                candidate = reject_candidate(
                    candidate_id=candidate_id,
                    actor_id=active_session.user.id,
                    session=db,
                )
            except PermissionError as exc:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        else:
            candidate.review_status = payload.review_status
            db.flush()

        db.commit()
        out = jsonable_encoder(CandidateOut.model_validate(candidate))
    engine.dispose()
    return out


@router.get("/clauses", include_in_schema=False)
def _clauses_stub() -> None:
    """Placeholder so /rules/clauses falls through to the contract 501 stub."""
    raise NotImplementedError("rules.clauses")


@router.get("/clauses/{clause_id}", include_in_schema=False)
def _clause_stub(clause_id: str) -> None:
    """Placeholder so /rules/clauses/{id} falls through to the contract 501 stub."""
    raise NotImplementedError("rules.clause")


@router.get("/{rule_id}", response_model=dict[str, Any])
def get_rule_endpoint(rule_id: UUID) -> dict[str, Any]:
    """Get a rule by ID with clause and source_version info."""
    from draftcheck.db.engine import database_url_from_env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = database_url_from_env()
    if not database_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database not configured")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        rule = get_rule(rule_id, db)
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")
        out = jsonable_encoder(RuleOut.model_validate(rule))
        # Include clause info.
        from draftcheck.db.models import Clause, SourceVersion

        clause = db.get(Clause, rule.clause_id)
        if clause:
            out["clause"] = {
                "id": str(clause.id),
                "clause_key": clause.clause_key,
                "disposition": clause.disposition,
                "section_ref": clause.section_ref,
            }
        source_version = db.get(SourceVersion, rule.source_version_id)
        if source_version:
            out["source_version"] = {
                "id": str(source_version.id),
                "version_label": source_version.version_label,
                "review_status": source_version.review_status,
            }
    engine.dispose()
    return out


@router.post("/{rule_id}/review", response_model=dict[str, Any])
def review_rule_endpoint(
    rule_id: UUID,
    payload: RuleReviewPayload,
    active_session: Annotated[ActiveSession, Depends(get_current_session)],
) -> dict[str, Any]:
    """Set lifecycle_status to 'approved' or 'rejected' (operator only).

    Note: 'approved' writes lifecycle_status='approved' and is the ONLY path to
    approval in this system; it requires operator (owner) role.
    """
    _require_operator(active_session)

    from draftcheck.db.engine import database_url_from_env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = database_url_from_env()
    if not database_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database not configured")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        rule = get_rule(rule_id, db)
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")

        if payload.lifecycle_status == "rejected":
            try:
                rule = reject_rule(
                    rule_id=rule_id,
                    actor_id=active_session.user.id,
                    reason=payload.reason or "",
                    session=db,
                )
            except (PermissionError, ValueError) as exc:
                code = (
                    status.HTTP_403_FORBIDDEN
                    if isinstance(exc, PermissionError)
                    else status.HTTP_422_UNPROCESSABLE_ENTITY
                )
                raise HTTPException(status_code=code, detail=str(exc)) from exc
        else:
            # approved — operator-only, requires reason for audit.
            rule.lifecycle_status = "approved"
            db.flush()

        db.commit()
        out = jsonable_encoder(RuleOut.model_validate(rule))
    engine.dispose()
    return out

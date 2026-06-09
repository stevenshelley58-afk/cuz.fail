"""Agent and eval API routes.

Endpoints:
  GET  /agent/jobs           — list job_traces, paginated
  POST /agent/jobs/{id}/retry  — re-enqueue (stub 202)
  POST /agent/jobs/{id}/cancel — cancel job (stub 202)
  GET  /agent/traces         — alias for /agent/jobs with full detail
  POST /eval/suites/{suite_name}/run — trigger EvalRunner.run_suite()
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_adapter() -> Any:
    """Return the global model adapter (lazy import to avoid circular deps)."""
    try:
        from draftcheck.providers import get_adapter  # type: ignore[attr-defined]

        return get_adapter()
    except (ImportError, AttributeError):
        from draftcheck.ai.substrate import LocalDeterministicModelAdapter

        return LocalDeterministicModelAdapter(mode="disabled")


def _get_session_factory() -> Any:
    import os

    from draftcheck.db.engine import create_runtime_engine
    from sqlalchemy.orm import sessionmaker

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None
    engine = create_runtime_engine(database_url)
    return sessionmaker(bind=engine)


# ---------------------------------------------------------------------------
# /agent/jobs
# ---------------------------------------------------------------------------


@router.get("/agent/jobs", tags=["agent"])
def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    """Return job_traces ordered by created_at desc, paginated."""
    from draftcheck.ai.substrate import InMemoryJobTraceStore

    # The global trace store is kept in the adapter; fall back to empty list
    try:
        adapter = _get_adapter()
        store: InMemoryJobTraceStore = getattr(adapter, "trace_store", None)
        traces = list(store.list_traces()) if store else []
    except Exception:
        traces = []

    traces_sorted = sorted(traces, key=lambda t: t.created_at, reverse=True)
    page = traces_sorted[offset : offset + limit]

    return JSONResponse(
        {
            "total": len(traces_sorted),
            "offset": offset,
            "limit": limit,
            "items": [
                {
                    "id": t.id,
                    "job_id": t.job_id,
                    "job_type": t.job_type,
                    "skill_version_id": t.skill_version_id,
                    "model_provider": t.model_provider,
                    "model": t.model,
                    "status": t.status,
                    "input_tokens": t.input_tokens,
                    "output_tokens": t.output_tokens,
                    "cost_cents": t.cost_cents,
                    "created_at": t.created_at.isoformat(),
                }
                for t in page
            ],
        }
    )


@router.get("/agent/traces", tags=["agent"])
def list_traces(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    """Alias for /agent/jobs with full detail."""
    return list_jobs(limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# /agent/jobs/{id}/retry  and  /agent/jobs/{id}/cancel
# ---------------------------------------------------------------------------


@router.post("/agent/jobs/{job_id}/retry", tags=["agent"])
def retry_job(job_id: str) -> JSONResponse:
    """Re-enqueue a job. Stub — returns 202 Accepted."""
    return JSONResponse(
        status_code=202,
        content={"accepted": True, "job_id": job_id, "action": "retry"},
    )


@router.post("/agent/jobs/{job_id}/cancel", tags=["agent"])
def cancel_job(job_id: str) -> JSONResponse:
    """Cancel a job. Stub — returns 202 Accepted."""
    return JSONResponse(
        status_code=202,
        content={"accepted": True, "job_id": job_id, "action": "cancel"},
    )


# ---------------------------------------------------------------------------
# /eval/suites/{suite_name}/run
# ---------------------------------------------------------------------------


@router.post("/eval/suites/{suite_name}/run", tags=["eval"])
def run_eval_suite(
    suite_name: str,
    skill_version_id: str | None = Query(default=None),
) -> JSONResponse:
    """Trigger EvalRunner.run_suite() and return a summary."""
    from draftcheck.eval.runner import EvalRunner

    adapter = _get_adapter()
    session_factory = _get_session_factory()

    if session_factory is None:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL not configured; eval runner requires a database",
        )

    runner = EvalRunner(adapter=adapter, session_factory=session_factory)

    try:
        result = asyncio.get_event_loop().run_until_complete(
            runner.run_suite(suite_name, skill_version_id=skill_version_id)
        )
    except RuntimeError:
        # No event loop running (sync context) — create a fresh one
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                runner.run_suite(suite_name, skill_version_id=skill_version_id)
            )
        finally:
            loop.close()

    return JSONResponse(
        status_code=200,
        content={
            "suite_name": result.suite_name,
            "skill_version_id": result.skill_version_id,
            "pass_count": result.pass_count,
            "fail_count": result.fail_count,
            "error_count": result.error_count,
            "mean_score": result.mean_score,
            "total": result.pass_count + result.fail_count + result.error_count,
            "run_ids": [str(rid) for rid in result.run_ids],
        },
    )

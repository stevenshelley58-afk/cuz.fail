"""Health check and Prometheus-style metrics endpoints."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from draftcheck.db.engine import create_runtime_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ops"])


def _db_ok() -> bool:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False
    engine = None
    try:
        engine = create_runtime_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        if engine is not None:
            engine.dispose()


@router.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    db_status = "ok" if _db_ok() else "error"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
    }


@router.get("/metrics", include_in_schema=False)
def metrics() -> PlainTextResponse:
    database_url = os.getenv("DATABASE_URL")
    lines: list[str] = []

    if not database_url:
        lines.append("# DATABASE_URL not configured")
        return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")

    engine = None
    try:
        engine = create_runtime_engine(database_url)
        with engine.connect() as conn:
            # LLM spend today
            try:
                r = conn.execute(
                    text(
                        "SELECT COALESCE(ROUND(SUM(cost_usd) * 100), 0) FROM job_traces "
                        "WHERE started_at >= date_trunc('day', now() AT TIME ZONE 'UTC')"
                    )
                )
                spend = float(r.scalar() or 0)
                lines.append(f"draftcheck_llm_spend_today_cents {spend}")
            except Exception:
                lines.append("draftcheck_llm_spend_today_cents 0")

            # LLM requests by status
            try:
                r = conn.execute(
                    text("SELECT status, COUNT(*) FROM job_traces GROUP BY status")
                )
                for status, count in r.fetchall():
                    lines.append(
                        f'draftcheck_llm_requests_total{{status="{status}"}} {count}'
                    )
            except Exception:
                pass

            # Approved rules
            try:
                r = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM rules WHERE lifecycle_status = 'approved'"
                    )
                )
                lines.append(f"draftcheck_rules_approved_total {r.scalar() or 0}")
            except Exception:
                pass

            # Check runs today
            try:
                r = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM check_runs "
                        "WHERE created_at >= date_trunc('day', now())"
                    )
                )
                lines.append(f"draftcheck_check_runs_today {r.scalar() or 0}")
            except Exception:
                pass
    except Exception as exc:
        logger.warning("metrics probe failed: %s", exc)
        lines.append("# db probe failed")
    finally:
        if engine is not None:
            engine.dispose()

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")

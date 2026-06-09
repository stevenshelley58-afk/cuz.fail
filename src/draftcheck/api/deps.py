"""Shared FastAPI dependencies for V3 API routers."""

from __future__ import annotations

import os
from collections.abc import Callable, Generator

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from draftcheck.db.engine import create_session_factory

# One engine/session factory per process, rebuilt only when DATABASE_URL
# changes (tests swap the URL between cases).
_session_factory: Callable[[], Session] | None = None
_factory_url: str | None = None


def get_db_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session bound to the shared engine.

    Raises 503 when DATABASE_URL is not configured so non-DB test suites can
    still import and route-test API modules with dependency overrides.
    """
    global _session_factory, _factory_url
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is not configured; durable storage unavailable.",
        )
    if _session_factory is None or _factory_url != database_url:
        _session_factory = create_session_factory(database_url)
        _factory_url = database_url
    db = _session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

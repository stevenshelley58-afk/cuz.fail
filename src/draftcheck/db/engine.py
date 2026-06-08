"""Small SQLAlchemy engine/session helpers for V3 runtime code."""

from __future__ import annotations

import os
from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def database_url_from_env() -> str | None:
    return os.getenv("DATABASE_URL")


def create_runtime_engine(database_url: str | None = None) -> Engine:
    url = database_url or database_url_from_env()
    if not url:
        raise RuntimeError("DATABASE_URL is required for a durable V3 store")
    return create_engine(url, pool_pre_ping=True, future=True)


def create_session_factory(database_url: str | None = None) -> Callable[[], Session]:
    engine = create_runtime_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

"""Postgres-backed V3 job package."""

from __future__ import annotations

import os

import procrastinate


def _conninfo() -> str:
    conninfo = os.getenv("PROCRASTINATE_DB_URI")
    if conninfo:
        return conninfo
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        return database_url
    raise RuntimeError("PROCRASTINATE_DB_URI or a PostgreSQL DATABASE_URL is required")


procrastinate_app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        conninfo=_conninfo(),
    ),
    worker_defaults={"listen_notify": False},
)


@procrastinate_app.task(name="draftcheck.noop", queue="default")
def noop() -> str:
    return "ok"

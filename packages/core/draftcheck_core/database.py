from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from draftcheck_core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
_DATABASE_INITIALIZED = False
REQUIRED_POSTGRES_EXTENSIONS = ("postgis", "vector")


def init_database() -> None:
    global _DATABASE_INITIALIZED
    if _DATABASE_INITIALIZED:
        return
    from draftcheck_core import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _upgrade_database_schema()
    if settings.bootstrap_demo_source_library:
        _bootstrap_demo_source_library()
    _DATABASE_INITIALIZED = True


def get_db() -> Generator[Session, None, None]:
    init_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_persistence_ready(settings: Settings | None = None) -> dict[str, str]:
    resolved = settings or get_settings()
    if resolved.require_durable_database and _is_sqlite_database_url(resolved.database_url):
        return {
            "status": "error",
            "detail": (
                "REQUIRE_DURABLE_DATABASE=true but DATABASE_URL is SQLite; "
                "configure a PostgreSQL/PostGIS DATABASE_URL."
            ),
        }
    if _is_sqlite_database_url(resolved.database_url):
        return {"status": "ok", "detail": "SQLite local/test database"}
    return {"status": "ok", "detail": "durable database URL configured"}


def check_database_extensions_ready(db: Session) -> dict[str, str]:
    bind = db.get_bind()
    dialect_name = bind.dialect.name
    if dialect_name == "sqlite":
        return {"status": "disabled", "detail": "SQLite local/test database"}
    if dialect_name != "postgresql":
        return {
            "status": "error",
            "detail": f"Unsupported durable database dialect '{dialect_name}'; configure PostgreSQL/PostGIS.",
        }

    try:
        rows = db.execute(text("select extname from pg_extension where extname in ('postgis', 'vector')"))
        installed = {row[0] for row in rows}
    except Exception as exc:
        return {"status": "error", "detail": f"Could not verify PostgreSQL extensions: {exc}"}

    missing = [extension for extension in REQUIRED_POSTGRES_EXTENSIONS if extension not in installed]
    if missing:
        return {
            "status": "error",
            "detail": "PostgreSQL database is missing required extensions: " + ", ".join(missing),
        }
    return {"status": "ok", "detail": "required PostgreSQL extensions installed: postgis, vector"}


def check_database_migrations_ready(db: Session) -> dict[str, str]:
    bind = db.get_bind()
    if bind.dialect.name == "sqlite":
        return {"status": "disabled", "detail": "SQLite local/test database"}

    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
    except ImportError as exc:
        return {"status": "error", "detail": f"Could not verify Alembic migrations: {exc}"}

    config_path = _find_alembic_ini()
    if not config_path:
        return {"status": "error", "detail": "Could not locate alembic.ini for migration readiness check."}

    try:
        config = Config(str(config_path))
        script = ScriptDirectory.from_config(config)
        expected_heads = set(script.get_heads())
        current_heads = set(MigrationContext.configure(db.connection()).get_current_heads())
    except Exception as exc:
        return {"status": "error", "detail": f"Could not verify Alembic migrations: {exc}"}

    if not current_heads:
        return {"status": "error", "detail": "Database is not stamped with an Alembic revision."}
    if current_heads != expected_heads:
        return {
            "status": "error",
            "detail": (
                "Database migrations are not at head: "
                f"current={_format_revisions(current_heads)}, expected={_format_revisions(expected_heads)}"
            ),
        }
    return {"status": "ok", "detail": f"database migrations at head: {_format_revisions(expected_heads)}"}


def _is_sqlite_database_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _upgrade_database_schema() -> None:
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        return

    config_path = _find_alembic_ini()
    if not config_path:
        return
    _prepare_alembic_version_table()
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


def _prepare_alembic_version_table() -> None:
    if engine.dialect.name == "sqlite":
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                create table if not exists alembic_version (
                    version_num varchar(255) not null primary key
                )
                """
            )
        )
        connection.execute(text("alter table alembic_version alter column version_num type varchar(255)"))


def _find_alembic_ini() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        legacy_candidate = parent / "alembic-legacy.ini"
        if legacy_candidate.exists():
            return legacy_candidate
        candidate = parent / "alembic.ini"
        if candidate.exists():
            return candidate
    return None


def _format_revisions(revisions: set[str]) -> str:
    return ", ".join(sorted(revisions)) or "none"


def _bootstrap_demo_source_library() -> None:
    from draftcheck_core.bootstrap_sources import ensure_demo_source_library

    with SessionLocal() as db:
        ensure_demo_source_library(db)
        db.commit()

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import re

from alembic import command
from alembic.config import Config

from draftcheck.db.models import Base


ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = ROOT / "alembic.ini"
V3_ALEMBIC = ROOT / "src" / "draftcheck" / "db" / "alembic"
V3_VERSIONS = sorted((V3_ALEMBIC / "versions").glob("*.py"))

LEGACY_TABLES = {
    "address_profiles",
    "source_licence_reviews",
    "rule_rows",
    "decision_traces",
    "review_queue_items",
    "golden_eval_cases",
    "golden_eval_runs",
    "source_chunk_embeddings",
    "check_definitions",
    "background_jobs",
}


def test_root_alembic_config_points_to_v3_schema_authority() -> None:
    config = Config(str(ALEMBIC_INI))

    assert config.get_main_option("script_location") == "src/draftcheck/db/alembic"
    assert V3_ALEMBIC.exists()
    assert (V3_ALEMBIC / "env.py").exists()


def test_v3_alembic_env_uses_new_metadata_without_legacy_imports() -> None:
    source = (V3_ALEMBIC / "env.py").read_text(encoding="utf-8")

    assert "from draftcheck.db.models import Base" in source
    assert "draftcheck_core" not in source
    assert "create_all" not in source
    assert "target_metadata = Base.metadata" in source


def test_v3_revisions_are_explicit_and_legacy_free() -> None:
    version_sources = [path.read_text(encoding="utf-8") for path in V3_VERSIONS]
    sources = "\n".join(version_sources)
    upgrade_sources = "\n".join(source.split("def downgrade", maxsplit=1)[0] for source in version_sources)

    # Substring checks below catch the *spirit* of the rule but used to
    # false-positive on docstrings that described the rule. The pattern
    # checks catch actual call sites; the substring checks remain for
    # legacy-table and old-codebase references where no callable exists.
    create_all_call = re.compile(r"(?<![\w\.])create_all\s*\(")
    drop_all_call = re.compile(r"(?<![\w\.])drop_all\s*\(")
    assert not create_all_call.search(sources)
    assert not drop_all_call.search(sources)
    assert "draftcheck_core" not in sources
    for legacy_table in LEGACY_TABLES:
        assert legacy_table not in sources

    created_tables = set(re.findall(r'op\.create_table\(\s*"([^"]+)"', upgrade_sources))
    renamed_tables = dict(re.findall(r'op\.rename_table\(\s*"([^"]+)"\s*,\s*"([^"]+)"', upgrade_sources))
    dropped_tables = set(re.findall(r'op\.drop_table\(\s*"([^"]+)"', upgrade_sources))
    final_tables = (created_tables - set(renamed_tables) - dropped_tables) | set(renamed_tables.values())

    assert set(Base.metadata.tables) == final_tables


def test_v3_offline_postgresql_downgrade_sql_exists_for_every_revision() -> None:
    """Every migration must have a reversible downgrade — verified by generating SQL."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option(
        "sqlalchemy.url",
        "postgresql+psycopg://draftcheck:draftcheck@localhost:5432/draftcheck",
    )

    for version_path in V3_VERSIONS:
        revision = version_path.stem.split("_")[0]
        output = StringIO()
        with redirect_stdout(output):
            command.downgrade(config, f"{revision}:-1", sql=True)
        sql = output.getvalue().strip()
        assert sql, f"downgrade for {revision} produced no SQL"
        # Downgrade SQL must not attempt to create the legacy tables.
        sql_lower = sql.lower()
        for legacy_table in LEGACY_TABLES:
            assert f"create table {legacy_table}" not in sql_lower


def test_v3_offline_postgresql_upgrade_sql_contains_foundation_schema() -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option(
        "sqlalchemy.url",
        "postgresql+psycopg://draftcheck:draftcheck@localhost:5432/draftcheck",
    )
    output = StringIO()

    with redirect_stdout(output):
        command.upgrade(config, "head", sql=True)

    sql = output.getvalue().lower()

    assert "create table orgs" in sql
    assert "create table projects" in sql
    assert "create table source_versions" in sql
    assert "alter table sources rename to source_documents" in sql
    assert "create table clauses" in sql
    assert "create table rules" in sql
    assert "create table resolved_rules" in sql
    assert "create table document_facts" in sql
    assert "create table validations" in sql
    assert "create table audit_events" in sql
    assert "create table job_traces" in sql
    assert "create table spatial_datasets" in sql
    assert "create table property_facts" in sql
    assert "using hnsw" in sql
    assert "using gin (to_tsvector('english', text))" in sql
    assert "using gist (geom)" in sql
    assert "create extension if not exists pg_trgm" in sql
    assert "geometry(point,7844)" in sql
    assert "vector(1536)" in sql
    for legacy_table in LEGACY_TABLES:
        assert f"create table {legacy_table}" not in sql

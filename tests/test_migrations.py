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
V3_VERSION = V3_ALEMBIC / "versions" / "0001_v3_foundation_metadata.py"

LEGACY_TABLES = {
    "address_profiles",
    "source_licence_reviews",
    "rule_rows",
    "resolved_rules",
    "decision_traces",
    "review_queue_items",
    "golden_eval_cases",
    "golden_eval_runs",
    "source_chunk_embeddings",
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


def test_v3_base_revision_is_explicit_and_legacy_free() -> None:
    source = V3_VERSION.read_text(encoding="utf-8")

    assert "create_all" not in source
    assert "drop_all" not in source
    assert "draftcheck_core" not in source
    for legacy_table in LEGACY_TABLES:
        assert legacy_table not in source

    created_tables = set(re.findall(r'op\.create_table\(\s*"([^"]+)"', source))
    assert set(Base.metadata.tables) == created_tables


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
    assert "create table job_traces" in sql
    assert "create table spatial_datasets" in sql
    assert "create table property_facts" in sql
    assert "geometry(point,7844)" in sql
    assert "vector(1536)" in sql
    for legacy_table in LEGACY_TABLES:
        assert f"create table {legacy_table}" not in sql

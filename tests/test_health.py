from __future__ import annotations

from pathlib import Path

from draftcheck_api.main import check_cors_ready
from draftcheck_api.rate_limit import check_rate_limit_ready
from draftcheck_core.auth import check_api_auth_ready
from draftcheck_core.config import get_settings
from draftcheck_core.database import (
    check_database_extensions_ready,
    check_database_migrations_ready,
    check_database_persistence_ready,
)
from draftcheck_core.object_storage import check_object_storage_persistence_ready, check_object_storage_ready
from draftcheck_core.queue import check_rq_ready


def test_health_and_ready_endpoints(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200
    checks = ready.json()["checks"]
    assert checks["database"]["status"] == "ok"
    assert checks["database_extensions"] == {"status": "disabled", "detail": "SQLite local/test database"}
    assert checks["database_migrations"] == {"status": "disabled", "detail": "SQLite local/test database"}
    assert checks["api_auth"]["status"] == "disabled"
    assert checks["cors"] == {"status": "disabled", "detail": "wildcard CORS allowed for local/test deployment"}
    assert checks["rate_limit"] == {"status": "ok", "detail": "rate limiting enabled for upload and chat endpoints"}
    assert checks["object_storage"]["status"] == "ok"
    assert checks["rq"]["status"] == "disabled"


def test_ready_endpoint_reports_storage_failure(client, monkeypatch):
    monkeypatch.setattr(
        "draftcheck_api.main.check_object_storage_ready",
        lambda root=None, settings=None: {"status": "error", "detail": "cannot write"},
    )

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["object_storage"] == {"status": "error", "detail": "cannot write"}


def test_openapi_operation_ids_are_unique(client):
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    operation_ids = [
        operation["operationId"]
        for path_item in schema.json()["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and operation.get("operationId")
    ]
    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_marks_deprecated_compliance_aliases(client):
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]

    assert paths["/v1/projects/{project_id}/compliance/run"]["post"].get("deprecated") is not True
    assert paths["/v1/projects/{project_id}/compliance/matrix"]["get"].get("deprecated") is not True
    assert paths["/v1/projects/{project_id}/checks/run"]["post"]["deprecated"] is True
    assert paths["/v1/projects/{project_id}/compliance-matrix"]["get"]["deprecated"] is True


def test_ready_endpoint_reports_rq_failure(client, monkeypatch):
    monkeypatch.setattr(
        "draftcheck_api.main.check_rq_ready",
        lambda settings=None: {"status": "error", "backend": "redis-rq", "detail": "ping failed"},
    )

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["rq"]["detail"] == "ping failed"


def test_ready_endpoint_reports_required_durable_database_failure(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/draftcheck.db")

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["database_persistence"] == {
        "status": "error",
        "detail": (
            "REQUIRE_DURABLE_DATABASE=true but DATABASE_URL is SQLite; "
            "configure a PostgreSQL/PostGIS DATABASE_URL."
        ),
    }


def test_database_persistence_check_accepts_non_sqlite_database(monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.test:5432/draftcheck")

    settings = get_settings()
    result = check_database_persistence_ready(settings)

    assert settings.database_url == "postgresql+psycopg://user:pass@example.test:5432/draftcheck"
    assert result == {"status": "ok", "detail": "durable database URL configured"}


def test_database_extensions_check_accepts_required_postgres_extensions():
    result = check_database_extensions_ready(FakeDb("postgresql", [("postgis",), ("vector",)]))

    assert result == {
        "status": "ok",
        "detail": "required PostgreSQL extensions installed: postgis, vector",
    }


def test_database_extensions_check_reports_missing_required_extension():
    result = check_database_extensions_ready(FakeDb("postgresql", [("postgis",)]))

    assert result == {
        "status": "error",
        "detail": "PostgreSQL database is missing required extensions: vector",
    }


def test_database_extensions_check_reports_unsupported_dialect():
    result = check_database_extensions_ready(FakeDb("mysql", []))

    assert result == {
        "status": "error",
        "detail": "Unsupported durable database dialect 'mysql'; configure PostgreSQL/PostGIS.",
    }


def test_database_migrations_check_is_disabled_for_sqlite():
    result = check_database_migrations_ready(FakeDb("sqlite", []))

    assert result == {"status": "disabled", "detail": "SQLite local/test database"}


def test_ready_endpoint_reports_auth_required_for_public_deployment(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["api_auth"] == {
        "status": "error",
        "detail": (
            "REQUIRE_DURABLE_DATABASE=true but API_AUTH_ENABLED=false; "
            "enable API auth before public deployment."
        ),
    }


def test_ready_endpoint_reports_wildcard_cors_for_durable_deployment(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["cors"] == {
        "status": "error",
        "detail": "Durable deployments must not use wildcard CORS; configure CORS_ALLOWED_ORIGINS.",
    }


def test_cors_ready_accepts_explicit_production_origin(monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.cuz.fail")

    assert check_cors_ready(get_settings()) == {"status": "ok", "detail": "explicit CORS origins configured"}


def test_ready_endpoint_reports_disabled_rate_limit_for_durable_deployment(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["rate_limit"] == {
        "status": "error",
        "detail": "Durable deployments must enable rate limiting for upload and chat endpoints.",
    }


def test_rate_limit_ready_rejects_non_positive_durable_chat_limit(monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("RATE_LIMIT_CHAT_REQUESTS", "0")

    assert check_rate_limit_ready(get_settings()) == {
        "status": "error",
        "detail": "Durable deployments require RATE_LIMIT_CHAT_REQUESTS to be greater than 0.",
    }


def test_ready_endpoint_reports_enabled_auth_without_keys(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.delenv("API_AUTH_KEYS", raising=False)

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["api_auth"] == {
        "status": "error",
        "detail": "API_AUTH_ENABLED=true but API_AUTH_KEYS is empty.",
    }


def test_api_auth_ready_accepts_short_local_key(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "secret-key")
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "false")

    assert check_api_auth_ready(get_settings()) == {
        "status": "ok",
        "detail": "API key authentication enabled",
    }


def test_api_auth_ready_rejects_short_production_key(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "tenant-a:short-key")
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")

    assert check_api_auth_ready(get_settings()) == {
        "status": "error",
        "detail": "Production API_AUTH_KEYS values must be at least 32 characters long.",
    }


def test_ready_endpoint_reports_required_durable_object_storage_failure(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_OBJECT_STORAGE", "true")
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)

    ready = client.get("/ready")

    assert ready.status_code == 503
    assert ready.json()["checks"]["object_storage"] == {
        "status": "error",
        "detail": (
            "REQUIRE_DURABLE_OBJECT_STORAGE=true but S3_ENDPOINT_URL is not configured; "
            "configure S3/MinIO object storage for uploads and exports."
        ),
    }


def test_object_storage_persistence_check_accepts_s3_config(monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_OBJECT_STORAGE", "true")
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://minio.example.test")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "draftcheck")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "secret")

    result = check_object_storage_persistence_ready(get_settings())

    assert result == {"status": "ok", "detail": "durable object storage configured"}


def test_object_storage_ready_probe_writes_reads_and_removes_sentinel(tmp_path: Path):
    result = check_object_storage_ready(str(tmp_path))

    assert result["status"] == "ok"
    assert not list((tmp_path / ".readiness").glob("probe-*.txt"))


def test_object_storage_ready_probe_reports_unusable_root(tmp_path: Path):
    root_file = tmp_path / "not-a-directory"
    root_file.write_text("not a directory", encoding="utf-8")

    result = check_object_storage_ready(str(root_file))

    assert result["status"] == "error"


def test_rq_ready_disabled_by_default(monkeypatch):
    monkeypatch.delenv("RQ_ENABLED", raising=False)

    result = check_rq_ready()

    assert result == {
        "status": "disabled",
        "backend": "local-disabled",
        "detail": "RQ_ENABLED=false",
    }


def test_rq_ready_pings_when_enabled(monkeypatch):
    class FakeRedis:
        def ping(self):
            return True

    monkeypatch.setenv("RQ_ENABLED", "true")
    monkeypatch.setattr("draftcheck_core.queue.redis_connection", lambda settings=None: FakeRedis())

    result = check_rq_ready()

    assert result["status"] == "ok"
    assert result["backend"] == "redis-rq"


def test_rq_ready_reports_ping_failure(monkeypatch):
    class FakeRedis:
        def ping(self):
            raise RuntimeError("redis unavailable")

    monkeypatch.setenv("RQ_ENABLED", "true")
    monkeypatch.setattr("draftcheck_core.queue.redis_connection", lambda settings=None: FakeRedis())

    result = check_rq_ready()

    assert result == {
        "status": "error",
        "backend": "redis-rq",
        "detail": "redis unavailable",
    }


class FakeDialect:
    def __init__(self, name: str):
        self.name = name


class FakeBind:
    def __init__(self, dialect_name: str):
        self.dialect = FakeDialect(dialect_name)


class FakeDb:
    def __init__(self, dialect_name: str, rows: list[tuple[str]]):
        self.bind = FakeBind(dialect_name)
        self.rows = rows

    def get_bind(self):
        return self.bind

    def execute(self, _statement):
        return self.rows

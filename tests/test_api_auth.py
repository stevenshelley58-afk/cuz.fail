from __future__ import annotations

from fastapi.testclient import TestClient

from draftcheck_api.main import create_app

PRODUCTION_API_KEY = "abcdefghijklmnopqrstuvwxyz123456"
PRODUCTION_ORIGIN = "https://app.cuz.fail"


def _set_production_cors(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", PRODUCTION_ORIGIN)


def test_api_auth_blocks_protected_route_when_enabled(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "secret-key")

    response = client.get("/v1/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid API key", "code": "unauthorized"}


def test_api_auth_accepts_bearer_token(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "secret-key")

    response = client.get("/v1/me", headers={"authorization": "Bearer secret-key"})

    assert response.status_code == 200
    assert response.json()["id"] == "dev-user"


def test_api_auth_accepts_x_api_key(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "secret-key")

    response = client.get("/v1/me", headers={"x-api-key": "secret-key"})

    assert response.status_code == 200
    assert response.json()["id"] == "dev-user"


def test_api_auth_exempts_health_ready_and_dev_login(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "secret-key")

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.post("/v1/auth/dev-login").status_code == 200


def test_api_auth_enabled_without_keys_returns_503_for_protected_route(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.delenv("API_AUTH_KEYS", raising=False)

    response = client.get("/v1/me")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "API_AUTH_ENABLED=true but API_AUTH_KEYS is empty.",
        "code": "auth_not_ready",
    }


def test_production_readiness_blocks_protected_routes_before_auth(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/draftcheck.db")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")

    response = client.post("/v1/chat", json={"message": "What is the site cover requirement for R30?"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"]["database_persistence"]["status"] == "error"
    assert body["checks"]["api_auth"]["status"] == "error"


def test_cors_preflight_reaches_cors_middleware_when_deployment_not_ready(monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/draftcheck.db")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", PRODUCTION_ORIGIN)

    with TestClient(create_app()) as test_client:
        response = test_client.options(
            "/v1/chat",
            headers={
                "Origin": PRODUCTION_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PRODUCTION_ORIGIN


def test_cors_preflight_rejects_unlisted_origin_before_auth_readiness(monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/draftcheck.db")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", PRODUCTION_ORIGIN)

    with TestClient(create_app()) as test_client:
        response = test_client.options(
            "/v1/chat",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_rejects_wildcard_origin_setting_in_durable_mode(monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/draftcheck.db")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")

    with TestClient(create_app()) as test_client:
        response = test_client.options(
            "/v1/chat",
            headers={
                "Origin": PRODUCTION_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_production_readiness_blocks_protected_routes_without_durable_object_storage(client, monkeypatch):
    _set_production_cors(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.test:5432/draftcheck")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", f"tenant-a:{PRODUCTION_API_KEY}")
    monkeypatch.setenv("REQUIRE_DURABLE_OBJECT_STORAGE", "true")
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert set(body["checks"]) == {"object_storage"}
    assert body["checks"]["object_storage"]["status"] == "error"


def test_production_readiness_blocks_protected_routes_when_s3_probe_fails(client, monkeypatch):
    _set_production_cors(monkeypatch)
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", f"tenant-a:{PRODUCTION_API_KEY}")
    monkeypatch.setenv("REQUIRE_DURABLE_OBJECT_STORAGE", "true")
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://minio.example.test")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "draftcheck")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(
        "draftcheck_api.main.check_object_storage_ready",
        lambda settings=None: {"status": "error", "detail": "S3 bucket does not exist: exports"},
    )

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"] == {
        "object_storage": {"status": "error", "detail": "S3 bucket does not exist: exports"}
    }


def test_production_readiness_blocks_protected_routes_when_database_schema_missing(client, monkeypatch):
    _set_production_cors(monkeypatch)
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.test:5432/draftcheck")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", f"tenant-a:{PRODUCTION_API_KEY}")
    monkeypatch.setattr(
        "draftcheck_api.main._database_ready_checks",
        lambda: {
            "database": {"status": "error", "detail": "missing tables: source_documents"},
            "database_extensions": {
                "status": "ok",
                "detail": "required PostgreSQL extensions installed: postgis, vector",
            },
        },
    )

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"] == {
        "database": {"status": "error", "detail": "missing tables: source_documents"}
    }


def test_production_readiness_blocks_protected_routes_when_migrations_are_stale(client, monkeypatch):
    _set_production_cors(monkeypatch)
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.test:5432/draftcheck")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", f"tenant-a:{PRODUCTION_API_KEY}")
    monkeypatch.setattr(
        "draftcheck_api.main._database_ready_checks",
        lambda: {
            "database": {"status": "ok", "detail": "ok"},
            "database_extensions": {
                "status": "ok",
                "detail": "required PostgreSQL extensions installed: postgis, vector",
            },
            "database_migrations": {
                "status": "error",
                "detail": (
                    "Database migrations are not at head: "
                    "current=0008_require_postgis_pgvector, expected=0009_source_chunk_embeddings"
                ),
            },
        },
    )

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"] == {
        "database_migrations": {
            "status": "error",
            "detail": (
                "Database migrations are not at head: "
                "current=0008_require_postgis_pgvector, expected=0009_source_chunk_embeddings"
            ),
        }
    }


def test_production_readiness_blocks_protected_routes_when_rq_enabled_but_unavailable(client, monkeypatch):
    _set_production_cors(monkeypatch)
    monkeypatch.setenv("REQUIRE_DURABLE_OBJECT_STORAGE", "true")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", f"tenant-a:{PRODUCTION_API_KEY}")
    monkeypatch.setenv("RQ_ENABLED", "true")
    monkeypatch.setattr(
        "draftcheck_api.main.check_object_storage_ready",
        lambda settings=None: {"status": "ok", "detail": "s3 buckets ready: raw-sources, parsed-sources, uploads, exports"},
    )
    monkeypatch.setattr(
        "draftcheck_api.main.check_rq_ready",
        lambda settings=None: {"status": "error", "backend": "redis-rq", "detail": "redis unavailable"},
    )

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"] == {
        "rq": {"status": "error", "backend": "redis-rq", "detail": "redis unavailable"}
    }


def test_production_readiness_blocks_protected_routes_when_rate_limit_disabled(client, monkeypatch):
    _set_production_cors(monkeypatch)
    monkeypatch.setenv("REQUIRE_DURABLE_OBJECT_STORAGE", "true")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", f"tenant-a:{PRODUCTION_API_KEY}")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setattr(
        "draftcheck_api.main.check_object_storage_ready",
        lambda settings=None: {"status": "ok", "detail": "s3 buckets ready: raw-sources, parsed-sources, uploads, exports"},
    )

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"] == {
        "rate_limit": {
            "status": "error",
            "detail": "Durable deployments must enable rate limiting for upload and chat endpoints.",
        }
    }


def test_production_readiness_exempts_health_ready_and_docs_but_disables_dev_login(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/draftcheck.db")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503
    assert client.get("/openapi.json").status_code == 200
    dev_login = client.post("/v1/auth/dev-login")
    assert dev_login.status_code == 404
    assert dev_login.json()["detail"] == "Development login is disabled for durable deployments"


def test_dev_login_disabled_when_durable_object_storage_required(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_OBJECT_STORAGE", "true")

    response = client.post("/v1/auth/dev-login")

    assert response.status_code == 404
    assert response.json()["detail"] == "Development login is disabled for durable deployments"


def test_production_readiness_rejects_unscoped_api_key(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.test:5432/draftcheck")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", PRODUCTION_API_KEY)

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"]["api_auth"] == {
        "status": "error",
        "detail": "Production API_AUTH_KEYS must use tenant-scoped entries in tenant-id:key format.",
    }


def test_production_readiness_rejects_short_api_key(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.test:5432/draftcheck")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "tenant-a:short-key")

    response = client.get("/v1/me", headers={"authorization": "Bearer short-key"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "deployment_not_ready"
    assert body["checks"]["api_auth"] == {
        "status": "error",
        "detail": "Production API_AUTH_KEYS values must be at least 32 characters long.",
    }


def test_production_readiness_allows_auth_when_ready(client, monkeypatch):
    _set_production_cors(monkeypatch)
    monkeypatch.setenv("REQUIRE_DURABLE_DATABASE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.test:5432/draftcheck")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", f"tenant-a:{PRODUCTION_API_KEY}")

    response = client.get("/v1/me", headers={"authorization": f"Bearer {PRODUCTION_API_KEY}"})

    assert response.status_code == 200
    assert response.json()["id"] == "dev-user"

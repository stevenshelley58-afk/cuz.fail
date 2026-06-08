from __future__ import annotations

from pathlib import Path

import yaml


COMPOSE_FILES = [
    Path("docker-compose.yml"),
    Path("deploy/docker-compose.vps.yml"),
    Path("infra/docker/docker-compose.production.yml"),
]


def test_db_compose_services_use_custom_postgis_pgvector_image_and_healthcheck():
    for compose_path in COMPOSE_FILES:
        compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        db_service = compose["services"]["db"]

        build = db_service["build"]
        assert build["dockerfile"] == "infra/docker/db/Dockerfile"
        assert db_service["healthcheck"]["test"] == [
            "CMD-SHELL",
            "draftcheck-db-healthcheck",
        ]

        for service_name in ["api", "worker"]:
            service = compose["services"][service_name]
            assert service["depends_on"]["db"]["condition"] == "service_healthy"
            assert service["environment"]["REQUIRE_DURABLE_OBJECT_STORAGE"] == "true"
            assert service["environment"]["S3_ENDPOINT_URL"] == "http://minio:9000"
        cors_origins = compose["services"]["api"]["environment"]["CORS_ALLOWED_ORIGINS"]
        assert cors_origins
        assert "*" not in cors_origins
        api_environment = compose["services"]["api"]["environment"]
        assert api_environment["RATE_LIMIT_ENABLED"] in {"true", "${RATE_LIMIT_ENABLED:-true}"}
        assert api_environment["RATE_LIMIT_WINDOW_SECONDS"] == "${RATE_LIMIT_WINDOW_SECONDS:-60}"
        assert api_environment["RATE_LIMIT_CHAT_REQUESTS"] == "${RATE_LIMIT_CHAT_REQUESTS:-120}"
        assert api_environment["RATE_LIMIT_UPLOAD_REQUESTS"] == "${RATE_LIMIT_UPLOAD_REQUESTS:-20}"


def test_db_image_installs_pgvector_and_copies_extension_healthcheck():
    dockerfile = Path("infra/docker/db/Dockerfile").read_text(encoding="utf-8")

    assert "FROM postgis/postgis:16-3.5" in dockerfile
    assert "PGVECTOR_VERSION=0.8.0" in dockerfile
    assert "make -C /tmp/pgvector install" in dockerfile
    assert "init-extensions.sql" in dockerfile
    assert "draftcheck-db-healthcheck" in dockerfile

    healthcheck = Path("infra/docker/db/healthcheck.sh").read_text(encoding="utf-8")
    assert "pg_isready" in healthcheck
    assert "pg_extension where extname = 'postgis'" in healthcheck
    assert "pg_extension where extname = 'vector'" in healthcheck


def test_database_extension_sql_and_migration_require_postgis_and_pgvector():
    init_sql = Path("infra/docker/db/init-extensions.sql").read_text(encoding="utf-8")
    migration = Path("infra/alembic/versions/0008_require_postgis_pgvector.py").read_text(
        encoding="utf-8"
    )

    assert "CREATE EXTENSION IF NOT EXISTS postgis" in init_sql
    assert "CREATE EXTENSION IF NOT EXISTS vector" in init_sql
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in migration
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration
    assert 'dialect.name == "sqlite"' in migration


def test_vercel_production_config_can_derive_supabase_url_and_generate_api_key():
    script = Path("scripts/configure-vercel-production.ps1").read_text(encoding="utf-8")
    docs = Path("docs/INFRASTRUCTURE.md").read_text(encoding="utf-8")
    vercel_entrypoint = Path("api/index.py").read_text(encoding="utf-8")

    assert "SUPABASE_DB_PASSWORD" in script
    assert "supabase\\.temp\\pooler-url" in script
    assert "ConvertTo-DatabaseUrlWithPassword" in script
    assert "New-GeneratedApiAuthKeys" in script
    assert "Assert-ProductionApiAuthKeys" in script
    assert "Assert-UsablePostgresDatabaseUrl" in script
    assert "looks like a Supabase secret digest" in script
    assert "Invoke-DurableDatabaseMigrations" in script
    assert "[switch]$SkipMigrations" in script
    assert "[switch]$PublicDefaultsOnly" in script
    assert "function New-PublicDefaultVercelEnvVars" in script
    assert "function Set-VercelEnvVars" in script
    assert "function Invoke-VercelProductionDeploy" in script
    assert "if ($PublicDefaultsOnly)" in script
    assert "Skipping full /ready success check" in script
    assert '$ErrorActionPreference = "Continue"' in script
    assert 'throw "Failed to list Vercel env vars for $TargetEnvironment."' in script
    assert "from draftcheck_core.database import init_database; init_database()" in script
    assert "tenant-scoped entries in tenant-id:key format" in script
    assert "must include at least one tenant-scoped production API key" in script
    assert "at least 32 characters long for production" in script
    assert "Generated DRAFTCHECK_API_AUTH_KEYS=" in script
    assert script.index("$ApiAuthKeys = Resolve-ApiAuthKeys") > script.index(
        'Assert-ConfiguredSecret "S3_SECRET_ACCESS_KEY"'
    )
    assert 'REQUIRE_DURABLE_OBJECT_STORAGE = "true"' in script
    assert 'CORS_ALLOWED_ORIGINS = $CorsAllowedOrigins' in script
    assert 'RATE_LIMIT_ENABLED = $RateLimitEnabled' in script
    assert 'RATE_LIMIT_CHAT_REQUESTS = $RateLimitChatRequests' in script
    assert 'RATE_LIMIT_UPLOAD_REQUESTS = $RateLimitUploadRequests' in script
    assert 'EMBEDDING_PROVIDER = $EmbeddingProvider' in script
    assert 'OPENAI_BASE_URL = $OpenAiBaseUrl' in script
    assert 'Assert-ConfiguredSecret "OPENAI_API_KEY"' in script
    assert '$envVars["OPENAI_API_KEY"] = $OpenAiApiKey' in script
    assert 'S3_REGION = $S3Region' in script
    assert "https://app.cuz.fail" in script
    assert 'Assert-ConfiguredSecret "CORS_ALLOWED_ORIGINS"' in script
    assert 'BOOTSTRAP_DEMO_SOURCE_LIBRARY = "false"' in script
    public_defaults_block = script.split("function New-PublicDefaultVercelEnvVars", 1)[1].split(
        "function Set-VercelEnvVars",
        1,
    )[0]
    assert 'BOOTSTRAP_DEMO_SOURCE_LIBRARY = "true"' not in public_defaults_block
    assert "DATABASE_URL" not in public_defaults_block
    assert "API_AUTH_KEYS" not in public_defaults_block
    assert "$envVars[\"DATABASE_URL\"] = $DatabaseUrl" in script
    assert "$envVars[\"API_AUTH_KEYS\"] = $ApiAuthKeys" in script
    assert 'Assert-ConfiguredSecret "S3_ENDPOINT_URL"' in script
    assert '"S3_REGION"' in script
    assert '"S3_SESSION_TOKEN"' in script
    assert 'Assert-ConfiguredSecret "S3_ACCESS_KEY_ID"' in script
    assert 'Assert-ConfiguredSecret "S3_SECRET_ACCESS_KEY"' in script
    assert "boto3>=1.34.0" in Path("requirements.txt").read_text(encoding="utf-8")
    assert "boto3>=1.34.0" in Path("pyproject.toml").read_text(encoding="utf-8")
    assert "alembic>=1.13.0" in Path("requirements.txt").read_text(encoding="utf-8")
    assert "alembic>=1.13.0" in Path("pyproject.toml").read_text(encoding="utf-8")
    assert "SUPABASE_DB_PASSWORD" in docs
    assert "64-character value returned by `supabase secrets list`" in docs
    assert "operator-approved credential rotation" in docs
    assert "-PublicDefaultsOnly -Deploy" in docs
    assert "protected routes remain fail-closed until the full" in docs
    assert "default-tenant:<random-key>" in docs
    assert "applies database migrations by default" in docs
    assert "-SkipMigrations" in docs
    assert "REQUIRE_DURABLE_OBJECT_STORAGE=true" in docs
    assert "S3_REGION" in docs
    assert "S3_SESSION_TOKEN" in docs
    assert "storage/v1/s3" in docs
    assert "CORS_ALLOWED_ORIGINS" in docs
    assert "RATE_LIMIT_CHAT_REQUESTS" in docs
    assert "EMBEDDING_PROVIDER=openai" in docs
    assert "OPENAI_API_KEY" in docs
    assert "scripts/rebuild_source_embeddings.py" in docs
    assert "Authenticated requests are bucketed by tenant" in docs
    assert "wildcard CORS is allowed only for local/test deployments" in docs
    assert "BOOTSTRAP_DEMO_SOURCE_LIBRARY=false" in docs
    assert "Production runtime startup must not automatically seed the demo/bootstrap source library." in docs
    assert 'os.environ.setdefault("BOOTSTRAP_DEMO_SOURCE_LIBRARY", "false")' in vercel_entrypoint
    assert 'os.environ.setdefault("BOOTSTRAP_DEMO_SOURCE_LIBRARY", "true")' not in vercel_entrypoint

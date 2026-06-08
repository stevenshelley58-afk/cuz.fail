param(
    [string]$ComposeFile = "docker-compose.yml",
    [string]$ProjectName = "draftcheck-wa-core",
    [string]$DbUser = "draftcheck",
    [string]$DbName = "draftcheck"
)

$ErrorActionPreference = "Stop"

function Invoke-Compose {
    param([string[]]$Args)
    docker compose -f $ComposeFile --project-name $ProjectName @Args
}

Write-Host "Checking compose services..."
Invoke-Compose @("ps")

Write-Host "Checking PostGIS and pgvector extensions..."
Invoke-Compose @(
    "exec", "-T", "db",
    "psql", "-U", $DbUser, "-d", $DbName,
    "-c", "SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'vector') ORDER BY extname;"
)

Write-Host "Checking Redis..."
Invoke-Compose @("exec", "-T", "redis", "redis-cli", "ping")

Write-Host "Checking MinIO buckets..."
Invoke-Compose @(
    "run", "--rm", "--entrypoint", "/bin/sh", "minio-init",
    "-c",
    "mc alias set local http://minio:9000 `$MINIO_ROOT_USER `$MINIO_ROOT_PASSWORD >/dev/null && mc ls local"
)

Write-Host "Checking API readiness endpoint through the api container..."
Invoke-Compose @(
    "exec", "-T", "api",
    "python", "-c",
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5).read(); print('ok')"
)

Write-Host "Checking worker readiness..."
Invoke-Compose @(
    "exec", "-T", "worker",
    "python", "-m", "draftcheck_worker.main", "--check-ready"
)

Write-Host "Infrastructure health checks completed."

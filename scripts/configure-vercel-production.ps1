param(
    [ValidateSet("production", "preview", "development")]
    [string]$Environment = "production",

    [string]$DatabaseUrl = $env:DRAFTCHECK_DATABASE_URL,
    [string]$SupabaseDbPassword = $env:SUPABASE_DB_PASSWORD,
    [string]$SupabasePoolerUrl = $env:SUPABASE_POOLER_URL,
    [string]$ApiAuthKeys = $env:DRAFTCHECK_API_AUTH_KEYS,
    [string]$ApiAuthTenant = $env:DRAFTCHECK_API_AUTH_TENANT,
    [string]$CorsAllowedOrigins = $(if ($env:CORS_ALLOWED_ORIGINS) { $env:CORS_ALLOWED_ORIGINS } else { "https://app.cuz.fail" }),
    [string]$RateLimitEnabled = $(if ($env:RATE_LIMIT_ENABLED) { $env:RATE_LIMIT_ENABLED } else { "true" }),
    [string]$RateLimitWindowSeconds = $(if ($env:RATE_LIMIT_WINDOW_SECONDS) { $env:RATE_LIMIT_WINDOW_SECONDS } else { "60" }),
    [string]$RateLimitChatRequests = $(if ($env:RATE_LIMIT_CHAT_REQUESTS) { $env:RATE_LIMIT_CHAT_REQUESTS } else { "120" }),
    [string]$RateLimitUploadRequests = $(if ($env:RATE_LIMIT_UPLOAD_REQUESTS) { $env:RATE_LIMIT_UPLOAD_REQUESTS } else { "20" }),
    [string]$S3Region = $(if ($env:S3_REGION) { $env:S3_REGION } else { "us-east-1" }),
    [string]$EmbeddingProvider = $(if ($env:EMBEDDING_PROVIDER) { $env:EMBEDDING_PROVIDER } else { "mock" }),
    [string]$EmbeddingModel = $env:EMBEDDING_MODEL,
    [string]$EmbeddingDimensions = $(if ($env:EMBEDDING_DIMENSIONS) { $env:EMBEDDING_DIMENSIONS } else { "0" }),
    [string]$EmbeddingTimeoutSeconds = $(if ($env:EMBEDDING_TIMEOUT_SECONDS) { $env:EMBEDDING_TIMEOUT_SECONDS } else { "30" }),
    [string]$OpenAiApiKey = $env:OPENAI_API_KEY,
    [string]$OpenAiBaseUrl = $(if ($env:OPENAI_BASE_URL) { $env:OPENAI_BASE_URL } else { "https://api.openai.com/v1" }),
    [string]$ProductionUrl = "https://api.cuz.fail",
    [string]$GoldenEvalPath = "tests/gold",
    [string]$GoldenEvalTrack = "retrieval",

    [switch]$SkipMigrations,
    [switch]$SeedGoldenEvals,
    [switch]$RunGoldenEvals,
    [switch]$Deploy,
    [switch]$PublicDefaultsOnly,
    [switch]$SkipReadyCheck
)

$ErrorActionPreference = "Stop"

function Assert-ConfiguredSecret {
    param(
        [string]$Name,
        [string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Name is required. Set it in the current shell environment before running this script."
    }
}

function Get-LinkedSupabasePoolerUrl {
    if (-not [string]::IsNullOrWhiteSpace($SupabasePoolerUrl)) {
        return $SupabasePoolerUrl.Trim()
    }

    $poolerPath = Join-Path (Get-Location) "supabase\.temp\pooler-url"
    if (Test-Path $poolerPath) {
        return (Get-Content $poolerPath -Raw).Trim()
    }

    return ""
}

function ConvertTo-DatabaseUrlWithPassword {
    param(
        [string]$PoolerUrl,
        [string]$Password
    )

    $trimmed = $PoolerUrl.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return ""
    }
    if ($trimmed -match "^\s*postgres(?:ql)?(?:\+psycopg)?://[^:@/]+:[^@/]+@") {
        return $trimmed
    }

    Assert-ConfiguredSecret "SUPABASE_DB_PASSWORD" $Password
    $schemeSeparator = $trimmed.IndexOf("://")
    if ($schemeSeparator -lt 0) {
        throw "SUPABASE_POOLER_URL is not a PostgreSQL URL."
    }
    $schemeEnd = $schemeSeparator + 3
    $prefix = $trimmed.Substring(0, $schemeEnd)
    $rest = $trimmed.Substring($schemeEnd)
    $atIndex = $rest.IndexOf("@")
    if ($atIndex -lt 0) {
        throw "SUPABASE_POOLER_URL must include a database username."
    }

    $userInfo = $rest.Substring(0, $atIndex)
    $hostAndPath = $rest.Substring($atIndex)
    if ($userInfo.Contains(":")) {
        return $trimmed
    }

    $encodedPassword = [System.Uri]::EscapeDataString($Password)
    return "$prefix$($userInfo):$encodedPassword$hostAndPath"
}

function Resolve-DatabaseUrl {
    if (-not [string]::IsNullOrWhiteSpace($DatabaseUrl)) {
        return $DatabaseUrl.Trim()
    }

    $pooler = Get-LinkedSupabasePoolerUrl
    if ([string]::IsNullOrWhiteSpace($pooler)) {
        return ""
    }

    Write-Host "Deriving DATABASE_URL from linked Supabase pooler URL and SUPABASE_DB_PASSWORD"
    return ConvertTo-DatabaseUrlWithPassword -PoolerUrl $pooler -Password $SupabaseDbPassword
}

function New-GeneratedApiAuthKeys {
    param([string]$Tenant)

    $tenantValue = $Tenant.Trim()
    if ([string]::IsNullOrWhiteSpace($tenantValue)) {
        $tenantValue = "default-tenant"
    }
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    $secret = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
    return "$($tenantValue):$secret"
}

function Resolve-ApiAuthKeys {
    if (-not [string]::IsNullOrWhiteSpace($ApiAuthKeys)) {
        return $ApiAuthKeys.Trim()
    }

    $generated = New-GeneratedApiAuthKeys -Tenant $ApiAuthTenant
    Write-Warning "DRAFTCHECK_API_AUTH_KEYS was not set; generated a tenant-scoped API key. Store this value securely because Vercel env values are not recoverable after upload."
    Write-Host "Generated DRAFTCHECK_API_AUTH_KEYS=$generated"
    return $generated
}

function Assert-ProductionApiAuthKeys {
    param([string]$Keys)

    $validEntryCount = 0
    foreach ($entry in $Keys.Split(",")) {
        $trimmed = $entry.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        $validEntryCount += 1
        $separator = $trimmed.IndexOf(":")
        if ($separator -lt 1) {
            throw "DRAFTCHECK_API_AUTH_KEYS must use tenant-scoped entries in tenant-id:key format for production."
        }
        $tenant = $trimmed.Substring(0, $separator).Trim()
        $key = $trimmed.Substring($separator + 1).Trim()
        if ([string]::IsNullOrWhiteSpace($tenant) -or $tenant -eq "default") {
            throw "DRAFTCHECK_API_AUTH_KEYS tenant ids must be explicit and cannot be 'default' for production."
        }
        if ($key.Length -lt 32) {
            throw "DRAFTCHECK_API_AUTH_KEYS values must be at least 32 characters long for production."
        }
    }
    if ($validEntryCount -eq 0) {
        throw "DRAFTCHECK_API_AUTH_KEYS must include at least one tenant-scoped production API key."
    }
}

function Assert-UsablePostgresDatabaseUrl {
    param([string]$ResolvedDatabaseUrl)

    if ($ResolvedDatabaseUrl -match "^[a-fA-F0-9]{64}$") {
        throw (
            "DRAFTCHECK_DATABASE_URL looks like a Supabase secret digest, not a database URL. " +
            "Use the actual PostgreSQL/PostGIS connection string from Supabase dashboard, password vault, " +
            "or CI secret store."
        )
    }
    if ($ResolvedDatabaseUrl -match "^\s*sqlite") {
        throw "DRAFTCHECK_DATABASE_URL must point at PostgreSQL/PostGIS for production, not SQLite."
    }
    if ($ResolvedDatabaseUrl -notmatch "^\s*postgres(?:ql)?(?:\+psycopg)?://") {
        throw "DRAFTCHECK_DATABASE_URL must be a PostgreSQL connection URL."
    }
}

function Get-VercelEnvNames {
    param([string]$TargetEnvironment)

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $json = (& vercel.cmd env ls $TargetEnvironment --format=json 2>$null | Out-String).Trim()
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw "Failed to list Vercel env vars for $TargetEnvironment."
    }
    if ([string]::IsNullOrWhiteSpace($json)) {
        return @()
    }

    $payload = $json | ConvertFrom-Json
    return @(
        $payload.envs | ForEach-Object {
            if ($_.key) {
                $_.key
            } elseif ($_.name) {
                $_.name
            }
        }
    )
}

function Set-VercelEnv {
    param(
        [string]$Name,
        [string]$Value,
        [string]$TargetEnvironment,
        [string[]]$ExistingNames
    )

    $previousErrorActionPreference = $ErrorActionPreference
    if ($ExistingNames -contains $Name) {
        Write-Host "Updating Vercel env var $Name for $TargetEnvironment"
        try {
            $ErrorActionPreference = "Continue"
            $Value | & vercel.cmd env update $Name $TargetEnvironment --sensitive --yes | Out-Host
            $exitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
    } else {
        Write-Host "Adding Vercel env var $Name for $TargetEnvironment"
        try {
            $ErrorActionPreference = "Continue"
            $Value | & vercel.cmd env add $Name $TargetEnvironment --sensitive --yes | Out-Host
            $exitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
    }

    if ($exitCode -ne 0) {
        throw "Failed to set Vercel env var $Name."
    }
}

function New-PublicDefaultVercelEnvVars {
    $vars = [ordered]@{
        REQUIRE_DURABLE_DATABASE = "true"
        REQUIRE_DURABLE_OBJECT_STORAGE = "true"
        API_AUTH_ENABLED = "true"
        CORS_ALLOWED_ORIGINS = $CorsAllowedOrigins
        RATE_LIMIT_ENABLED = $RateLimitEnabled
        RATE_LIMIT_WINDOW_SECONDS = $RateLimitWindowSeconds
        RATE_LIMIT_CHAT_REQUESTS = $RateLimitChatRequests
        RATE_LIMIT_UPLOAD_REQUESTS = $RateLimitUploadRequests
        BOOTSTRAP_DEMO_SOURCE_LIBRARY = "false"
        EMBEDDING_PROVIDER = $EmbeddingProvider
        EMBEDDING_DIMENSIONS = $EmbeddingDimensions
        EMBEDDING_TIMEOUT_SECONDS = $EmbeddingTimeoutSeconds
        OPENAI_BASE_URL = $OpenAiBaseUrl
        S3_REGION = $S3Region
        S3_BUCKET_RAW_SOURCES = $(if ($env:S3_BUCKET_RAW_SOURCES) { $env:S3_BUCKET_RAW_SOURCES } else { "raw-sources" })
        S3_BUCKET_PARSED_SOURCES = $(if ($env:S3_BUCKET_PARSED_SOURCES) { $env:S3_BUCKET_PARSED_SOURCES } else { "parsed-sources" })
        S3_BUCKET_UPLOADS = $(if ($env:S3_BUCKET_UPLOADS) { $env:S3_BUCKET_UPLOADS } else { "uploads" })
        S3_BUCKET_EXPORTS = $(if ($env:S3_BUCKET_EXPORTS) { $env:S3_BUCKET_EXPORTS } else { "exports" })
    }
    if (-not [string]::IsNullOrWhiteSpace($EmbeddingModel)) {
        $vars["EMBEDDING_MODEL"] = $EmbeddingModel
    }
    return $vars
}

function Set-VercelEnvVars {
    param(
        [System.Collections.IDictionary]$EnvVars,
        [string]$TargetEnvironment
    )

    $existingNames = Get-VercelEnvNames -TargetEnvironment $TargetEnvironment
    foreach ($entry in $EnvVars.GetEnumerator()) {
        Set-VercelEnv -Name $entry.Key -Value $entry.Value -TargetEnvironment $TargetEnvironment -ExistingNames $existingNames
        if ($existingNames -notcontains $entry.Key) {
            $existingNames += $entry.Key
        }
    }
}

function Invoke-VercelProductionDeploy {
    Write-Host "Deploying production build"
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & vercel.cmd deploy --prod --yes | Out-Host
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw "Production deployment failed."
    }
}

function Get-WorkspacePython {
    $venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Invoke-DurableDatabaseMigrations {
    param([string]$ResolvedDatabaseUrl)

    $previousDatabaseUrl = $env:DATABASE_URL
    $previousBootstrap = $env:BOOTSTRAP_DEMO_SOURCE_LIBRARY
    $python = Get-WorkspacePython

    try {
        $env:DATABASE_URL = $ResolvedDatabaseUrl
        $env:BOOTSTRAP_DEMO_SOURCE_LIBRARY = "false"
        Write-Host "Applying durable database migrations"
        & $python -c "from draftcheck_core.database import init_database; init_database()" | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Durable database migration failed."
        }
    } finally {
        $env:DATABASE_URL = $previousDatabaseUrl
        $env:BOOTSTRAP_DEMO_SOURCE_LIBRARY = $previousBootstrap
    }
}

if ($PublicDefaultsOnly) {
    $publicEnvVars = New-PublicDefaultVercelEnvVars
    Set-VercelEnvVars -EnvVars $publicEnvVars -TargetEnvironment $Environment

    if ($Deploy) {
        Invoke-VercelProductionDeploy
    }

    if (-not $SkipReadyCheck) {
        Write-Host "Public defaults only configured. Skipping full /ready success check because DATABASE_URL, API_AUTH_KEYS, S3_ENDPOINT_URL, and S3 credentials may still be absent."
    }
    return
}

$DatabaseUrl = Resolve-DatabaseUrl

Assert-ConfiguredSecret "DRAFTCHECK_DATABASE_URL or SUPABASE_DB_PASSWORD with a linked Supabase pooler URL" $DatabaseUrl
Assert-ConfiguredSecret "CORS_ALLOWED_ORIGINS" $CorsAllowedOrigins
Assert-ConfiguredSecret "S3_ENDPOINT_URL" $env:S3_ENDPOINT_URL
Assert-ConfiguredSecret "S3_ACCESS_KEY_ID" $env:S3_ACCESS_KEY_ID
Assert-ConfiguredSecret "S3_SECRET_ACCESS_KEY" $env:S3_SECRET_ACCESS_KEY
if ($EmbeddingProvider.Trim().ToLowerInvariant() -in @("openai", "openai-compatible")) {
    Assert-ConfiguredSecret "OPENAI_API_KEY" $OpenAiApiKey
}

Assert-UsablePostgresDatabaseUrl -ResolvedDatabaseUrl $DatabaseUrl

$ApiAuthKeys = Resolve-ApiAuthKeys
Assert-ConfiguredSecret "DRAFTCHECK_API_AUTH_KEYS" $ApiAuthKeys
Assert-ProductionApiAuthKeys -Keys $ApiAuthKeys

if (-not $SkipMigrations) {
    Invoke-DurableDatabaseMigrations -ResolvedDatabaseUrl $DatabaseUrl
}

$envVars = New-PublicDefaultVercelEnvVars
$envVars["DATABASE_URL"] = $DatabaseUrl
$envVars["API_AUTH_KEYS"] = $ApiAuthKeys
if (-not [string]::IsNullOrWhiteSpace($OpenAiApiKey)) {
    $envVars["OPENAI_API_KEY"] = $OpenAiApiKey
}

$optionalS3Vars = @(
    "S3_ENDPOINT_URL",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_SESSION_TOKEN",
    "S3_BUCKET_RAW_SOURCES",
    "S3_BUCKET_PARSED_SOURCES",
    "S3_BUCKET_UPLOADS",
    "S3_BUCKET_EXPORTS"
)
foreach ($name in $optionalS3Vars) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        $envVars[$name] = $value
    }
}

Set-VercelEnvVars -EnvVars $envVars -TargetEnvironment $Environment

if ($SeedGoldenEvals -or $RunGoldenEvals) {
    $previousDatabaseUrl = $env:DATABASE_URL
    $previousBootstrap = $env:BOOTSTRAP_DEMO_SOURCE_LIBRARY
    $env:DATABASE_URL = $DatabaseUrl
    $env:BOOTSTRAP_DEMO_SOURCE_LIBRARY = "true"
    $python = Get-WorkspacePython
    try {
        if ($SeedGoldenEvals) {
            Write-Host "Seeding golden eval cases into the durable database"
            & $python scripts/seed_golden_evals.py $GoldenEvalPath | Out-Host
            if ($LASTEXITCODE -ne 0) {
                throw "Golden eval seeding failed."
            }
        }
        if ($RunGoldenEvals) {
            Write-Host "Running golden eval track '$GoldenEvalTrack' against the durable database"
            & $python scripts/run_golden_evals.py --track $GoldenEvalTrack --run-by "vercel-production-bootstrap" | Out-Host
            if ($LASTEXITCODE -ne 0) {
                throw "Golden eval run failed."
            }
        }
    } finally {
        $env:DATABASE_URL = $previousDatabaseUrl
        $env:BOOTSTRAP_DEMO_SOURCE_LIBRARY = $previousBootstrap
    }
}

if ($Deploy) {
    Invoke-VercelProductionDeploy
}

if (-not $SkipReadyCheck) {
    $readyUrl = "$($ProductionUrl.TrimEnd('/'))/ready"
    Write-Host "Checking $readyUrl"
    try {
        $ready = Invoke-RestMethod -Method Get -Uri $readyUrl -TimeoutSec 30
        if ($ready.status -ne "ok") {
            throw "Ready status was '$($ready.status)'."
        }
        Write-Host "Production readiness check passed."
    } catch {
        $detail = $_.ErrorDetails.Message
        if ([string]::IsNullOrWhiteSpace($detail)) {
            $detail = $_.Exception.Message
        }
        throw "Production readiness check failed: $detail"
    }
}

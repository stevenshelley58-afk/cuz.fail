param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [string]$ComposeFile = "docker-compose.yml",
    [string]$ProjectName = "draftcheck-wa-core",
    [string]$DbUser = "draftcheck",
    [string]$DbName = "draftcheck",
    [ValidateSet("local", "production")]
    [string]$Environment = "local",
    [switch]$CleanMachineRestore,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$startedAt = Get-Date
$resolvedBackup = Resolve-Path $BackupDir
$dbBackup = Join-Path $resolvedBackup "postgres.dump"
$minioBackup = Join-Path $resolvedBackup "minio"
$manifest = Join-Path $resolvedBackup "manifest.sha256"

if (-not (Test-Path $dbBackup)) {
    throw "Missing database backup: $dbBackup"
}

if (-not (Test-Path $minioBackup)) {
    throw "Missing MinIO backup directory: $minioBackup"
}

if (Test-Path $manifest) {
    Write-Host "Validating SHA-256 manifest..."
    Get-Content $manifest | ForEach-Object {
        $parts = $_ -split " ", 2
        if ($parts.Count -ne 2) {
            throw "Invalid manifest line: $_"
        }
        $path = Join-Path $resolvedBackup $parts[1]
        $actual = (Get-FileHash -Algorithm SHA256 -Path $path).Hash
        if ($actual -ne $parts[0]) {
            throw "Checksum mismatch: $($parts[1])"
        }
    }
}

if (-not $Force) {
    $answer = Read-Host "Restore overwrites the local DB and MinIO buckets for project '$ProjectName'. Type RESTORE to continue"
    if ($answer -ne "RESTORE") {
        Write-Host "Restore cancelled."
        exit 1
    }
}

Write-Host "Restoring database from $dbBackup"
docker compose -f $ComposeFile --project-name $ProjectName cp $dbBackup db:/tmp/draftcheck-restore.dump
docker compose -f $ComposeFile --project-name $ProjectName exec -T db `
    pg_restore -U $DbUser -d $DbName --clean --if-exists --no-owner --no-acl /tmp/draftcheck-restore.dump
docker compose -f $ComposeFile --project-name $ProjectName exec -T db rm -f /tmp/draftcheck-restore.dump

Write-Host "Restoring MinIO buckets from $minioBackup"
docker compose -f $ComposeFile --project-name $ProjectName run --rm `
    --entrypoint /bin/sh `
    -v "$((Resolve-Path $minioBackup).Path):/backup:ro" `
    minio-init -c "mc alias set local http://minio:9000 `$MINIO_ROOT_USER `$MINIO_ROOT_PASSWORD >/dev/null && mc mirror --overwrite /backup local"

$durationSeconds = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 3)
$checksumValidated = if (Test-Path $manifest) { "true" } else { "false" }
$manifestHash = if (Test-Path $manifest) { (Get-FileHash -Algorithm SHA256 -Path $manifest).Hash } else { "" }

Write-Host "Recording restore audit event"
docker compose -f $ComposeFile --project-name $ProjectName run --rm api `
    python scripts/record_infra_event.py `
    --action infra.restore.completed `
    --target-id $((Split-Path -Leaf $resolvedBackup.Path)) `
    --metadata "backup_dir=$($resolvedBackup.Path)" `
    --metadata "environment=$Environment" `
    --metadata "clean_machine_restore=$($CleanMachineRestore.IsPresent.ToString().ToLowerInvariant())" `
    --metadata "checksum_validated=$checksumValidated" `
    --metadata "manifest_sha256=$manifestHash" `
    --metadata "duration_seconds=$durationSeconds"

Write-Host "Restore complete."

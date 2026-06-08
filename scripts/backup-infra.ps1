param(
    [string]$ComposeFile = "docker-compose.yml",
    [string]$ProjectName = "draftcheck-wa-core",
    [string]$BackupRoot = ".backups",
    [string]$DbUser = "draftcheck",
    [string]$DbName = "draftcheck",
    [ValidateSet("local", "production")]
    [string]$Environment = "local",
    [switch]$Offsite,
    [switch]$Encrypted,
    [switch]$ScheduledDaily
)

$ErrorActionPreference = "Stop"

$startedAt = Get-Date
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $BackupRoot $timestamp
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$dbBackup = Join-Path $backupDir "postgres.dump"
$minioBackup = Join-Path $backupDir "minio"
$manifest = Join-Path $backupDir "manifest.sha256"

Write-Host "Writing database backup to $dbBackup"
docker compose -f $ComposeFile --project-name $ProjectName exec -T db `
    pg_dump -U $DbUser -d $DbName --format=custom --no-owner --no-acl --file=/tmp/draftcheck-postgres.dump
docker compose -f $ComposeFile --project-name $ProjectName cp db:/tmp/draftcheck-postgres.dump $dbBackup
docker compose -f $ComposeFile --project-name $ProjectName exec -T db rm -f /tmp/draftcheck-postgres.dump

Write-Host "Mirroring MinIO buckets to $minioBackup"
New-Item -ItemType Directory -Force -Path $minioBackup | Out-Null
docker compose -f $ComposeFile --project-name $ProjectName run --rm `
    --entrypoint /bin/sh `
    -v "$((Resolve-Path $minioBackup).Path):/backup" `
    minio-init -c "mc alias set local http://minio:9000 `$MINIO_ROOT_USER `$MINIO_ROOT_PASSWORD >/dev/null && mc mirror --overwrite local /backup"

Write-Host "Writing SHA-256 manifest"
Get-ChildItem -Path $backupDir -Recurse -File |
    Where-Object { $_.FullName -ne (Resolve-Path -Path $manifest -ErrorAction SilentlyContinue) } |
    ForEach-Object {
        $hash = Get-FileHash -Algorithm SHA256 -Path $_.FullName
        "$($hash.Hash) $($_.FullName.Substring((Resolve-Path $backupDir).Path.Length + 1))"
    } | Set-Content -Path $manifest -Encoding UTF8

$manifestHash = (Get-FileHash -Algorithm SHA256 -Path $manifest).Hash
$durationSeconds = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 3)

Write-Host "Recording backup audit event"
docker compose -f $ComposeFile --project-name $ProjectName run --rm api `
    python scripts/record_infra_event.py `
    --action infra.backup.completed `
    --target-id $timestamp `
    --metadata "backup_dir=$((Resolve-Path $backupDir).Path)" `
    --metadata "environment=$Environment" `
    --metadata "offsite=$($Offsite.IsPresent.ToString().ToLowerInvariant())" `
    --metadata "encrypted=$($Encrypted.IsPresent.ToString().ToLowerInvariant())" `
    --metadata "schedule=$(if ($ScheduledDaily.IsPresent) { 'daily' } else { 'manual' })" `
    --metadata "db_backup=postgres.dump" `
    --metadata "minio_backup=minio" `
    --metadata "manifest_sha256=$manifestHash" `
    --metadata "duration_seconds=$durationSeconds"

Write-Host "Backup complete: $backupDir"

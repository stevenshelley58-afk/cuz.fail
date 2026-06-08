from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


PYTHONPATH = os.pathsep.join(
    [
        "apps/api",
        "apps/worker",
        "packages/core",
        "packages/ingestion",
        "packages/retrieval",
        "packages/compliance",
        "packages/document_ai",
        "packages/export",
        "packages/scraper",
        "packages/shared_schemas",
    ]
)


def test_record_infra_event_script_writes_audit_event(tmp_path):
    db_path = tmp_path / "audit.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "PYTHONPATH": PYTHONPATH,
    }

    result = subprocess.run(
        [
            sys.executable,
            "scripts/record_infra_event.py",
            "--action",
            "infra.backup.completed",
            "--target-id",
            "20260606-120000",
            "--metadata",
            "duration_seconds=1.25",
            "--metadata",
            "checksum_validated=true",
        ],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    with engine.connect() as conn:
        row = conn.execute(
            text("select action, target_type, target_id, metadata_json from audit_events")
        ).one()
    assert row.action == "infra.backup.completed"
    assert row.target_type == "infrastructure"
    assert row.target_id == "20260606-120000"
    assert json.loads(row.metadata_json) == {
        "duration_seconds": 1.25,
        "checksum_validated": True,
    }


def test_backup_restore_scripts_record_ops_audit_events():
    backup_script = Path("scripts/backup-infra.ps1").read_text(encoding="utf-8")
    restore_script = Path("scripts/restore-infra.ps1").read_text(encoding="utf-8")

    assert "scripts/record_infra_event.py" in backup_script
    assert "--action infra.backup.completed" in backup_script
    assert "environment=$Environment" in backup_script
    assert "offsite=" in backup_script
    assert "encrypted=" in backup_script
    assert "schedule=" in backup_script
    assert "manifest_sha256=" in backup_script
    assert "duration_seconds=" in backup_script

    assert "scripts/record_infra_event.py" in restore_script
    assert "--action infra.restore.completed" in restore_script
    assert "environment=$Environment" in restore_script
    assert "clean_machine_restore=" in restore_script
    assert "checksum_validated=" in restore_script
    assert "duration_seconds=" in restore_script

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def test_v3_authority_is_locked_in_active_agent_docs() -> None:
    agents = read("AGENTS.md")
    readme = read("README.md")

    assert "docs/MASTER_REBUILD_PLAN.md" in agents
    assert "DATA_INVENTORY.md" in agents
    assert "docs/MASTER_REBUILD_PLAN.md" in readme
    assert "This repo intentionally contains no frontend" not in readme


def test_superseded_authority_docs_warn_near_top() -> None:
    for path in [
        "docs/REBUILD_SPEC.md",
    ]:
        first_page = "\n".join(read(path).splitlines()[:12])
        assert "SUPERSEDED" in first_page
        assert "docs/MASTER_REBUILD_PLAN.md" in first_page


def test_ignore_rules_cover_runtime_and_private_artifacts() -> None:
    gitignore = read(".gitignore")
    dockerignore = read(".dockerignore")
    required = [
        ".venv",
        ".vercel",
        "build",
        "backups",
        "*.db-wal",
        "*.db-shm",
        ".storage",
        "data/corpus",
        ".import_linter_cache",
    ]

    for pattern in required:
        assert pattern in gitignore
        assert pattern in dockerignore


def test_precommit_guard_blocks_dangerous_paths() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "precommit_guard.py"),
            "draftcheck.db",
            ".storage/projects/example",
            ".vercel/.env.production.local",
            "data/corpus/example.pdf",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1
    assert "draftcheck.db" in result.stderr
    assert ".storage/projects/example" in result.stderr
    assert ".vercel/.env.production.local" in result.stderr
    assert "data/corpus/example.pdf" in result.stderr

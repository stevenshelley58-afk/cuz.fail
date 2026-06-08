from __future__ import annotations

import os
import shutil
import sys
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

for package_path in [
    ROOT / "apps" / "api",
    ROOT / "apps" / "worker",
    ROOT / "packages" / "core",
    ROOT / "packages" / "ingestion",
    ROOT / "packages" / "retrieval",
    ROOT / "packages" / "compliance",
    ROOT / "packages" / "document_ai",
    ROOT / "packages" / "export",
    ROOT / "packages" / "scraper",
    ROOT / "packages" / "shared_schemas",
]:
    sys.path.insert(0, str(package_path))

seed_db = ROOT / "draftcheck.db"
runtime_db = Path("/tmp/draftcheck.db")


def _file_sha256(path: Path) -> bytes:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


if seed_db.exists() and (
    not runtime_db.exists() or _file_sha256(seed_db) != _file_sha256(runtime_db)
):
    shutil.copyfile(seed_db, runtime_db)

os.environ.setdefault("DATABASE_URL", f"sqlite:///{runtime_db.as_posix()}")
os.environ.setdefault("OBJECT_STORAGE_ROOT", "/tmp/draftcheck-storage")
os.environ.setdefault("REQUIRE_DURABLE_DATABASE", "true")
os.environ.setdefault("REQUIRE_DURABLE_OBJECT_STORAGE", "true")
os.environ.setdefault("BOOTSTRAP_DEMO_SOURCE_LIBRARY", "false")

from draftcheck_api.main import app  # noqa: E402

__all__ = ["app"]

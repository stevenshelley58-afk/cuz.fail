from __future__ import annotations

from pathlib import Path

from draftcheck_core.database import SessionLocal, init_database
from draftcheck_ingestion.service import SourceIngestionService


def main() -> None:
    init_database()
    manifest = Path("data/seed/source_manifest.example.yaml").read_text(encoding="utf-8")
    with SessionLocal() as db:
        results = SourceIngestionService(db).import_manifest_yaml(manifest)
        db.commit()
    print(f"Imported {len(results)} source entries")


if __name__ == "__main__":
    main()

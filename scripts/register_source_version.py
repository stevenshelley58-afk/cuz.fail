"""Register a new source version from a fetched PDF/URL.

Creates SourceDocument (or finds existing), SourceVersion, content-addressed
artifact, and source chunks with embeddings.

Usage:
    python scripts/register_source_version.py \
        --title "Residential Design Codes Volume 1 (April 2026)" \
        --authority "Department of Planning, Lands and Heritage" \
        --source-type r_code \
        --jurisdiction WA \
        --licence-status verified_open \
        --pdf-path data/raw-sources/rcodes_vol1_april2026.pdf \
        --effective-from 2026-04-10 \
        --version-label "2026-04-amended"

Prints the source_version_id for downstream scripts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]", file=sys.stderr)
    sys.exit(1)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def content_addressed_path(storage_root: Path, sha: str) -> Path:
    """Return storage_path = sha256[:2]/sha256."""
    return storage_root / sha[:2] / sha


def store_pdf(pdf_path: Path, storage_root: Path, sha: str) -> Path:
    dest = content_addressed_path(storage_root, sha)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(pdf_path, dest)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Register a new source version.")
    parser.add_argument("--title", required=True, help="Source document title")
    parser.add_argument("--authority", required=True, help="Publishing authority")
    parser.add_argument("--source-type", required=True, help="e.g. r_code, ncc, dcp, local_policy")
    parser.add_argument("--jurisdiction", default="WA", help="Jurisdiction code")
    parser.add_argument(
        "--licence-status", default="pending_review",
        choices=["verified_open", "pending_review", "restricted", "metadata_only"],
    )
    parser.add_argument("--pdf-path", required=True, help="Path to the PDF file")
    parser.add_argument("--effective-from", help="ISO date (e.g. 2026-04-10)")
    parser.add_argument("--version-label", help="Human version label")
    parser.add_argument("--canonical-url", help="Official URL of the source")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without DB writes")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    sha = sha256_file(pdf_path)
    storage_root = Path(os.getenv("DRAFTCHECK_STORAGE_ROOT", "/srv/draftcheck/storage"))
    effective_from = (
        datetime.fromisoformat(args.effective_from).replace(tzinfo=timezone.utc)
        if args.effective_from else None
    )

    if args.dry_run:
        print(f"[DRY RUN] Would register source version:")
        print(f"  title:          {args.title}")
        print(f"  authority:      {args.authority}")
        print(f"  source_type:    {args.source_type}")
        print(f"  jurisdiction:   {args.jurisdiction}")
        print(f"  licence_status: {args.licence_status}")
        print(f"  sha256:         {sha}")
        print(f"  effective_from: {effective_from}")
        print(f"  version_label:  {args.version_label}")
        print(f"  storage_path:   {content_addressed_path(storage_root, sha)}")
        return 0

    db_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(db_url) as conn:
        cur = conn.cursor()

        # 1. Store PDF in content-addressed tree
        stored_path = store_pdf(pdf_path, storage_root, sha)
        print(f"Stored PDF: {stored_path}")

        # 2. Find or create SourceDocument
        cur.execute(
            "SELECT id FROM source_documents WHERE title = %s AND authority = %s",
            (args.title, args.authority),
        )
        row = cur.fetchone()
        if row:
            source_id = str(row[0])
            print(f"Found existing source document: {source_id}")
        else:
            source_id = str(uuid4())
            cur.execute(
                """INSERT INTO source_documents
                   (id, title, jurisdiction, authority, source_type, canonical_url,
                    access_type, status, metadata_json, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, 'public', 'active', '{}', now(), now())""",
                (source_id, args.title, args.jurisdiction, args.authority,
                 args.source_type, args.canonical_url),
            )
            print(f"Created source document: {source_id}")

        # 3. Check for existing version with same sha
        cur.execute(
            "SELECT id FROM source_versions WHERE source_id = %s AND sha256 = %s",
            (source_id, sha),
        )
        existing = cur.fetchone()
        if existing:
            print(f"Source version already exists: {existing[0]}")
            print(f"source_version_id={existing[0]}")
            conn.commit()
            return 0

        # 4. Create SourceVersion
        version_id = str(uuid4())
        cur.execute(
            """INSERT INTO source_versions
               (id, source_id, version_label, sha256, storage_manifest_json,
                licence_status, review_status, effective_from, fetched_at,
                metadata_json, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, 'pending_review', %s, now(), '{}', now(), now())""",
            (
                version_id, source_id, args.version_label, sha,
                json.dumps({"storage_path": str(stored_path), "kind": "raw_pdf"}),
                args.licence_status, effective_from,
            ),
        )
        print(f"Created source version: {version_id}")

        # 5. Create ContentAddressedArtifact
        artifact_id = str(uuid4())
        cur.execute(
            """INSERT INTO content_addressed_artifacts
               (id, sha256, kind, storage_path, byte_size, metadata_json, created_at, updated_at)
               VALUES (%s, %s, 'raw_pdf', %s, %s, '{}', now(), now())
               ON CONFLICT (sha256, kind) DO NOTHING""",
            (artifact_id, sha, str(stored_path), pdf_path.stat().st_size),
        )

        conn.commit()
        print(f"\nsource_version_id={version_id}")
        print("NOTE: Operator must approve this source version (review_status → approved)")
        print("      before rules extracted from it can be cited.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

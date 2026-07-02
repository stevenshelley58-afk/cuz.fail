"""WP4 — acquisition worker: drain pending target_manifest rows via lawful fetch.

DB_BUILDOUT_AGENT_PLAN WP4 / CORPUS_COMPLETENESS_PLAN Phase 2. Claims pending
``target_manifest`` rows (FOR UPDATE SKIP LOCKED lease), runs the existing
single-insertion-path pipeline (fetch_public_source -> import_source -> chunks
+ embeddings -> raw artifact -> source_fetch_log), then terminates the row:

  - success                  -> status='acquired', source_document_id set
  - HTTP 401/402/403         -> status='metadata_only' (licensed/paid; no full text)
  - 3 failed attempts        -> status='blocked', notes carry the error + the
                                one-command unblock (re-run this script)
  - no canonical_url         -> status='blocked' with a discovery note

Idempotent: import_source dedupes by content hash; re-running is safe. Workers
never talk to each other — the manifest table is the queue.

Run inside the api container:
    python /app/scripts/wp4_acquire.py [--limit N] [--worker-id NAME] \
        --report /app/reports/wp4_acquisition.json
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import traceback
from typing import Any
from uuid import UUID

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import httpx  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from draftcheck.domain.address.lga import canonical_local_government_name  # noqa: E402
from draftcheck.domain.identity.sqlalchemy_store import SqlAlchemyIdentityStore  # noqa: E402
from draftcheck.domain.identity.roles import IdentityRole  # noqa: E402
from draftcheck.domain.sources.fetching import fetch_public_source  # noqa: E402
from draftcheck.domain.sources.models import LicenceStatus, SourceReviewStatus  # noqa: E402
from draftcheck.domain.sources.sqlalchemy_store import SqlAlchemySourceLibrary  # noqa: E402

OPERATOR_EMAIL = os.environ.get("WP4_OPERATOR_EMAIL", "ops@lotfile.app")
ORG_SLUG = os.environ.get("WP4_ORG_SLUG", "draftcheck-wa")
ORG_NAME = os.environ.get("WP4_ORG_NAME", "DraftCheck WA")
MAX_ATTEMPTS = 3
MIN_CHUNKS = 3  # fewer than this on a fresh fetch => suspected index/landing page
RESTRICTED_HTTP = ("401", "402", "403")


def _local_government_for(issuing_authority: str | None) -> str | None:
    """Council-issued instruments get tagged with their canonical LGA name.

    State bodies (WAPC, DPLH, Parliament) return None so their docs stay global.
    """
    authority = str(issuing_authority or "").strip()
    if authority.lower().startswith(("city of ", "town of ", "shire of ")):
        return canonical_local_government_name(authority) or authority
    return None

CLAIM_SQL = text(
    """
    UPDATE target_manifest SET claimed_by = :worker, lease_expires_at = now() + interval '30 minutes'
    WHERE id = (
        SELECT id FROM target_manifest
        WHERE status = 'pending'
          AND (lease_expires_at IS NULL OR lease_expires_at < now())
        ORDER BY category, instrument_name
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id, instrument_name, category, issuing_authority, canonical_url, notes
    """
)

TERMINATE_SQL = text(
    """
    UPDATE target_manifest
    SET status = :status, source_document_id = :doc_id, notes = :notes,
        last_checked_at = now(), claimed_by = NULL, lease_expires_at = NULL,
        updated_at = now()
    WHERE id = :id
    """
)


def operator_ids(database_url: str) -> tuple[UUID, UUID]:
    store = SqlAlchemyIdentityStore.from_database_url(database_url)
    org = store.get_or_create_org(slug=ORG_SLUG, name=ORG_NAME)
    user = store.get_or_create_user(org=org, email=OPERATOR_EMAIL, role=IdentityRole.OWNER)
    return org.id, user.id


def acquire_one(
    library: SqlAlchemySourceLibrary,
    row: dict[str, Any],
    org_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """Fetch + import one manifest row. Returns terminal disposition."""
    url = (row["canonical_url"] or "").strip()
    if not url:
        return {"status": "blocked", "doc_id": None,
                "notes": "No canonical_url — needs discovery. UNBLOCK: set canonical_url, "
                         "reset status='pending', re-run scripts/wp4_acquire.py"}

    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            public_source = fetch_public_source(url, licence_notes="")
            result = library.import_source(
                title=str(row["instrument_name"]),
                content=public_source.text,
                uri=url,
                publisher=str(row["issuing_authority"] or ""),
                licence_status=LicenceStatus.PENDING_REVIEW,
                review_status=SourceReviewStatus.PENDING_REVIEW,
                media_type="text/plain",
                metadata_only=False,
                jurisdiction="WA",
                authority=str(row["issuing_authority"] or ""),
                local_government=_local_government_for(row["issuing_authority"]),
                source_type=str(row["category"]),
                access_type="public",
                licence_notes="",
                version_label=f"fetched:{public_source.sha256[:12]}",
                source_metadata={"wp4": True, "target_manifest_id": str(row["id"])},
                version_metadata=public_source.metadata,
            )
            library.record_raw_fetch_artifact(
                source_id=result.source.id,
                source_version_id=result.version.id,
                content=public_source.content,
                content_type=public_source.content_type,
                final_url=public_source.final_url,
                metadata=public_source.metadata,
            )
            library.record_fetch_log(
                source_id=result.source.id,
                source_version_id=result.version.id,
                org_id=org_id,
                requested_by_user_id=user_id,
                fetch_kind="public_source_fetch",
                status="success",
                metadata=public_source.metadata,
                completed=True,
            )
            if len(result.chunks) < MIN_CHUNKS and not result.duplicate:
                # A statute or policy that parses to a couple of chunks is almost
                # certainly an index/landing page, not the instrument itself.
                return {"status": "blocked", "doc_id": result.source.id,
                        "notes": f"Suspected landing page ({len(result.chunks)} chunks from {url}). "
                                 "UNBLOCK: set canonical_url to the document itself (PDF), "
                                 "reset status='pending', re-run scripts/wp4_acquire.py"}
            return {"status": "acquired", "doc_id": result.source.id,
                    "notes": f"WP4 acquired ({len(result.chunks)} chunks, "
                             f"duplicate={result.duplicate})",
                    "chunks": len(result.chunks), "duplicate": result.duplicate}
        except (httpx.HTTPError, ValueError) as exc:
            last_error = str(exc)
            if any(code in last_error for code in RESTRICTED_HTTP):
                return {"status": "metadata_only", "doc_id": None,
                        "notes": f"Access-restricted ({last_error[:200]}); full text not stored"}

    return {"status": "blocked", "doc_id": None,
            "notes": f"{MAX_ATTEMPTS} fetch attempts failed: {last_error[:300]}. "
                     "UNBLOCK: re-run scripts/wp4_acquire.py (or fix canonical_url)"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max manifest rows to process (0 = drain)")
    ap.add_argument("--worker-id", default=f"wp4-{socket.gethostname()}")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    database_url = os.environ["DATABASE_URL"]
    org_id, user_id = operator_ids(database_url)
    library = SqlAlchemySourceLibrary.from_database_url(database_url)
    engine = create_engine(database_url)

    summary: dict[str, int] = {"acquired": 0, "metadata_only": 0, "blocked": 0, "errors": 0}
    items: list[dict[str, Any]] = []
    processed = 0

    while args.limit == 0 or processed < args.limit:
        with engine.begin() as conn:
            claimed = conn.execute(CLAIM_SQL, {"worker": args.worker_id}).mappings().first()
        if claimed is None:
            break
        row = dict(claimed)
        processed += 1
        print(f"[{processed}] {row['category']}: {row['instrument_name'][:70]}", flush=True)
        try:
            outcome = acquire_one(library, row, org_id, user_id)
        except Exception as exc:  # worker must never stall the queue
            traceback.print_exc()
            outcome = {"status": "blocked", "doc_id": None,
                       "notes": f"Unexpected worker error: {str(exc)[:300]}. "
                                "UNBLOCK: re-run scripts/wp4_acquire.py"}
            summary["errors"] += 1
        with engine.begin() as conn:
            conn.execute(TERMINATE_SQL, {
                "id": row["id"], "status": outcome["status"],
                "doc_id": outcome["doc_id"], "notes": outcome["notes"],
            })
        summary[outcome["status"]] = summary.get(outcome["status"], 0) + 1
        items.append({"manifest_id": str(row["id"]), "instrument": row["instrument_name"],
                      "category": row["category"], **{k: str(v) for k, v in outcome.items()}})

    with engine.connect() as conn:
        remaining = conn.execute(
            text("SELECT status, count(*) FROM target_manifest GROUP BY 1")
        ).fetchall()
    report = {"wp": "WP4", "worker": args.worker_id, "processed": processed,
              "summary": summary, "manifest_status_after": dict(remaining), "items": items}
    out = json.dumps(report, indent=2, default=str)
    print(out)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

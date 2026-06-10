"""WP4 — acquisition runner for pending target_manifest rows (Phase 2 of
docs/CORPUS_COMPLETENESS_PLAN.md).

Runs INSIDE the api container (psycopg3 + DATABASE_URL present):

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp4_acquire.py \
        --report /app/reports/acquisition_report.json \
        [--limit N] [--category state_planning_policy] [--retry-blocked] \
        [--ids <uuid>,<uuid>] [--worker-id wp4-a] [--delay 1.0]

Behaviour (mechanical, per the plan — no judgment calls):
  1. Claims `pending` target_manifest rows through the lease columns
     (claimed_by / lease_expires_at) with FOR UPDATE SKIP LOCKED so multiple
     swarm workers can run concurrently without double-fetching.
  2. Each row goes through the EXISTING pipeline: lawful fetch
     (draftcheck.domain.sources.fetching — robots, licence, restricted-term
     checks) -> SqlAlchemySourceLibrary.import_source (source_documents ->
     source_versions sha256 -> artifacts -> chunks + citations + embeddings)
     -> record_raw_fetch_artifact -> record_fetch_log.
  3. Failure policy: fetch fails 3x -> status='blocked' with the error and a
     one-command unblock in notes; parse fails -> pymupdf/OCR repair attempt,
     still failing -> 'blocked' with the raw artifact preserved; paid/licensed
     (Standards Australia etc.) -> 'metadata_only'; success -> 'acquired' with
     source_document_id FK set. Every processed row updates last_checked_at.
  4. Idempotent: re-running only claims `pending` rows; acquired / blocked /
     metadata_only / out_of_scope rows are skipped unless --retry-blocked.
  5. Writes a JSON report (counts by category/status, per-row outcomes,
     escalations). Exit code 0 even with blocked rows — blocked is a valid
     terminal state; nonzero only on crash.

source_fetch_log rows require an existing source_documents row (NOT NULL FK),
so fetches that never produced a source row are recorded in the JSON report
only — this is the documented fallback, not a silent drop.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import traceback
from datetime import UTC, datetime
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import httpx  # noqa: E402
import psycopg  # noqa: E402

# Same DraftCheck WA org/system user used by WP3/WP6.
ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
USER_ID = "393277fe-3581-4a29-b394-a41cfc26f01b"

TERMINAL_STATUSES = ("acquired", "blocked", "metadata_only", "out_of_scope")
DEFAULT_REPORT_PATH = "/app/reports/acquisition_report.json"
RETRY_DELAYS = (2.0, 5.0)
MAX_FETCH_ATTEMPTS = 3
NOTE_MAX_CHARS = 2000

# Manifest category -> source_documents.source_type (vocabulary already in use
# by the source library / wp3_reconcile).
SOURCE_TYPE_BY_CATEGORY = {
    "act": "legislation",
    "regulations": "legislation",
    "region_scheme": "region_scheme",
    "state_planning_policy": "state_planning_policy",
    "dc_policy": "development_control_policy",
    "local_planning_scheme": "local_planning_scheme",
    "local_planning_policy": "local_planning_policy",
    "local_planning_strategy": "local_planning_strategy",
    "local_development_plan": "local_development_plan",
    "structure_plan": "structure_plan",
    "scheme_map": "scheme_map",
    "building_code": "building_code",
    "standard": "standard_metadata",
    "spatial_layer": "spatial_dataset",
    "council_page": "source_document",
    "index_page": "index_page",
}

# Notes markers that mean "paid / licence-blocked -> metadata_only" (Phase 2
# rule: record canonical metadata, never store full text).
PAID_LICENCE_MARKERS = (
    "paid",
    "licence-blocked",
    "license-blocked",
    "licence blocked",
    "subscription",
    "metadata only",
    "metadata-only",
    "metadata_only",
    "standards australia",
)

# fetch_public_source ValueError messages that will never succeed on retry.
PERMANENT_FETCH_MARKERS = (
    "robots.txt disallows",
    "requires restricted access",
    "restricted source URL",
    "private/local URLs",
    "only absolute public HTTP(S) URLs",
    "metadata-only unless lawfully supplied",
)

# Permanent errors that indicate a licensing wall rather than a broken URL.
LICENCE_ERROR_MARKERS = (
    "metadata-only unless lawfully supplied",
    "standards australia",
)

PARSE_FAILURE_MARKER = "no parseable text"


class PermanentFetchError(Exception):
    """Lawfulness/robots/licence failure — retrying will not help."""


class ParseFailure(Exception):
    """Fetch succeeded but produced no parseable text."""


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without Postgres)
# ---------------------------------------------------------------------------


def psycopg_dsn(raw: str) -> str:
    """Normalise a SQLAlchemy-style DATABASE_URL for psycopg.connect."""
    return raw.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def sqlalchemy_url(raw: str) -> str:
    """Normalise DATABASE_URL so SQLAlchemy uses the psycopg3 driver."""
    if raw.startswith("postgresql+psycopg://"):
        return raw
    if raw.startswith("postgresql+asyncpg://"):
        return raw.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    return raw.replace("postgresql://", "postgresql+psycopg://")


def build_claim_sql(
    *,
    category: str | None = None,
    ids: list[str] | None = None,
    retry_blocked: bool = False,
) -> str:
    """Atomic lease-claim over the target_manifest swarm queue.

    Only `pending` rows are claimable by default (terminal rows are skipped);
    --retry-blocked / --ids also reopen `blocked` rows. Rows already leased by
    a live worker (lease_expires_at in the future) are skipped, and FOR UPDATE
    SKIP LOCKED keeps concurrent workers from blocking on each other.
    """
    statuses = "('pending', 'blocked')" if (retry_blocked or ids) else "('pending')"
    where = [
        f"status IN {statuses}",
        "(claimed_by IS NULL OR lease_expires_at IS NULL OR lease_expires_at < now())",
    ]
    if category:
        where.append("category = %(category)s")
    if ids:
        where.append("id = ANY(%(ids)s::uuid[])")
    return (
        "UPDATE target_manifest SET claimed_by = %(worker_id)s, "
        "lease_expires_at = now() + make_interval(mins => %(lease_minutes)s), "
        "updated_at = now() "
        "WHERE id IN ("
        "SELECT id FROM target_manifest "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY category, instrument_name "
        "LIMIT %(batch_size)s "
        "FOR UPDATE SKIP LOCKED"
        ") "
        "RETURNING id, instrument_name, category, issuing_authority, index_source_url, "
        "canonical_url, expected_version_hint, status, notes"
    )


def classify_target(canonical_url: str | None, notes: str | None, category: str) -> str:
    """Pre-fetch classification: 'fetch' | 'metadata_only' | 'no_url'."""
    if not (canonical_url or "").strip():
        return "no_url"
    if category == "standard" or "standards.org.au" in canonical_url.lower():
        return "metadata_only"
    lowered_notes = (notes or "").lower()
    if any(marker in lowered_notes for marker in PAID_LICENCE_MARKERS):
        return "metadata_only"
    return "fetch"


def is_permanent_fetch_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker.lower() in lowered for marker in PERMANENT_FETCH_MARKERS)


def is_licence_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker.lower() in lowered for marker in LICENCE_ERROR_MARKERS)


def is_parse_failure(message: str) -> bool:
    return PARSE_FAILURE_MARKER in message.lower()


def unblock_command(manifest_id: str) -> str:
    return (
        "docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp4_acquire.py "
        f"--retry-blocked --ids {manifest_id} --report {DEFAULT_REPORT_PATH}"
    )


def unblock_hint(kind: str, manifest_id: str, canonical_url: str | None = None) -> str:
    """One-command unblock per mechanical failure class."""
    rerun = unblock_command(manifest_id)
    if kind == "no_url":
        return (
            f"set the URL then rerun: psql \"$DATABASE_URL\" -c \"UPDATE target_manifest "
            f"SET canonical_url='<url>', status='pending' WHERE id='{manifest_id}'\"; then {rerun}"
        )
    if kind == "robots":
        return f"robots.txt disallows automated fetch; manually verify {canonical_url} then {rerun}"
    if kind == "restricted":
        return (
            f"URL returned a restricted-access response; verify {canonical_url} in a browser, "
            f"update canonical_url if it moved, then {rerun}"
        )
    if kind == "parse":
        return f"raw artifact preserved; fix parser / OCR deps in the api image then {rerun}"
    return rerun


def format_blocked_note(*, error: str, unblock: str, attempts: int) -> str:
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    note = f"[wp4 {stamp}] BLOCKED after {attempts} attempt(s): {error} | unblock: {unblock}"
    return note[:NOTE_MAX_CHARS]


def format_metadata_only_note(reason: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    note = (
        f"[wp4 {stamp}] metadata_only: {reason}; canonical metadata recorded, "
        "full text never stored (CORPUS_COMPLETENESS_PLAN Phase 2 licence rule)"
    )
    return note[:NOTE_MAX_CHARS]


def source_type_for_category(category: str) -> str:
    return SOURCE_TYPE_BY_CATEGORY.get(category, "source_document")


def local_government_for_authority(authority: str) -> str | None:
    if authority.startswith(("City of ", "Town of ", "Shire of ")):
        return authority
    return None


def looks_like_pdf(content: bytes, content_type: str, final_url: str) -> bool:
    return (
        "pdf" in content_type.lower()
        or final_url.lower().endswith(".pdf")
        or content[:5] == b"%PDF-"
    )


def build_report(
    *,
    worker_id: str,
    args_summary: dict[str, Any],
    outcomes: list[dict[str, Any]],
    manifest_totals: dict[str, Any],
    escalations: list[str],
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_category: dict[str, dict[str, int]] = {}
    for outcome in outcomes:
        status = outcome["status"]
        category = outcome["category"]
        by_status[status] = by_status.get(status, 0) + 1
        by_category.setdefault(category, {})
        by_category[category][status] = by_category[category].get(status, 0) + 1
    return {
        "run": {
            "worker_id": worker_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "args": args_summary,
        },
        "counts": {
            "processed": len(outcomes),
            "by_status": by_status,
            "by_category_status": by_category,
        },
        "rows": outcomes,
        "escalations": escalations,
        "manifest_totals_after": manifest_totals,
    }


# ---------------------------------------------------------------------------
# Fetch / parse-repair (network; uses the existing lawful-fetch pipeline)
# ---------------------------------------------------------------------------


def lawful_fetch_with_retries(url: str, licence_notes: str, *, max_attempts: int = MAX_FETCH_ATTEMPTS):
    """fetch_public_source with the Phase 2 mechanical retry policy.

    Returns (PublicSourceFetch, attempts). Raises PermanentFetchError (no
    retry), ParseFailure (fetched but unreadable), or the last transient
    exception after max_attempts.
    """
    from draftcheck.domain.sources.fetching import fetch_public_source

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            time.sleep(RETRY_DELAYS[min(attempt - 2, len(RETRY_DELAYS) - 1)])
        try:
            return fetch_public_source(url, licence_notes=licence_notes, timeout_seconds=60.0), attempt
        except ValueError as exc:
            message = str(exc)
            if is_parse_failure(message):
                raise ParseFailure(message) from exc
            if is_permanent_fetch_error(message):
                raise PermanentFetchError(message) from exc
            last_exc = exc  # e.g. transient parse oddity — retry mechanically
        except httpx.HTTPError as exc:
            last_exc = exc
    raise RuntimeError(f"fetch failed after {max_attempts} attempts: {last_exc}") from last_exc


def raw_fetch_and_repair(url: str) -> tuple[bytes, str, str, str, dict[str, Any]]:
    """Re-fetch raw bytes (robots already validated) and attempt parse repair.

    Returns (content, content_type, final_url, repaired_text, repair_metadata);
    repaired_text is "" when both pymupdf and OCR repair fail.
    """
    from draftcheck.domain.sources.fetching import (
        USER_AGENT,
        extract_pdf_text_with_ocr,
        extract_pdf_text_with_pymupdf,
        sanitize_source_text,
    )

    with httpx.Client(
        follow_redirects=True, timeout=120.0, headers={"user-agent": USER_AGENT}
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.content
        content_type = response.headers.get("content-type", "application/octet-stream")
        final_url = str(response.url)

    text = ""
    metadata: dict[str, Any] = {"repair_attempted": True}
    if looks_like_pdf(content, content_type, final_url):
        for method, extractor in (
            ("pymupdf_text_layer", extract_pdf_text_with_pymupdf),
            ("pymupdf_render_tesseract_ocr", extract_pdf_text_with_ocr),
        ):
            try:
                extraction = extractor(content)
            except ValueError as exc:  # repair dependency unavailable
                metadata.setdefault("repair_errors", []).append(f"{method}: {exc}")
                continue
            candidate = sanitize_source_text(extraction.text)
            if candidate.strip():
                text = candidate
                metadata["repair_method"] = method
                metadata.update(extraction.metadata)
                break
            metadata.setdefault("repair_errors", []).append(f"{method}: no text")
    else:
        metadata["repair_errors"] = [f"unsupported content kind for repair: {content_type}"]
    return content, content_type, final_url, text, metadata


# ---------------------------------------------------------------------------
# DB plumbing
# ---------------------------------------------------------------------------


def build_library():
    """Existing service-layer source library on the same DATABASE_URL."""
    from draftcheck.domain.sources.store import SqlAlchemySourceLibrary

    return SqlAlchemySourceLibrary.from_database_url(sqlalchemy_url(os.environ["DATABASE_URL"]))


def claim_batch(
    conn: psycopg.Connection,
    *,
    worker_id: str,
    lease_minutes: int,
    batch_size: int,
    category: str | None,
    ids: list[str] | None,
    retry_blocked: bool,
) -> list[dict[str, Any]]:
    sql = build_claim_sql(category=category, ids=ids, retry_blocked=retry_blocked)
    params: dict[str, Any] = {
        "worker_id": worker_id,
        "lease_minutes": lease_minutes,
        "batch_size": batch_size,
    }
    if category:
        params["category"] = category
    if ids:
        params["ids"] = ids
    rows = conn.execute(sql, params).fetchall()
    conn.commit()
    columns = (
        "id", "instrument_name", "category", "issuing_authority", "index_source_url",
        "canonical_url", "expected_version_hint", "status", "notes",
    )
    return [dict(zip(columns, row, strict=True)) for row in rows]


def finalize_row(
    conn: psycopg.Connection,
    manifest_id: str,
    *,
    status: str,
    note: str | None,
    source_document_id: str | None,
) -> None:
    conn.execute(
        "UPDATE target_manifest SET status = %s, "
        "source_document_id = COALESCE(%s::uuid, source_document_id), "
        "notes = COALESCE(%s, notes), last_checked_at = now(), "
        "claimed_by = NULL, lease_expires_at = NULL, updated_at = now() "
        "WHERE id = %s",
        (status, source_document_id, note, manifest_id),
    )
    conn.commit()


def manifest_totals(conn: psycopg.Connection) -> dict[str, Any]:
    by_status = dict(
        conn.execute("SELECT status, count(*) FROM target_manifest GROUP BY status").fetchall()
    )
    by_category: dict[str, dict[str, int]] = {}
    for category, status, count in conn.execute(
        "SELECT category, status, count(*) FROM target_manifest GROUP BY category, status"
    ).fetchall():
        by_category.setdefault(category, {})[status] = count
    return {"by_status": by_status, "by_category_status": by_category}


# ---------------------------------------------------------------------------
# Per-row processing
# ---------------------------------------------------------------------------


def _import_kwargs(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(row["instrument_name"])[:500],
        "uri": row["canonical_url"],
        "publisher": row["issuing_authority"],
        "jurisdiction": "WA",
        "authority": row["issuing_authority"],
        "local_government": local_government_for_authority(row["issuing_authority"]),
        "source_type": source_type_for_category(row["category"]),
        "access_type": "public",
        "source_metadata": {
            "wp4": True,
            "manifest_id": str(row["id"]),
            "manifest_category": row["category"],
            "index_source_url": row.get("index_source_url"),
            "expected_version_hint": row.get("expected_version_hint"),
        },
    }


def _record_fetch_log(library, *, source_id: str, source_version_id: str | None,
                      fetch_kind: str, status: str, metadata: dict[str, Any],
                      error: str | None, escalations: list[str]) -> None:
    from uuid import UUID

    try:
        library.record_fetch_log(
            source_id=source_id,
            source_version_id=source_version_id,
            org_id=UUID(ORG_ID),
            requested_by_user_id=UUID(USER_ID),
            fetch_kind=fetch_kind,
            status=status,
            metadata=metadata,
            error=error,
            completed=True,
        )
    except Exception as exc:  # noqa: BLE001 — fetch-log failure must not stall the run
        escalations.append(
            f"source_fetch_log insert failed for source {source_id}: {exc} — "
            "unblock: verify org/user seed rows "
            f"({ORG_ID} / {USER_ID}) exist in the target database."
        )


def process_row(row: dict[str, Any], *, library, escalations: list[str]) -> dict[str, Any]:
    """Acquire one manifest row. Returns the outcome dict (never raises)."""
    from draftcheck.domain.sources.models import LicenceStatus, SourceReviewStatus

    manifest_id = str(row["id"])
    outcome: dict[str, Any] = {
        "manifest_id": manifest_id,
        "instrument_name": row["instrument_name"],
        "category": row["category"],
        "status": "blocked",
        "source_document_id": None,
        "source_version_id": None,
        "attempts": 0,
        "error": None,
        "note": None,
    }
    plan = classify_target(row["canonical_url"], row["notes"], row["category"])
    common = _import_kwargs(row)

    if plan == "no_url":
        note = format_blocked_note(
            error="no canonical_url on manifest row",
            unblock=unblock_hint("no_url", manifest_id),
            attempts=0,
        )
        outcome.update(status="blocked", error="no canonical_url", note=note)
        escalations.append(f"{row['instrument_name']}: blocked — no canonical_url")
        return outcome

    if plan == "metadata_only":
        reason = "paid/licence-blocked source (notes/URL indicate restricted licence)"
        result = library.import_source(
            content="",
            licence_status=LicenceStatus.METADATA_ONLY,
            review_status=SourceReviewStatus.PENDING_REVIEW,
            metadata_only=True,
            licence_notes=reason,
            version_label="wp4-metadata-only",
            version_metadata={"wp4": True, "manifest_id": manifest_id, "reason": reason},
            **common,
        )
        _record_fetch_log(
            library,
            source_id=result.source.id,
            source_version_id=result.version.id,
            fetch_kind="wp4_manifest_acquisition",
            status="metadata_only",
            metadata={"manifest_id": manifest_id, "canonical_url": row["canonical_url"]},
            error=None,
            escalations=escalations,
        )
        outcome.update(
            status="metadata_only",
            source_document_id=result.source.id,
            source_version_id=result.version.id,
            note=format_metadata_only_note(reason),
        )
        return outcome

    # plan == "fetch": lawful fetch through the existing pipeline.
    licence_notes = ""
    try:
        fetch, attempts = lawful_fetch_with_retries(row["canonical_url"], licence_notes)
        outcome["attempts"] = attempts
    except PermanentFetchError as exc:
        message = str(exc)
        outcome["attempts"] = 1
        if is_licence_error(message):
            # Licensing wall (e.g. Standards Australia) -> metadata_only.
            result = library.import_source(
                content="",
                licence_status=LicenceStatus.METADATA_ONLY,
                review_status=SourceReviewStatus.PENDING_REVIEW,
                metadata_only=True,
                licence_notes=message,
                version_label="wp4-metadata-only",
                version_metadata={"wp4": True, "manifest_id": manifest_id, "reason": message},
                **common,
            )
            _record_fetch_log(
                library,
                source_id=result.source.id,
                source_version_id=result.version.id,
                fetch_kind="wp4_manifest_acquisition",
                status="metadata_only",
                metadata={"manifest_id": manifest_id, "canonical_url": row["canonical_url"]},
                error=message,
                escalations=escalations,
            )
            outcome.update(
                status="metadata_only",
                source_document_id=result.source.id,
                source_version_id=result.version.id,
                note=format_metadata_only_note(message),
            )
            return outcome
        kind = "robots" if "robots.txt" in message else "restricted"
        note = format_blocked_note(
            error=message,
            unblock=unblock_hint(kind, manifest_id, row["canonical_url"]),
            attempts=1,
        )
        outcome.update(status="blocked", error=message, note=note)
        escalations.append(f"{row['instrument_name']}: blocked — {message}")
        return outcome
    except ParseFailure as exc:
        return _handle_parse_failure(
            row, str(exc), library=library, common=common, outcome=outcome,
            escalations=escalations,
        )
    except Exception as exc:  # noqa: BLE001 — transient exhaustion / unexpected fetch error
        message = str(exc)
        outcome["attempts"] = MAX_FETCH_ATTEMPTS
        note = format_blocked_note(
            error=message,
            unblock=unblock_hint("transient", manifest_id, row["canonical_url"]),
            attempts=MAX_FETCH_ATTEMPTS,
        )
        outcome.update(status="blocked", error=message, note=note)
        escalations.append(f"{row['instrument_name']}: blocked — {message}")
        return outcome

    result = library.import_source(
        content=fetch.text,
        licence_status=LicenceStatus.PENDING_REVIEW,
        review_status=SourceReviewStatus.PENDING_REVIEW,
        media_type="text/plain",
        metadata_only=False,
        licence_notes=(
            "Fetched by wp4_acquire from the official public index; "
            "source_reviews gate still required before citation."
        ),
        version_label=f"fetched:{fetch.sha256[:12]}",
        version_metadata=fetch.metadata,
        **common,
    )
    raw_artifact = library.record_raw_fetch_artifact(
        source_id=result.source.id,
        source_version_id=result.version.id,
        content=fetch.content,
        content_type=fetch.content_type,
        final_url=fetch.final_url,
        metadata=fetch.metadata,
    )
    _record_fetch_log(
        library,
        source_id=result.source.id,
        source_version_id=result.version.id,
        fetch_kind="wp4_manifest_acquisition",
        status="success",
        metadata={
            "manifest_id": manifest_id,
            "canonical_url": row["canonical_url"],
            "raw_artifact_id": raw_artifact["id"],
            "duplicate": result.duplicate,
            **dict(fetch.metadata),
        },
        error=None,
        escalations=escalations,
    )
    parse_quality = fetch.metadata.get("parse_quality")
    outcome.update(
        status="acquired",
        source_document_id=result.source.id,
        source_version_id=result.version.id,
        chunk_count=len(result.chunks),
        duplicate=result.duplicate,
        parse_quality=parse_quality,
        note=None,
    )
    if isinstance(parse_quality, dict) and parse_quality.get("status") == "low_signal_review":
        escalations.append(
            f"{row['instrument_name']}: acquired but parse quality is low_signal_review "
            f"(source_version {result.version.id}) — repair via existing parse-repair job."
        )
    return outcome


def _handle_parse_failure(
    row: dict[str, Any],
    message: str,
    *,
    library,
    common: dict[str, Any],
    outcome: dict[str, Any],
    escalations: list[str],
) -> dict[str, Any]:
    """Plan rule: parse fails -> OCR fallback; still failing -> blocked with artifact preserved."""
    from draftcheck.domain.sources.models import LicenceStatus, SourceReviewStatus

    manifest_id = str(row["id"])
    outcome["attempts"] = 1
    try:
        content, content_type, final_url, text, repair_meta = raw_fetch_and_repair(
            row["canonical_url"]
        )
    except Exception as exc:  # noqa: BLE001 — raw re-fetch failed; block mechanically
        error = f"{message}; raw re-fetch for artifact preservation failed: {exc}"
        note = format_blocked_note(
            error=error,
            unblock=unblock_hint("parse", manifest_id, row["canonical_url"]),
            attempts=1,
        )
        outcome.update(status="blocked", error=error, note=note)
        escalations.append(f"{row['instrument_name']}: blocked — {error}")
        return outcome

    repaired = bool(text.strip())
    result = library.import_source(
        content=text,
        licence_status=LicenceStatus.PENDING_REVIEW,
        review_status=SourceReviewStatus.PENDING_REVIEW,
        media_type="text/plain",
        metadata_only=not repaired,
        licence_notes="Fetched by wp4_acquire; parse repair " + ("succeeded" if repaired else "failed"),
        version_label=("repaired:" if repaired else "unparsed:") + sha256_short(content),
        version_metadata={"wp4": True, "manifest_id": manifest_id, **repair_meta},
        **common,
    )
    raw_artifact = library.record_raw_fetch_artifact(
        source_id=result.source.id,
        source_version_id=result.version.id,
        content=content,
        content_type=content_type,
        final_url=final_url,
        metadata=repair_meta,
    )
    _record_fetch_log(
        library,
        source_id=result.source.id,
        source_version_id=result.version.id,
        fetch_kind="wp4_manifest_acquisition",
        status="success" if repaired else "parse_failed",
        metadata={
            "manifest_id": manifest_id,
            "canonical_url": row["canonical_url"],
            "raw_artifact_id": raw_artifact["id"],
            **repair_meta,
        },
        error=None if repaired else message,
        escalations=escalations,
    )
    if repaired:
        outcome.update(
            status="acquired",
            source_document_id=result.source.id,
            source_version_id=result.version.id,
            chunk_count=len(result.chunks),
            parse_quality=repair_meta.get("parse_quality"),
            note=None,
        )
        return outcome
    error = f"{message}; pymupdf/OCR repair also failed (raw artifact {raw_artifact['id']} preserved)"
    note = format_blocked_note(
        error=error,
        unblock=unblock_hint("parse", manifest_id, row["canonical_url"]),
        attempts=1,
    )
    outcome.update(
        status="blocked",
        source_document_id=result.source.id,
        source_version_id=result.version.id,
        error=error,
        note=note,
    )
    escalations.append(f"{row['instrument_name']}: blocked — {error}")
    return outcome


def sha256_short(content: bytes) -> str:
    from hashlib import sha256

    return sha256(content).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", default="", help="path for the JSON acquisition report")
    ap.add_argument("--limit", type=int, default=0, help="max rows to process (0 = all claimable)")
    ap.add_argument("--category", default="", help="only process this manifest category")
    ap.add_argument("--ids", default="", help="comma-separated manifest UUIDs to (re)process")
    ap.add_argument(
        "--retry-blocked", action="store_true",
        help="also claim rows already in status='blocked'",
    )
    ap.add_argument("--worker-id", default="", help="lease owner id (default: host+pid)")
    ap.add_argument("--lease-minutes", type=int, default=30)
    ap.add_argument("--claim-batch", type=int, default=5, help="rows claimed per lease round")
    ap.add_argument("--delay", type=float, default=1.0, help="politeness delay between fetches (s)")
    args = ap.parse_args()

    worker_id = args.worker_id or f"wp4-{socket.gethostname()}-{os.getpid()}"
    ids = [part.strip() for part in args.ids.split(",") if part.strip()] or None
    category = args.category or None
    started_at = datetime.now(UTC).isoformat()
    escalations: list[str] = []
    outcomes: list[dict[str, Any]] = []

    if not os.environ.get("OPENAI_API_KEY"):
        escalations.append(
            "OPENAI_API_KEY not set: chunk embeddings fall back to the hash stub "
            "(or fail in APP_ENV=production). Unblock: set OPENAI_API_KEY in the api env."
        )

    dsn = psycopg_dsn(os.environ["DATABASE_URL"])
    library = build_library()

    claim_batch_size = len(ids) if ids else args.claim_batch
    with psycopg.connect(dsn) as conn:
        while True:
            remaining = args.limit - len(outcomes) if args.limit else claim_batch_size
            if remaining <= 0:
                break
            batch = claim_batch(
                conn,
                worker_id=worker_id,
                lease_minutes=args.lease_minutes,
                batch_size=min(claim_batch_size, remaining),
                category=category,
                ids=ids,
                retry_blocked=args.retry_blocked,
            )
            if not batch:
                break
            for row in batch:
                time.sleep(args.delay)
                try:
                    outcome = process_row(row, library=library, escalations=escalations)
                except Exception as exc:  # noqa: BLE001 — never stall the run on one row
                    error = f"unexpected error: {exc}"
                    print(traceback.format_exc(), file=sys.stderr, flush=True)
                    outcome = {
                        "manifest_id": str(row["id"]),
                        "instrument_name": row["instrument_name"],
                        "category": row["category"],
                        "status": "blocked",
                        "source_document_id": None,
                        "source_version_id": None,
                        "attempts": 1,
                        "error": error,
                        "note": format_blocked_note(
                            error=error,
                            unblock=unblock_hint("transient", str(row["id"])),
                            attempts=1,
                        ),
                    }
                    escalations.append(f"{row['instrument_name']}: blocked — {error}")
                finalize_row(
                    conn,
                    str(row["id"]),
                    status=outcome["status"],
                    note=outcome.get("note"),
                    source_document_id=outcome.get("source_document_id"),
                )
                outcomes.append(outcome)
                print(
                    f"[{len(outcomes)}] {outcome['status']:<13} {row['category']:<24} "
                    f"{row['instrument_name'][:70]}",
                    flush=True,
                )
            if ids:
                break  # explicit id list is a single round

        totals = manifest_totals(conn)

    report = build_report(
        worker_id=worker_id,
        args_summary={
            "limit": args.limit,
            "category": category,
            "ids": ids,
            "retry_blocked": args.retry_blocked,
            "claim_batch": args.claim_batch,
            "delay": args.delay,
        },
        outcomes=outcomes,
        manifest_totals=totals,
        escalations=escalations,
        started_at=started_at,
        finished_at=datetime.now(UTC).isoformat(),
    )
    payload = json.dumps(report, indent=2, default=str)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(payload)
    print(payload)
    return 0  # blocked rows are a valid terminal state; nonzero only on crash


if __name__ == "__main__":
    raise SystemExit(main())

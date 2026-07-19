"""WP4 blocked manifest alias/supersession reconciliation.

Closes blocked rows that are not acquisition failures:

* title variants that point to an already-acquired source document become
  ``acquired`` aliases with ``source_document_id`` and canonical URL filled.
* amendment, commencement, reprint, fragment, and repealed/superseded rows
  become ``out_of_scope`` with a terminal note.

Run inside the api container:
    python /app/scripts/wp4_reconcile_aliases.py --apply \
        --report /app/reports/wp4_reconcile_aliases.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "wp4_reconcile_aliases.json"

FRAGMENT_TERMS = (
    "amendment",
    "assent commencement",
    "citation published commencement",
    "commencement",
    "reprint of",
    "operation of",
    "forms ",
)

FRAGMENT_PREFIXES = (
    "iii of ",
    "when ",
    "wiluna ",
    "yelbeni ",
    "western australian planning commission ",
    "swan valley planning scheme ",
)

TITLE_VARIANT_PREFIXES = (
    "the ",
    "western australia ",
    "authority ",
)

LOCAL_SCHEME_ALIASES = {
    "local planning scheme no 6",
    "local planning scheme no.6",
    "local planning scheme no. 6",
}

LOCAL_SCHEME_TARGET = "City of Melville Local Planning Scheme No. 6 - Scheme Text"

EXPLICIT_ALIAS_TARGETS = {
    "building building regulations 2012": "Building Regulations 2012",
    "metropolitan redevelopment authority metropolitan redevelopment authority act 2011": (
        "Metropolitan Redevelopment Authority Act 2011"
    ),
}

SUPERSEDED_TARGETS = {
    "armadale redevelopment act 2001": "Metropolitan Redevelopment Authority Act 2011",
    "east perth redevelopment act 1991": "Metropolitan Redevelopment Authority Act 2011",
    "midland redevelopment act 1999": "Metropolitan Redevelopment Authority Act 2011",
    "subiaco redevelopment act 1994": "Metropolitan Redevelopment Authority Act 2011",
    "building regulations 1989": "Building Regulations 2012",
    "planning scheme act 1959": "Planning and Development Act 2005",
    "swan valley planning act 1995": "Swan Valley Planning Act 2020",
    "swan valley planning regulations 1995": "Swan Valley Planning Act 2020",
    "the heritage of western australia act 1990": "Heritage Act 2018",
}

COVERAGE_SUBSTRING_TARGETS = (
    ("aboriginal affairs planning authority act amendment", "Aboriginal Affairs Planning Authority Act 1972"),
    ("aboriginal affairs planning authority amendment", "Aboriginal Affairs Planning Authority Act 1972"),
    ("aboriginal heritage amendment", "Aboriginal Heritage Act 1972"),
    ("building amendment act", "Building Act 2011"),
    ("building amendment regulations", "Building Regulations 2012"),
    ("building regulations amendment regulations", "Building Regulations 2012"),
    ("home building contracts amendment act", "Home Building Contracts Act 1991"),
    ("heritage amendment regulations", "Heritage Regulations 2019"),
    ("planning and development amendment act", "Planning and Development Act 2005"),
    ("planning legislation amendment act", "Planning and Development Act 2005"),
    ("town planning and development amendment act", "Planning and Development Act 2005"),
)


@dataclass(frozen=True)
class ManifestRow:
    id: str
    instrument_name: str
    category: str
    status: str


@dataclass(frozen=True)
class SourceDoc:
    id: str
    title: str
    canonical_url: str | None
    chunk_count: int = 3


@dataclass(frozen=True)
class ReconcileDecision:
    manifest_id: str
    instrument_name: str
    current_status: str
    recommended_status: str
    reason: str
    source_document_id: str | None = None
    source_title: str | None = None
    canonical_url: str | None = None


def norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def strip_variant_prefix(value: str) -> str:
    current = value
    changed = True
    while changed:
        changed = False
        for prefix in TITLE_VARIANT_PREFIXES:
            if current.startswith(prefix):
                current = current[len(prefix) :].strip()
                changed = True
    return current


def find_source(title: str, sources_by_norm_title: dict[str, SourceDoc]) -> SourceDoc | None:
    return sources_by_norm_title.get(norm(title))


def alias_target(row_name: str, sources_by_norm_title: dict[str, SourceDoc]) -> SourceDoc | None:
    normalized = norm(row_name)
    explicit = EXPLICIT_ALIAS_TARGETS.get(normalized)
    if explicit:
        return find_source(explicit, sources_by_norm_title)

    if normalized in LOCAL_SCHEME_ALIASES:
        return find_source(LOCAL_SCHEME_TARGET, sources_by_norm_title)

    direct = find_source(row_name, sources_by_norm_title)
    if direct is not None:
        return direct

    stripped = strip_variant_prefix(normalized)
    return sources_by_norm_title.get(stripped)


def covered_source(row_name: str, sources_by_norm_title: dict[str, SourceDoc]) -> SourceDoc | None:
    normalized = norm(row_name)
    explicit = SUPERSEDED_TARGETS.get(strip_variant_prefix(normalized)) or SUPERSEDED_TARGETS.get(normalized)
    if explicit:
        source = find_source(explicit, sources_by_norm_title)
        if source is not None:
            return source

    for substring, target in COVERAGE_SUBSTRING_TARGETS:
        if substring in normalized:
            source = find_source(target, sources_by_norm_title)
            if source is not None:
                return source

    for source_title, source in sources_by_norm_title.items():
        if normalized.endswith(source_title):
            return source
    return None


def is_fragment_or_superseded(row_name: str) -> bool:
    normalized = norm(row_name)
    stripped = strip_variant_prefix(normalized)
    return (
        any(term in normalized for term in FRAGMENT_TERMS)
        or any(normalized.startswith(prefix) for prefix in FRAGMENT_PREFIXES)
        or stripped in SUPERSEDED_TARGETS
        or normalized in SUPERSEDED_TARGETS
    )


def classify_row(row: ManifestRow, sources_by_norm_title: dict[str, SourceDoc]) -> ReconcileDecision:
    if row.status != "blocked":
        return ReconcileDecision(
            manifest_id=row.id,
            instrument_name=row.instrument_name,
            current_status=row.status,
            recommended_status=row.status,
            reason="Row is not blocked; no reconciliation needed.",
        )

    if is_fragment_or_superseded(row.instrument_name):
        source = covered_source(row.instrument_name, sources_by_norm_title)
        source_bits = {
            "source_document_id": source.id if source else None,
            "source_title": source.title if source else None,
            "canonical_url": source.canonical_url if source else None,
        }
        return ReconcileDecision(
            manifest_id=row.id,
            instrument_name=row.instrument_name,
            current_status=row.status,
            recommended_status="out_of_scope",
            reason="Superseded, amendment-only, commencement, reprint, or extracted citation fragment.",
            **source_bits,
        )

    source = alias_target(row.instrument_name, sources_by_norm_title)
    if source is not None:
        return ReconcileDecision(
            manifest_id=row.id,
            instrument_name=row.instrument_name,
            current_status=row.status,
            recommended_status="acquired",
            reason="Title variant resolved to an already acquired source document.",
            source_document_id=source.id,
            source_title=source.title,
            canonical_url=source.canonical_url,
        )

    return ReconcileDecision(
        manifest_id=row.id,
        instrument_name=row.instrument_name,
        current_status=row.status,
        recommended_status="blocked",
        reason="No safe alias or supersession reconciliation found.",
    )


def database_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def load_blocked_rows(database_url_value: str) -> list[ManifestRow]:
    engine = create_engine(database_url_value)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id::text, instrument_name, category, status
                FROM target_manifest
                WHERE status = 'blocked'
                ORDER BY category, instrument_name
                """
            )
        ).mappings()
        return [
            ManifestRow(
                id=str(row["id"]),
                instrument_name=str(row["instrument_name"]),
                category=str(row["category"]),
                status=str(row["status"]),
            )
            for row in rows
        ]


def load_sources(database_url_value: str) -> dict[str, SourceDoc]:
    engine = create_engine(database_url_value)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT s.id::text, s.title, s.canonical_url, count(sc.id) AS chunk_count
                FROM source_documents s
                JOIN target_manifest tm ON tm.source_document_id = s.id
                JOIN source_versions sv ON sv.source_id = s.id
                JOIN source_chunks sc ON sc.source_version_id = sv.id
                WHERE tm.status = 'acquired'
                GROUP BY s.id, s.title, s.canonical_url
                HAVING count(sc.id) >= 3
                """
            )
        ).mappings()
        return {
            norm(str(row["title"])): SourceDoc(
                id=str(row["id"]),
                title=str(row["title"]),
                canonical_url=row["canonical_url"],
                chunk_count=int(row["chunk_count"]),
            )
            for row in rows
        }


def apply_decisions(database_url_value: str, decisions: list[ReconcileDecision]) -> int:
    engine = create_engine(database_url_value)
    changed = 0
    with engine.begin() as conn:
        for decision in decisions:
            if decision.recommended_status == "blocked":
                continue
            result = conn.execute(
                text(
                    """
                    UPDATE target_manifest
                    SET status = :status,
                        source_document_id = COALESCE(CAST(:doc_id AS uuid), source_document_id),
                        canonical_url = COALESCE(CAST(:canonical_url AS text), canonical_url),
                        notes = :notes,
                        metadata_json = COALESCE(metadata_json, '{}'::jsonb)
                            || CAST(:metadata AS jsonb),
                        last_checked_at = now(),
                        updated_at = now(),
                        claimed_by = NULL,
                        lease_expires_at = NULL
                    WHERE id = CAST(:id AS uuid)
                      AND status = 'blocked'
                    """
                ),
                {
                    "id": decision.manifest_id,
                    "status": decision.recommended_status,
                    "doc_id": decision.source_document_id,
                    "canonical_url": decision.canonical_url,
                    "notes": (
                        f"WP4 reconcile: {decision.reason}"
                        + (f" Covered by: {decision.source_title}" if decision.source_title else "")
                    ),
                    "metadata": json.dumps(
                        {
                            "wp4_reconcile": True,
                            "reason": decision.reason,
                            "source_document_id": decision.source_document_id,
                            "source_title": decision.source_title,
                        }
                    ),
                },
            )
            changed += result.rowcount or 0
    return changed


def report_for(decisions: list[ReconcileDecision], *, mode: str, rows_scanned: int, changed: int) -> dict[str, Any]:
    by_recommendation: dict[str, int] = {}
    for decision in decisions:
        by_recommendation[decision.recommended_status] = by_recommendation.get(decision.recommended_status, 0) + 1
    return {
        "wp": "WP4",
        "mode": mode,
        "rows_scanned": rows_scanned,
        "changed": changed,
        "by_recommendation": by_recommendation,
        "decisions": [decision.__dict__ for decision in decisions],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    db_url = database_url()
    rows = load_blocked_rows(db_url)
    sources_by_norm_title = load_sources(db_url)
    decisions = [classify_row(row, sources_by_norm_title) for row in rows]
    changed = apply_decisions(db_url, decisions) if args.apply else 0
    report = report_for(decisions, mode="apply" if args.apply else "dry_run", rows_scanned=len(rows), changed=changed)

    out = json.dumps(report, indent=2, default=str)
    print(out)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

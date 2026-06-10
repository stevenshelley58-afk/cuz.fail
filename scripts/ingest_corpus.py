"""Ingest the WA Planning Corpus into the durable V3 source library.

For every row in data/manifest.csv this imports a source + version via
SqlAlchemySourceLibrary.import_source (which chunks the text and writes
citations + embeddings), carrying rich metadata from:
  corpus/extracted/{id}/full_text.txt   extracted instrument text
  corpus/analysis/{id}/analysis.json    agent-verified analysis (version,
                                        numeric standards, cross references)
  corpus/docs/{id}/meta.json            fetch provenance (hash, final_url)
  reports/verification_results.json     fleet verdicts (correct_document)

Then an automated validator gate (--approve) approves versions that pass:
  - fleet verdict correct_document == True
  - extracted text >= 400 chars and >= 1 chunk
  - no fatal quality flags
Approved versions become citable (review_status=approved,
licence_status=verified_open) per the cite-or-refuse retrieval gate.

Usage:
  set DATABASE_URL=...   (postgresql+psycopg://... on the VPS)
  .venv/Scripts/python scripts/ingest_corpus.py [--approve] [--local-validate]

  --local-validate  use sqlite:///./draftcheck-corpus.db and create the dev
                    schema (test-suite-style SQLite patches; prod uses alembic)
Embeddings: with OPENAI_API_KEY set, real text-embedding-3-small vectors are
written at import time; without it (development) a hash stub is used and
`draftcheck re-embed` should be run on the VPS afterwards.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_ORG_ID = "00000000-0000-5000-8000-000000000001"  # well-known system org for corpus workbench
SYSTEM_ACTOR_ID = "00000000-0000-5000-8000-000000000002"  # well-known system actor for automated validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

MANIFEST = REPO_ROOT / "data" / "manifest.csv"
EXTRACTED = REPO_ROOT / "corpus" / "extracted"
ANALYSIS = REPO_ROOT / "corpus" / "analysis"
DOCS = REPO_ROOT / "corpus" / "docs"
VERIFICATION = REPO_ROOT / "reports" / "verification_results.json"
REPORT = REPO_ROOT / "reports" / "ingestion_report.json"

SOURCE_TYPE_BY_CATEGORY = {
    "planning_code": "r_code",
    "SPP": "state_planning_policy",
    "DC": "development_control_policy",
    "position_statement": "position_statement",
    "planning_bulletin": "planning_bulletin",
    "legislation": "legislation",
    "region_scheme": "region_scheme",
    "scheme": "local_planning_scheme",
    "strategy": "local_planning_strategy",
    "scheme_map": "map_layer",
    "LPP": "local_planning_policy",
    "structure_plan": "structure_plan",
    "building_code": "building_code",
}

DATE_FORMATS = ("%d %B %Y", "%B %Y", "%Y-%m-%d", "%d/%m/%Y", "%Y")


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    m = re.search(r"(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{4})", value)
    if m and m.group(1) != value:
        return parse_date(m.group(1))
    return None


def local_government_for(authority: str) -> str | None:
    m = re.match(r"(?:City|Town|Shire) of (.+)", authority.strip())
    return m.group(1) if m else None


def load_json(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def apply_sqlite_dev_patches() -> None:
    """Same patches the test suite uses so the V3 schema works on SQLite."""
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
        def _visit_jsonb(self, type_, **kw):  # type: ignore[no-untyped-def]
            return "JSON"

        SQLiteTypeCompiler.visit_JSONB = _visit_jsonb  # type: ignore[attr-defined]

    import draftcheck.db.models as models_mod

    # SQLite errors on duplicate index names (column index=True + explicit
    # Index with the same name). Keep the first of each name per table.
    for tbl in models_mod.Base.metadata.tables.values():
        seen: set[str] = set()
        for idx in sorted(list(tbl.indexes), key=lambda i: i.name or ""):
            if idx.name in seen:
                tbl.indexes.discard(idx)
            elif idx.name:
                seen.add(idx.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true",
                        help="run the automated validator gate and approve passing versions")
    parser.add_argument("--local-validate", action="store_true",
                        help="use a local SQLite DB with dev schema (validation only)")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.local_validate:
        os.environ["DATABASE_URL"] = "sqlite:///./draftcheck-corpus.db"
        os.environ.setdefault("APP_ENV", "development")
        apply_sqlite_dev_patches()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("error: DATABASE_URL is required", file=sys.stderr)
        raise SystemExit(2)

    from draftcheck.domain.sources.models import LicenceStatus, SourceReviewStatus
    from draftcheck.domain.sources.sqlalchemy_store import SqlAlchemySourceLibrary

    if args.local_validate:
        from sqlalchemy import create_engine

        import draftcheck.db.models as models_mod

        engine = create_engine(database_url)
        # dev validation only; prod uses alembic. Skip PostGIS tables on SQLite.
        non_spatial = [
            t for t in models_mod.Base.metadata.sorted_tables
            if not any("geometry" in str(c.type).lower() for c in t.columns)
        ]
        models_mod.Base.metadata.create_all(engine, tables=non_spatial)
        engine.dispose()

    library = SqlAlchemySourceLibrary.from_database_url(database_url)

    verdicts: dict[str, dict] = {}
    vdata = load_json(VERIFICATION)
    if vdata:
        verdicts = {v["id"]: v for v in vdata.get("results", [])}

    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    report: list[dict] = []
    counts = {"imported": 0, "duplicates": 0, "metadata_only": 0, "approved": 0,
              "held_pending": 0, "errors": 0}

    for row in rows:
        rid = row["id"]
        if row["status"] == "out_of_scope":
            continue
        try:
            text = ""
            full_text_path = EXTRACTED / rid / "full_text.txt"
            if row["status"] == "extracted" and full_text_path.exists():
                text = full_text_path.read_text(encoding="utf-8", errors="replace")

            analysis = load_json(ANALYSIS / rid / "analysis.json") or {}
            fetch_meta = load_json(DOCS / rid / "meta.json") or {}
            verdict = verdicts.get(rid, {})

            version_date = analysis.get("version_date") or row.get("expected_version_hint") or ""
            version_metadata = {
                "workbench_id": rid,
                "category": row["category"],
                "instrument_no": analysis.get("instrument_no"),
                "version_date": version_date or None,
                "operative_status": analysis.get("operative_status"),
                "scope_summary": analysis.get("scope_summary"),
                "residential_relevance": analysis.get("residential_relevance"),
                "key_numeric_standards": analysis.get("key_numeric_standards", []),
                "cross_references": analysis.get("cross_references", []),
                "quality_flags": analysis.get("quality_flags", []),
                "fetch": {
                    "final_url": fetch_meta.get("final_url"),
                    "fetched_at": fetch_meta.get("fetched_at"),
                    "content_hash": fetch_meta.get("content_hash"),
                    "http_status": fetch_meta.get("http_status"),
                },
                "verified_correct_document": verdict.get("correct_document"),
            }
            metadata_only = not text.strip() or row["status"] in ("metadata_only", "blocked", "pending")

            result = library.import_source(
                title=row["instrument_name"],
                content=text,
                uri=row.get("canonical_url") or None,
                authority=row["issuing_authority"],
                local_government=local_government_for(row["issuing_authority"]),
                jurisdiction="WA",
                source_type=SOURCE_TYPE_BY_CATEGORY.get(row["category"], "planning_instrument"),
                access_type="public",
                licence_status=LicenceStatus.OPEN if not metadata_only else LicenceStatus.METADATA_ONLY,
                review_status=SourceReviewStatus.PENDING_REVIEW,
                licence_notes=(
                    "Publicly published WA government planning instrument (Crown copyright); "
                    "stored for advisory, cite-or-refuse retrieval with attribution."
                ),
                media_type="text/plain",
                metadata_only=metadata_only,
                version_label=(analysis.get("version_date") or row.get("expected_version_hint")
                               or f"fetched-{(fetch_meta.get('fetched_at') or '')[:10] or 'unknown'}"),
                source_metadata={"workbench_id": rid, "index_source_url": row.get("index_source_url")},
                version_metadata=version_metadata,
                effective_from=parse_date(version_date),
                published_at=parse_date(version_date),
            )
            counts["duplicates" if result.duplicate else "imported"] += 1
            if metadata_only:
                counts["metadata_only"] += 1

            entry = {
                "id": rid,
                "source_id": str(result.source.id),
                "source_version_id": str(result.version.id),
                "duplicate": result.duplicate,
                "metadata_only": metadata_only,
                "chars": len(text),
            }

            if args.approve and not metadata_only:
                flags = [f.lower() for f in analysis.get("quality_flags", [])]
                # Fatal quality flags are structured prefixes, not free-text
                # substrings. Substring-matching "wrong"/"empty"/"corrupt" against
                # analyst-written narrative flags false-positives on common phrases
                # like "summary.json title is wrong" or "key_provisions is empty"
                # (both about the extractor summary, not the document itself).
                # Only treat a flag as fatal if it begins with a structured
                # category token (e.g. "wrong_document", "empty full_text",
                # "corrupt_*") so the verifier verdict stays authoritative.
                fatal = [
                    f for f in flags
                    if re.match(r"\s*(wrong_document\b|empty full_text\b|corrupt\b)", f)
                ]
                checks = {
                    "verified_correct_document": verdict.get("correct_document") is True,
                    "text_volume": len(text.strip()) >= 400,
                    "no_fatal_quality_flags": not fatal,
                }
                if all(checks.values()):
                    library.review_source(
                        source_id=str(result.source.id),
                        source_version_id=str(result.version.id),
                        review_status=SourceReviewStatus.APPROVED,
                        licence_status=LicenceStatus.VERIFIED_OPEN,
                        org_id=SYSTEM_ORG_ID,
                        actor_id=SYSTEM_ACTOR_ID,
                        notes=f"automated validator gate v1 passed: {json.dumps(checks)}",
                    )
                    counts["approved"] += 1
                    entry["approved"] = True
                else:
                    counts["held_pending"] += 1
                    entry["approved"] = False
                    entry["held_reason"] = {k: v for k, v in checks.items() if not v}
            report.append(entry)
            print(f"{rid}: {'dup' if result.duplicate else 'ok'}"
                  f"{' meta-only' if metadata_only else ''}"
                  f"{' APPROVED' if entry.get('approved') else ''}", flush=True)
        except Exception as exc:  # noqa: BLE001 — record and continue
            counts["errors"] += 1
            report.append({"id": rid, "error": f"{type(exc).__name__}: {exc}"})
            print(f"{rid}: ERROR {exc}", flush=True)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"counts": counts, "items": report}, indent=2), encoding="utf-8")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()

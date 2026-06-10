"""WP5 — citation closure loop (docs/CORPUS_COMPLETENESS_PLAN.md Phase 3).

Runs INSIDE the api container (psycopg3 + DATABASE_URL present; no LLM keys
needed — the extractor is fully deterministic):

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp5_citation_closure.py \
        [--dry-run] [--max-rounds 10] [--source-version <uuid>] [--limit N] \
        --report /app/reports/citation_closure.json

Per round:
  1. For every parsed document (every source_version with source_chunks), run
     the deterministic extractor (draftcheck.extraction.citations) over its
     clauses rows — falling back to raw source_chunks when no structure pass has
     produced clauses yet — and upsert edges into legal_edges with
     relation='cites'. Resolved targets: to_type='target_manifest',
     to_ref=<manifest uuid>. Unresolved: to_type='external_reference',
     to_ref=<normalized instrument key>.
  2. Resolution matches each reference against target_manifest.instrument_name
     plus instrument_aliases (exact aliases via normalized lookup, regex aliases
     against the raw text), trying deterministic key variants ("spp 2" <->
     "spp 2.0", "TPS3" <-> "Town Planning Scheme No. 3", ...). Self-citations
     (a document mentioning itself) are skipped.
  3. Every key still unresolved after matching gets a new target_manifest row —
     status='pending' by default, or status='out_of_scope' when it matches the
     closed out-of-scope list from docs/CORPUS_SCOPE.md — plus instrument_aliases
     rows so the next round resolves it. When a reference resolves, its stale
     external_reference edge is deleted.
  4. Loop until a full pass finds zero unresolved references and adds zero new
     manifest rows (fixpoint), capped by --max-rounds.

Edges use from_ref=<clause/source_chunk UUID> (clause_key is only unique per
source_version, so it cannot serve as a global ref); the clause_key/path and
source_version_id are recorded in metadata_json.

Exit code 0 only when the fixpoint was reached. --dry-run runs the same loop in
one never-committed transaction and rolls back at the end.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402
from psycopg.types.json import Json  # noqa: E402

from draftcheck.extraction.citations import (  # noqa: E402
    Reference,
    build_alias_map,
    classify_out_of_scope,
    default_category,
    extract_references,
    out_of_scope_note,
    resolve_key,
)
from draftcheck.extraction.normalize import whitespace_normalize  # noqa: E402

RELATION = "cites"
QUOTE_WINDOW = 80


# ---------------------------------------------------------------------------
# DB loading
# ---------------------------------------------------------------------------


def load_documents(
    conn: psycopg.Connection, source_version: str, limit: int
) -> list[tuple[str, str, str]]:
    """Every parsed document: (source_version_id, source_document_id, title)."""
    sql = (
        "SELECT sv.id, sv.source_id, sd.title "
        "FROM source_versions sv JOIN source_documents sd ON sd.id = sv.source_id "
        "WHERE EXISTS (SELECT 1 FROM source_chunks sc WHERE sc.source_version_id = sv.id) "
    )
    params: list[Any] = []
    if source_version:
        sql += "AND sv.id = %s "
        params.append(source_version)
    sql += "ORDER BY sd.title, sv.id"
    rows = [(str(r[0]), str(r[1]), r[2]) for r in conn.execute(sql, params).fetchall()]
    return rows[:limit] if limit else rows


def load_units(conn: psycopg.Connection, sv_id: str) -> tuple[str, list[tuple[str, str, str]]]:
    """Text units for one source_version: clauses if present, else source_chunks."""
    rows = conn.execute(
        "SELECT id, COALESCE(clause_path, clause_key), text FROM clauses "
        "WHERE source_version_id = %s ORDER BY clause_key",
        (sv_id,),
    ).fetchall()
    if rows:
        return "clause", [(str(r[0]), r[1] or "", r[2] or "") for r in rows]
    rows = conn.execute(
        "SELECT id, chunk_index, text FROM source_chunks "
        "WHERE source_version_id = %s ORDER BY chunk_index",
        (sv_id,),
    ).fetchall()
    return "source_chunk", [(str(r[0]), f"chunk-{r[1]}", r[2] or "") for r in rows]


def load_resolver(
    conn: psycopg.Connection, escalations: list[str]
) -> tuple[dict[str, str], list[tuple[re.Pattern[str], str]], dict[str, str | None]]:
    """Alias map + regex aliases + manifest_id -> source_document_id (for self-skip).

    Canonical instrument names are fed to build_alias_map before aliases so the
    canonical name wins when both normalize to the same key.
    """
    pairs: list[tuple[str, str]] = []
    manifest_doc: dict[str, str | None] = {}
    for mid, name, sdid in conn.execute(
        "SELECT id, instrument_name, source_document_id FROM target_manifest"
    ):
        manifest_doc[str(mid)] = str(sdid) if sdid else None
        pairs.append((name, str(mid)))
    regex_aliases: list[tuple[re.Pattern[str], str]] = []
    for alias, mid, kind in conn.execute(
        "SELECT alias_text, canonical_manifest_id, match_kind FROM instrument_aliases"
    ):
        if kind == "regex":
            try:
                regex_aliases.append((re.compile(alias, re.IGNORECASE), str(mid)))
            except re.error as exc:
                escalations.append(f"instrument_aliases regex alias {alias!r} invalid: {exc}")
        else:
            pairs.append((alias, str(mid)))
    return build_alias_map(pairs), regex_aliases, manifest_doc


def resolve_reference(
    ref: Reference,
    alias_map: dict[str, str],
    regex_aliases: list[tuple[re.Pattern[str], str]],
) -> str | None:
    assert ref.instrument_key is not None
    mid = resolve_key(ref.instrument_key, alias_map)
    if mid:
        return mid
    for rx, target in regex_aliases:
        if rx.search(ref.instrument_text) or rx.search(ref.raw):
            return target
    return None


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def insert_edge(
    conn: psycopg.Connection,
    from_type: str,
    from_ref: str,
    to_type: str,
    to_ref: str,
    quote: str,
    confidence: float,
    review_status: str,
    meta: dict[str, Any],
) -> bool:
    cur = conn.execute(
        """
        INSERT INTO legal_edges (id, from_type, from_ref, to_type, to_ref, relation,
            evidence_quote, confidence, review_status, metadata_json, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        ON CONFLICT (from_type, from_ref, to_type, to_ref, relation) DO NOTHING
        """,
        (from_type, from_ref, to_type, to_ref[:200], RELATION, quote, confidence,
         review_status, Json(meta)),
    )
    return cur.rowcount == 1


def delete_stale_external(
    conn: psycopg.Connection, from_type: str, from_ref: str, key: str
) -> int:
    cur = conn.execute(
        "DELETE FROM legal_edges WHERE from_type = %s AND from_ref = %s "
        "AND relation = %s AND to_type = 'external_reference' AND to_ref = %s",
        (from_type, from_ref, RELATION, key[:200]),
    )
    return cur.rowcount


def context_quote(text: str, ref: Reference) -> str:
    s = max(0, ref.start - QUOTE_WINDOW)
    e = min(len(text), ref.end + QUOTE_WINDOW)
    return whitespace_normalize(text[s:e])[:500]


def display_name(instrument_text: str) -> str:
    t = whitespace_normalize(instrument_text)
    t = re.sub(r"^(?:the|this|that|these)\s+", "", t, flags=re.IGNORECASE)
    return t.strip(" ,;:.-")[:500] or "unknown instrument"


def add_manifest_row(
    conn: psycopg.Connection, key: str, info: dict[str, Any], round_no: int
) -> tuple[bool, int]:
    """Insert a target_manifest row + aliases for one unresolved key.

    Returns (row_was_new, aliases_added).
    """
    oos = classify_out_of_scope(key, info["display"])
    status = "out_of_scope" if oos else "pending"
    docs = sorted(info["documents"])
    notes = (
        f"WP5 citation closure round {round_no}: cited as {info['example']!r} "
        f"({info['count']}x) in {', '.join(docs[:3])}"
        + ("..." if len(docs) > 3 else "")
    )
    if oos:
        notes += f" | out_of_scope ({oos}): {out_of_scope_note(oos)}"
    meta = {
        "wp5": True,
        "round": round_no,
        "normalized_key": key,
        "citation_count": info["count"],
        "patterns": sorted(info["patterns"]),
        "cited_in": docs[:10],
        "out_of_scope_category": oos,
    }
    row = conn.execute(
        """
        INSERT INTO target_manifest (instrument_name, category, issuing_authority,
            status, notes, metadata_json, last_checked_at)
        VALUES (%s, %s, '', %s, %s, %s, now())
        ON CONFLICT (instrument_name, issuing_authority) DO NOTHING
        RETURNING id
        """,
        (info["display"], info["category"], status, notes, Json(meta)),
    ).fetchone()
    if row is not None:
        manifest_id, is_new = str(row[0]), True
    else:
        existing = conn.execute(
            "SELECT id FROM target_manifest "
            "WHERE instrument_name = %s AND issuing_authority = ''",
            (info["display"],),
        ).fetchone()
        if existing is None:  # pragma: no cover — conflict implies the row exists
            return False, 0
        manifest_id, is_new = str(existing[0]), False
    aliases_added = 0
    for alias_text in {key, info["display"]}:
        cur = conn.execute(
            "INSERT INTO instrument_aliases (alias_text, canonical_manifest_id, match_kind) "
            "VALUES (%s, %s, 'exact') ON CONFLICT (alias_text, match_kind) DO NOTHING",
            (alias_text, manifest_id),
        )
        aliases_added += cur.rowcount
    return is_new, aliases_added


# ---------------------------------------------------------------------------
# One closure round
# ---------------------------------------------------------------------------


def run_round(
    conn: psycopg.Connection, args: argparse.Namespace, round_no: int, escalations: list[str]
) -> dict[str, Any]:
    alias_map, regex_aliases, manifest_doc = load_resolver(conn, escalations)
    docs = load_documents(conn, args.source_version, args.limit)
    stats: dict[str, Any] = {
        "round": round_no,
        "documents_processed": len(docs),
        "units_scanned": 0,
        "references_found": 0,
        "internal_references_skipped": 0,
        "self_citations_skipped": 0,
        "resolved": 0,
        "edges_inserted_resolved": 0,
        "edges_inserted_external": 0,
        "stale_external_edges_deleted": 0,
        "unresolved_keys": 0,
        "manifest_rows_added": 0,
        "manifest_rows_out_of_scope": 0,
        "aliases_added": 0,
        "new_manifest_rows": [],
    }
    unresolved: dict[str, dict[str, Any]] = {}

    for sv_id, source_doc_id, title in docs:
        from_type, units = load_units(conn, sv_id)
        stats["units_scanned"] += len(units)
        for unit_id, unit_label, unit_text in units:
            for ref in extract_references(unit_text):
                stats["references_found"] += 1
                if ref.instrument_key is None:
                    stats["internal_references_skipped"] += 1
                    continue
                meta = {
                    "wp5": True,
                    "round": round_no,
                    "pattern": ref.pattern,
                    "instrument_key": ref.instrument_key,
                    "clause_path": ref.clause_path,
                    "from_label": unit_label,
                    "source_version_id": sv_id,
                    "char_start": ref.start,
                    "char_end": ref.end,
                }
                mid = resolve_reference(ref, alias_map, regex_aliases)
                quote = context_quote(unit_text, ref)
                if mid is not None:
                    if manifest_doc.get(mid) == source_doc_id:
                        stats["self_citations_skipped"] += 1
                        continue
                    stats["resolved"] += 1
                    if insert_edge(conn, from_type, unit_id, "target_manifest", mid,
                                   quote, 1.0, "approved", meta):
                        stats["edges_inserted_resolved"] += 1
                    stats["stale_external_edges_deleted"] += delete_stale_external(
                        conn, from_type, unit_id, ref.instrument_key
                    )
                else:
                    if insert_edge(conn, from_type, unit_id, "external_reference",
                                   ref.instrument_key, quote, 0.5, "pending_review", meta):
                        stats["edges_inserted_external"] += 1
                    info = unresolved.setdefault(
                        ref.instrument_key,
                        {
                            "display": display_name(ref.instrument_text),
                            "example": ref.raw[:120],
                            "category": default_category(ref.pattern, ref.instrument_key),
                            "count": 0,
                            "patterns": set(),
                            "documents": set(),
                        },
                    )
                    info["count"] += 1
                    info["patterns"].add(ref.pattern)
                    info["documents"].add(title[:120])

    stats["unresolved_keys"] = len(unresolved)
    for key in sorted(unresolved):
        is_new, aliases_added = add_manifest_row(conn, key, unresolved[key], round_no)
        stats["aliases_added"] += aliases_added
        if is_new:
            stats["manifest_rows_added"] += 1
            oos = classify_out_of_scope(key, unresolved[key]["display"])
            if oos:
                stats["manifest_rows_out_of_scope"] += 1
            stats["new_manifest_rows"].append(
                {
                    "instrument_name": unresolved[key]["display"],
                    "normalized_key": key,
                    "category": unresolved[key]["category"],
                    "status": "out_of_scope" if oos else "pending",
                    "out_of_scope_category": oos,
                    "citations": unresolved[key]["count"],
                }
            )
    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="WP5 citation closure loop (Phase 3)")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the full loop in one transaction and roll back at the end")
    ap.add_argument("--max-rounds", type=int, default=10, help="safety cap on closure rounds")
    ap.add_argument("--source-version", default="", help="restrict to one source_version uuid")
    ap.add_argument("--limit", type=int, default=0, help="cap documents processed (smoke tests)")
    ap.add_argument("--report", default="reports/citation_closure.json")
    args = ap.parse_args()

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    escalations: list[str] = []
    rounds: list[dict[str, Any]] = []
    fixpoint = False

    with psycopg.connect(dsn) as conn:
        for round_no in range(1, args.max_rounds + 1):
            stats = run_round(conn, args, round_no, escalations)
            rounds.append(stats)
            if not args.dry_run:
                conn.commit()
            print(
                f"round {round_no}: docs={stats['documents_processed']} "
                f"refs={stats['references_found']} resolved={stats['resolved']} "
                f"unresolved_keys={stats['unresolved_keys']} "
                f"new_manifest_rows={stats['manifest_rows_added']}",
                flush=True,
            )
            if stats["unresolved_keys"] == 0 and stats["manifest_rows_added"] == 0:
                fixpoint = True
                break
        else:
            escalations.append(
                f"--max-rounds={args.max_rounds} reached without fixpoint; "
                "inspect the unresolved keys in the last round."
            )

        edges_by_relation = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT relation, count(*) FROM legal_edges GROUP BY relation ORDER BY relation"
            ).fetchall()
        }
        unresolved_external = conn.execute(
            "SELECT count(*) FROM legal_edges "
            "WHERE relation = %s AND to_type = 'external_reference'",
            (RELATION,),
        ).fetchone()[0]
        wp5_edges = conn.execute(
            "SELECT to_type, count(*) FROM legal_edges "
            "WHERE relation = %s AND metadata_json->>'wp5' = 'true' GROUP BY to_type",
            (RELATION,),
        ).fetchall()
        if args.dry_run:
            conn.rollback()

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dry_run": args.dry_run,
        "rounds_run": len(rounds),
        "fixpoint_reached": fixpoint,
        "unresolved_external_references": unresolved_external,
        "edges_by_relation": edges_by_relation,
        "wp5_cites_edges_by_to_type": {r[0]: r[1] for r in wp5_edges},
        "new_manifest_rows_added_total": sum(r["manifest_rows_added"] for r in rounds),
        "rounds": rounds,
        "escalations": escalations,
    }
    out = json.dumps(report, indent=2, default=str)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0 if fixpoint else 1


if __name__ == "__main__":
    raise SystemExit(main())

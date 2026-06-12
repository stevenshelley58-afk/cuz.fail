"""WP5 - deterministic citation closure over acquired source chunks.

Drains source_versions that have chunks and no WP5 ``cites`` legal edge yet.
For each chunk, a deterministic regex pass finds instrument references, resolves
them against target_manifest / instrument_aliases, and writes idempotent
``legal_edges`` rows. Unresolved references become pending target_manifest rows
plus exact aliases so the WP4/WP5 fixpoint can continue without AI decisions.

Run inside the api container:
    python /app/scripts/wp5_citations.py --report /app/reports/citation_closure.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402

NS = uuid.UUID("61b95508-8ac2-4d19-bb5b-79a6b4f3bf33")
DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "citation_closure.json"
NO_REFS_TARGET = "wp5:no_instrument_references"

REFERENCE_RE = re.compile(
    r"\b("
    r"State Planning Policy [0-9.]+|"
    r"Development Control Policy [0-9.]+|"
    r"Local Planning Scheme No\.? ?\d+|"
    r"R-Codes|Residential Design Codes|"
    r"(?-i:[A-Z][A-Za-z]*(?:\s+(?:and|of|the|[A-Z][A-Za-z]*)){0,6})\s+(?:Act|Regulations) \d{4}|"
    r"AS/NZS [0-9.]+|"
    r"NCC|Building Code of Australia"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ManifestTarget:
    id: str
    instrument_name: str
    category: str | None = None
    issuing_authority: str | None = None


@dataclass(frozen=True)
class AliasTarget:
    alias_text: str
    match_kind: str
    target: ManifestTarget


@dataclass(frozen=True)
class ReferenceHit:
    reference: str
    quote: str
    start: int
    end: int


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def compact_reference(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_reference_text(value: str) -> str:
    ref = compact_reference(value)
    acronym_prefixed = re.fullmatch(
        r"[A-Z]{2,8}\s+Act\s+(.+\s+(?:Act|Regulations)\s+\d{4})",
        ref,
    )
    if acronym_prefixed:
        return compact_reference(acronym_prefixed.group(1))
    return ref


def deterministic_id(kind: str, *parts: object) -> str:
    return str(uuid.uuid5(NS, "|".join([kind, *(str(p) for p in parts)])))


def sentence_for_match(text_value: str, start: int, end: int) -> str:
    left = max(text_value.rfind(".", 0, start), text_value.rfind("?", 0, start), text_value.rfind("!", 0, start))
    right_candidates = [i for i in (text_value.find(".", end), text_value.find("?", end), text_value.find("!", end)) if i >= 0]
    right = min(right_candidates) + 1 if right_candidates else len(text_value)
    sentence = text_value[left + 1 : right]
    return re.sub(r"\s+", " ", sentence).strip() or compact_reference(text_value[start:end])


def extract_references(chunk_text: str) -> list[ReferenceHit]:
    hits: list[ReferenceHit] = []
    seen: set[tuple[str, str]] = set()
    for match in REFERENCE_RE.finditer(chunk_text or ""):
        ref = normalize_reference_text(match.group(1))
        quote = sentence_for_match(chunk_text, match.start(1), match.end(1))
        key = (norm(ref), norm(quote))
        if key in seen:
            continue
        seen.add(key)
        hits.append(ReferenceHit(reference=ref, quote=quote, start=match.start(1), end=match.end(1)))
    return hits


def alias_candidates(reference: str) -> list[str]:
    ref = compact_reference(reference)
    candidates = [ref]
    spp = re.fullmatch(r"State Planning Policy ([0-9.]+)", ref, flags=re.IGNORECASE)
    if spp:
        candidates.append(f"SPP {spp.group(1)}")
    dc = re.fullmatch(r"Development Control Policy ([0-9.]+)", ref, flags=re.IGNORECASE)
    if dc:
        candidates.append(f"DC {dc.group(1)}")
    scheme = re.fullmatch(r"Local Planning Scheme No\.? ?(\d+)", ref, flags=re.IGNORECASE)
    if scheme:
        candidates.extend([f"LPS {scheme.group(1)}", f"Local Planning Scheme {scheme.group(1)}"])
    if norm(ref) == "building code of australia":
        candidates.append("BCA")
    if norm(ref) == "ncc":
        candidates.append("National Construction Code")
    out: list[str] = []
    for candidate in candidates:
        if norm(candidate) not in {norm(x) for x in out}:
            out.append(candidate)
    return out


def infer_manifest_category(reference: str) -> tuple[str, str]:
    low = norm(reference)
    if low.startswith("state planning policy") or low in {"r-codes", "residential design codes"}:
        return "state_planning_policy", "Western Australian Planning Commission"
    if low.startswith("development control policy"):
        return "dc_policy", "Western Australian Planning Commission"
    if low.startswith("local planning scheme"):
        return "local_planning_scheme", ""
    if low.endswith(" act 2005") or " act " in low:
        return "act", "Government of Western Australia"
    if " regulations " in low:
        return "regulations", "Government of Western Australia"
    if low.startswith("as/nzs"):
        return "standard", "Standards Australia"
    if low in {"ncc", "building code of australia"}:
        return "building_code", "Australian Building Codes Board"
    return "unknown", ""


def resolve_reference(
    reference: str,
    manifests: list[ManifestTarget],
    aliases: list[AliasTarget],
) -> ManifestTarget | None:
    by_name = {norm(m.instrument_name): m for m in manifests}
    for candidate in alias_candidates(reference):
        direct = by_name.get(norm(candidate))
        if direct is not None:
            return direct

    exact_aliases = {norm(a.alias_text): a.target for a in aliases if a.match_kind == "exact"}
    for candidate in alias_candidates(reference):
        direct = exact_aliases.get(norm(candidate))
        if direct is not None:
            return direct

    for alias in aliases:
        if alias.match_kind != "regex":
            continue
        try:
            if re.fullmatch(alias.alias_text, reference, flags=re.IGNORECASE):
                return alias.target
        except re.error:
            continue
    return None


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def load_targets(conn: Connection) -> tuple[list[ManifestTarget], list[AliasTarget]]:
    manifest_rows = conn.execute(
        text("SELECT id::text, instrument_name, category, issuing_authority FROM target_manifest")
    ).mappings()
    manifests = [
        ManifestTarget(
            id=str(row["id"]),
            instrument_name=str(row["instrument_name"]),
            category=row["category"],
            issuing_authority=row["issuing_authority"],
        )
        for row in manifest_rows
    ]
    by_id = {m.id: m for m in manifests}
    alias_rows = conn.execute(
        text(
            """
            SELECT alias_text, match_kind, canonical_manifest_id::text AS canonical_manifest_id
            FROM instrument_aliases
            """
        )
    ).mappings()
    aliases = [
        AliasTarget(str(row["alias_text"]), str(row["match_kind"]), by_id[str(row["canonical_manifest_id"])])
        for row in alias_rows
        if str(row["canonical_manifest_id"]) in by_id
    ]
    return manifests, aliases


def queued_versions(conn: Connection, limit: int) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT sv.id::text AS source_version_id, sv.source_id::text AS source_id,
               sd.title, sd.authority, sd.source_type
        FROM source_versions sv
        JOIN source_documents sd ON sd.id = sv.source_id
        WHERE EXISTS (
            SELECT 1 FROM source_chunks sc WHERE sc.source_version_id = sv.id
        )
          AND NOT EXISTS (
            SELECT 1 FROM legal_edges le
            WHERE le.relation = 'cites'
              AND le.metadata_json->>'wp5' = 'true'
              AND le.metadata_json->>'source_version_id' = sv.id::text
          )
        ORDER BY sd.title, sv.id
        LIMIT CASE WHEN :limit > 0 THEN :limit ELSE 2147483647 END
        """
    )
    return [dict(row) for row in conn.execute(sql, {"limit": limit}).mappings()]


def chunks_for_version(conn: Connection, source_version_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT id::text AS chunk_id, chunk_index, text
            FROM source_chunks
            WHERE source_version_id = CAST(:source_version_id AS uuid)
            ORDER BY chunk_index
            """
        ),
        {"source_version_id": source_version_id},
    ).mappings()
    return [dict(row) for row in rows]


def ensure_pending_manifest(conn: Connection, reference: str, dry_run: bool) -> ManifestTarget:
    category, authority = infer_manifest_category(reference)
    manifest_id = deterministic_id("manifest", reference, authority)
    target = ManifestTarget(manifest_id, reference, category, authority)
    if dry_run:
        return target
    metadata = json.dumps({"wp5": True, "created_from_unresolved_reference": reference})
    row = conn.execute(
        text(
            """
            INSERT INTO target_manifest (id, instrument_name, category, issuing_authority,
                status, notes, metadata_json, created_at, updated_at)
            VALUES (CAST(:id AS uuid), :instrument_name, :category, :authority, 'pending',
                :notes, CAST(:metadata AS jsonb), now(), now())
            ON CONFLICT (instrument_name, issuing_authority) DO UPDATE
                SET updated_at = now()
            RETURNING id::text
            """
        ),
        {
            "id": manifest_id,
            "instrument_name": reference,
            "category": category,
            "authority": authority,
            "notes": "WP5 unresolved citation placeholder; run WP4 acquisition after URL discovery.",
            "metadata": metadata,
        },
    ).mappings().first()
    target_id = str(row["id"]) if row else manifest_id
    alias_id = deterministic_id("alias", reference, "exact")
    conn.execute(
        text(
            """
            INSERT INTO instrument_aliases (id, alias_text, canonical_manifest_id, match_kind,
                created_at, updated_at)
            VALUES (CAST(:id AS uuid), :alias_text, CAST(:target_id AS uuid), 'exact', now(), now())
            ON CONFLICT (alias_text, match_kind) DO NOTHING
            """
        ),
        {"id": alias_id, "alias_text": reference, "target_id": target_id},
    )
    return ManifestTarget(target_id, reference, category, authority)


def insert_citation_edge(
    conn: Connection,
    *,
    source_version_id: str,
    chunk_id: str,
    target: ManifestTarget,
    hit: ReferenceHit,
    resolved: bool,
    dry_run: bool,
) -> str:
    edge_id = deterministic_id("edge", "source_chunk", chunk_id, "target_manifest", target.id, "cites")
    if dry_run:
        return edge_id
    metadata = json.dumps(
        {
            "wp5": True,
            "source_version_id": source_version_id,
            "reference_text": hit.reference,
            "resolved": resolved,
        }
    )
    conn.execute(
        text(
            """
            INSERT INTO legal_edges (id, from_type, from_ref, to_type, to_ref, relation,
                evidence_quote, confidence, review_status, metadata_json, created_at, updated_at)
            VALUES (CAST(:id AS uuid), 'source_chunk', :chunk_id, 'target_manifest',
                :target_id, 'cites', :quote, :confidence, 'pending_review',
                CAST(:metadata AS jsonb), now(), now())
            ON CONFLICT (from_type, from_ref, to_type, to_ref, relation) DO UPDATE
                SET evidence_quote = EXCLUDED.evidence_quote,
                    metadata_json = legal_edges.metadata_json || EXCLUDED.metadata_json,
                    updated_at = now()
            """
        ),
        {
            "id": edge_id,
            "chunk_id": chunk_id,
            "target_id": target.id,
            "quote": hit.quote,
            "confidence": 0.95 if resolved else 0.55,
            "metadata": metadata,
        },
    )
    return edge_id


def insert_no_refs_marker(conn: Connection, source_version_id: str, dry_run: bool) -> str:
    edge_id = deterministic_id("edge", "source_version", source_version_id, "external_reference", NO_REFS_TARGET, "cites")
    if dry_run:
        return edge_id
    metadata = json.dumps({"wp5": True, "source_version_id": source_version_id, "no_references": True})
    conn.execute(
        text(
            """
            INSERT INTO legal_edges (id, from_type, from_ref, to_type, to_ref, relation,
                evidence_quote, confidence, review_status, metadata_json, created_at, updated_at)
            VALUES (CAST(:id AS uuid), 'source_version', :source_version_id, 'external_reference',
                :target, 'cites', :quote, 1.0, 'approved', CAST(:metadata AS jsonb), now(), now())
            ON CONFLICT (from_type, from_ref, to_type, to_ref, relation) DO UPDATE
                SET evidence_quote = EXCLUDED.evidence_quote,
                    metadata_json = legal_edges.metadata_json || EXCLUDED.metadata_json,
                    updated_at = now()
            """
        ),
        {
            "id": edge_id,
            "source_version_id": source_version_id,
            "target": NO_REFS_TARGET,
            "quote": "WP5 deterministic citation pass found no instrument references.",
            "metadata": metadata,
        },
    )
    return edge_id


def process_version(
    conn: Connection,
    version: dict[str, Any],
    manifests: list[ManifestTarget],
    aliases: list[AliasTarget],
    dry_run: bool,
) -> dict[str, Any]:
    source_version_id = str(version["source_version_id"])
    items: list[dict[str, Any]] = []
    resolved_count = 0
    unresolved_count = 0
    edges = 0

    for chunk in chunks_for_version(conn, source_version_id):
        for hit in extract_references(str(chunk["text"] or "")):
            target = resolve_reference(hit.reference, manifests, aliases)
            resolved = target is not None
            if target is None:
                target = ensure_pending_manifest(conn, hit.reference, dry_run=dry_run)
                unresolved_count += 1
            else:
                resolved_count += 1
            edge_id = insert_citation_edge(
                conn,
                source_version_id=source_version_id,
                chunk_id=str(chunk["chunk_id"]),
                target=target,
                hit=hit,
                resolved=resolved,
                dry_run=dry_run,
            )
            edges += 1
            items.append(
                {
                    "chunk_id": str(chunk["chunk_id"]),
                    "chunk_index": int(chunk["chunk_index"]),
                    "reference": hit.reference,
                    "quote": hit.quote,
                    "target_manifest_id": target.id,
                    "resolved": resolved,
                    "edge_id": edge_id,
                }
            )

    if not items:
        marker_id = insert_no_refs_marker(conn, source_version_id, dry_run=dry_run)
        edges += 1
        items.append({"no_references": True, "edge_id": marker_id})

    return {
        "source_version_id": source_version_id,
        "source_id": str(version["source_id"]),
        "title": version["title"],
        "source_type": version["source_type"],
        "resolved": resolved_count,
        "unresolved_manifest_rows": unresolved_count,
        "edges": edges,
        "items": items,
    }


def remaining_queue_count(conn: Connection) -> int:
    row = conn.execute(
        text(
            """
            SELECT count(*)
            FROM source_versions sv
            WHERE EXISTS (SELECT 1 FROM source_chunks sc WHERE sc.source_version_id = sv.id)
              AND NOT EXISTS (
                SELECT 1 FROM legal_edges le
                WHERE le.relation = 'cites'
                  AND le.metadata_json->>'wp5' = 'true'
                  AND le.metadata_json->>'source_version_id' = sv.id::text
              )
            """
        )
    ).first()
    return int(row[0]) if row else 0


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="max source_versions to process (0 = all queued)")
    parser.add_argument("--worker-id", default=f"wp5-{socket.gethostname()}")
    parser.add_argument("--dry-run", action="store_true", help="scan and report without DB writes")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    engine = create_engine(database_url())
    processed: list[dict[str, Any]] = []
    summary = {"versions": 0, "resolved": 0, "unresolved_manifest_rows": 0, "edges": 0, "errors": 0}
    escalations: list[str] = []

    with engine.begin() as conn:
        manifests, aliases = load_targets(conn)
        versions = queued_versions(conn, args.limit)
        for idx, version in enumerate(versions, start=1):
            print(f"[{idx}/{len(versions)}] {version['title']}", flush=True)
            try:
                if args.dry_run:
                    result = process_version(conn, version, manifests, aliases, dry_run=True)
                else:
                    with conn.begin_nested():
                        result = process_version(conn, version, manifests, aliases, dry_run=False)
            except Exception as exc:  # noqa: BLE001 - keep the queue moving
                summary["errors"] += 1
                escalations.append(f"{version['source_version_id']}: {exc}")
                continue
            processed.append(result)
            summary["versions"] += 1
            summary["resolved"] += result["resolved"]
            summary["unresolved_manifest_rows"] += result["unresolved_manifest_rows"]
            summary["edges"] += result["edges"]

        remaining = remaining_queue_count(conn) if not args.dry_run else len(versions)

    report = {
        "wp": "WP5",
        "worker": args.worker_id,
        "dry_run": args.dry_run,
        "summary": summary,
        "remaining_queue_count": remaining,
        "escalations": escalations,
        "versions": processed,
    }
    write_report(Path(args.report), report)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

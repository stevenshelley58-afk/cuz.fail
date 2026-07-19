"""WP9 — close out remaining DB population gaps after WP6.

Subcommands (each idempotent, safe to re-run):

  skill-version    Backfill skill_versions row 'wp6-extractor-v1' and stamp the
                   WP6 rule_candidates / rules rows that reference it.
  source-reviews   Automated licence review pass: official *.wa.gov.au sources
                   get licence_status='approved'; everything else
                   'pending_review'. Writes a source_reviews row per decision.
  legal-edges      Populate legal_edges: 'references_definition' edges from
                   rule-bearing/procedural clauses to definition clauses, and
                   'performance_alternative_to' edges between deemed_to_comply
                   and design_principle rules sharing a base rule key within
                   one source version.
  golden-fixture   Seed the M1 golden-fixture project (244 Vincent St, North
                   Perth — zone/R-code R60) with confirmed demo PropertyFacts.
  run-check        Execute the deterministic compliance engine against the
                   golden-fixture project and print the results.
  db-state         Regenerate the db_state report (row counts + alembic head).
  all              Run everything above in order.

Usage (inside the api container):
  python /app/scripts/wp9_complete_db.py <subcommand> [--report /app/reports/wp9.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from typing import Any

import psycopg
from psycopg.types.json import Json

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA (same as WP6)
EXPECTED_HEAD = "0019_rule_decode_logic"

GOLDEN_PROJECT_NAME = "M1 Golden Fixture — 244 Vincent Street, North Perth WA 6006"

# Demo measurements for the golden fixture. These are fixture inputs for an
# advisory engine run — not survey data. Provenance records that explicitly.
GOLDEN_FACTS: list[tuple[str, dict[str, Any], float]] = [
    ("zone", {"code": "R60"}, 0.7),
    ("r_code", {"code": "R60"}, 0.7),
    ("proposed_setback_front_m", {"value": 4.5, "unit": "m"}, 0.9),
    ("proposed_setback_rear_m", {"value": 3.5, "unit": "m"}, 0.9),
    ("proposed_setback_side_primary_m", {"value": 1.5, "unit": "m"}, 0.9),
    ("proposed_setback_side_secondary_m", {"value": 1.5, "unit": "m"}, 0.9),
    ("proposed_site_cover_pct", {"value": 45.0, "unit": "%"}, 0.9),
    ("proposed_open_space_pct", {"value": 50.0, "unit": "%"}, 0.9),
    ("proposed_garage_width_m", {"value": 5.5, "unit": "m"}, 0.9),
]

APPROVED_LICENCE_DOMAINS = (
    ".wa.gov.au",
    "legislation.wa.gov.au",
)


def dsn() -> str:
    return (
        os.environ["DATABASE_URL"]
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )


# ---------------------------------------------------------------------------
# skill-version
# ---------------------------------------------------------------------------


def backfill_skill_version(conn: psycopg.Connection) -> dict:
    sv_id = "wp6-extractor-v1"
    manifest = {
        "skill": "wp6-extractor",
        "pipeline": "3-pass blind ensemble (2x minimax + 1x openai/openrouter), "
                    "deterministic validators, challenge-round adjudication",
        "script": "scripts/wp6_extract.py",
    }
    conn.execute(
        """
        INSERT INTO skill_versions (id, skill_name, version, content_hash, status,
            active_from, manifest_json, eval_summary_json, created_at, updated_at)
        VALUES (%s, 'wp6-extractor', 'v1', %s, 'active', now(), %s, '{}', now(), now())
        ON CONFLICT (id) DO NOTHING
        """,
        (sv_id, hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
         Json(manifest)),
    )
    rc = conn.execute(
        "UPDATE rule_candidates SET skill_version_id = %s "
        "WHERE skill_version_id IS NULL AND metadata_json->>'wp6' = 'true'",
        (sv_id,),
    ).rowcount
    ru = conn.execute(
        "UPDATE rules SET skill_version_id = %s "
        "WHERE skill_version_id IS NULL AND metadata_json->>'wp6' = 'true'",
        (sv_id,),
    ).rowcount
    conn.commit()
    return {"skill_version_id": sv_id, "candidates_stamped": rc, "rules_stamped": ru}


# ---------------------------------------------------------------------------
# source-reviews
# ---------------------------------------------------------------------------


def automated_licence_review(conn: psycopg.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT sv.id, sv.source_id, sd.org_id, sd.canonical_url, sv.licence_status
        FROM source_versions sv
        JOIN source_documents sd ON sd.id = sv.source_id
        WHERE sv.licence_status NOT IN ('approved', 'blocked')
          AND NOT EXISTS (
            SELECT 1 FROM source_reviews sr WHERE sr.source_version_id = sv.id
          )
        """
    ).fetchall()
    approved = pending = 0
    for sv_id, source_id, org_id, url, _status in rows:
        host = (url or "").split("//")[-1].split("/")[0].lower()
        is_official = any(
            host == d.lstrip(".") or host.endswith(d) for d in APPROVED_LICENCE_DOMAINS
        )
        new_status = "approved" if is_official else "pending_review"
        rationale = (
            f"Automated licence review: host {host!r} "
            + ("matches official WA Government domain allowlist."
               if is_official else "is not on the official domain allowlist; "
               "licence confirmation required before citation.")
        )
        conn.execute(
            "UPDATE source_versions SET licence_status = %s, updated_at = now() WHERE id = %s",
            (new_status, sv_id),
        )
        conn.execute(
            """
            INSERT INTO source_reviews (id, org_id, source_id, source_version_id,
                review_status, licence_status, notes, reviewed_at, decision_metadata_json)
            VALUES (%s, %s, %s, %s, 'approved', %s, %s, now(), %s)
            """,
            (str(uuid.uuid4()), org_id or ORG_ID, source_id, sv_id, new_status,
             rationale, Json({"actor": "system", "wp9": True, "host": host})),
        )
        approved += int(is_official)
        pending += int(not is_official)
    conn.commit()
    return {"reviewed": len(rows), "licence_approved": approved, "licence_pending": pending}


# ---------------------------------------------------------------------------
# legal-edges
# ---------------------------------------------------------------------------


def populate_legal_edges(conn: psycopg.Connection) -> dict:
    import re

    # 1. references_definition — a rule-bearing/procedural clause uses a term
    #    that a definition clause in the same source version defines.
    #    Definition clauses are bags of entries like:
    #      "Access" means ... / 'coastal hazard' means ... / Servicing Report – means ...
    #    Clause keys are synthetic, so terms come from the definition text.
    quoted = re.compile(r"['‘\"“]([A-Za-z][A-Za-z \-]{2,40}?)['’\"”]\s+means\b")
    dashed = re.compile(r"(?m)^\s*([A-Z][A-Za-z \-]{2,40}?)\s*[–—-]\s*means\b")

    defs = conn.execute(
        "SELECT source_version_id, clause_key, text FROM clauses "
        "WHERE disposition = 'definition'"
    ).fetchall()

    terms: list[tuple[str, str, str]] = []  # (source_version_id, def_clause_key, term)
    for sv_id, def_key, text in defs:
        found = set(quoted.findall(text or "")) | set(dashed.findall(text or ""))
        for t in found:
            t = t.strip().lower()
            if len(t) > 3:
                terms.append((str(sv_id), def_key, t))

    def_edges = 0
    for sv_id, def_key, term in terms:
        def_edges += conn.execute(
            """
            INSERT INTO legal_edges (id, from_type, from_ref, to_type, to_ref, relation,
                confidence, review_status, metadata_json, created_at, updated_at)
            SELECT gen_random_uuid(), 'clause', c.clause_key, 'clause', %(def_key)s,
                   'references_definition', 0.7, 'pending_review',
                   jsonb_build_object('wp9', true, 'term', %(term)s::text,
                                      'source_version_id', %(sv_id)s::text),
                   now(), now()
            FROM clauses c
            WHERE c.source_version_id = %(sv_id)s
              AND c.disposition IN ('rule_bearing', 'procedural')
              AND c.clause_key <> %(def_key)s
              AND position(%(term)s IN lower(c.text)) > 0
            ON CONFLICT (from_type, from_ref, to_type, to_ref, relation) DO NOTHING
            """,
            {"sv_id": sv_id, "def_key": def_key, "term": term},
        ).rowcount

    # 2. performance_alternative_to — design_principle rule is the performance
    #    pathway alternative to a deemed_to_comply rule with the same base key
    #    in the same source version (SPP 7.3 R-Codes structure).
    alt_edges = conn.execute(
        """
        INSERT INTO legal_edges (id, from_type, from_ref, to_type, to_ref, relation,
            confidence, review_status, metadata_json, created_at, updated_at)
        SELECT DISTINCT gen_random_uuid(), 'rule', dp.id::text, 'rule', dtc.id::text,
               'performance_alternative_to', 0.9, 'pending_review',
               jsonb_build_object('wp9', true,
                                  'base_rule_key', dtc.value_json->>'base_rule_key',
                                  'source_version_id', dtc.source_version_id::text),
               now(), now()
        FROM rules dtc
        JOIN rules dp
          ON dp.source_version_id = dtc.source_version_id
         AND coalesce(dp.value_json->>'base_rule_key', split_part(dp.rule_key, '.', 1))
           = coalesce(dtc.value_json->>'base_rule_key', split_part(dtc.rule_key, '.', 1))
        WHERE dtc.pathway = 'deemed_to_comply'
          AND dp.pathway = 'design_principle'
          AND dtc.lifecycle_status = 'approved'
          AND dp.lifecycle_status = 'approved'
        ON CONFLICT (from_type, from_ref, to_type, to_ref, relation) DO NOTHING
        """
    ).rowcount
    conn.commit()
    return {
        "definition_terms_found": len(terms),
        "references_definition": def_edges,
        "performance_alternative_to": alt_edges,
    }


# ---------------------------------------------------------------------------
# golden-fixture
# ---------------------------------------------------------------------------


def seed_golden_fixture(conn: psycopg.Connection) -> dict:
    row = conn.execute(
        "SELECT id FROM projects WHERE name = %s", (GOLDEN_PROJECT_NAME,)
    ).fetchone()
    if row:
        project_id = str(row[0])
        created = False
    else:
        project_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO projects (id, org_id, name, status, metadata_json, created_at, updated_at)
            VALUES (%s, %s, %s, 'active', %s, now(), now())
            """,
            (project_id, ORG_ID, GOLDEN_PROJECT_NAME,
             Json({"golden_fixture": "m1", "address": "244 Vincent Street, North Perth WA 6006"})),
        )
        created = True

    facts_inserted = 0
    for fact_type, value_json, confidence in GOLDEN_FACTS:
        exists = conn.execute(
            "SELECT 1 FROM property_facts WHERE project_id = %s AND fact_type = %s",
            (project_id, fact_type),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO property_facts (id, org_id, project_id, fact_type, value_json,
                confidence, method, provenance_json, review_status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'manual_demo', %s, 'confirmed', now(), now())
            """,
            (str(uuid.uuid4()), ORG_ID, project_id, fact_type, Json(value_json), confidence,
             Json({"kind": "golden_fixture", "method": "manual_demo",
                   "note": "M1 demo measurement — advisory engine verification input, "
                           "not survey data", "target_crs": "EPSG:7844"})),
        )
        facts_inserted += 1
    conn.commit()
    return {"project_id": project_id, "created": created, "facts_inserted": facts_inserted}


def run_check(conn: psycopg.Connection) -> dict:
    """Run the deterministic engine via its own SQLAlchemy session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SaSession

    from draftcheck.checks.engine import ComplianceEngine

    row = conn.execute(
        "SELECT id FROM projects WHERE name = %s", (GOLDEN_PROJECT_NAME,)
    ).fetchone()
    if not row:
        raise SystemExit("golden fixture project missing — run golden-fixture first")
    project_id = str(row[0])

    sa = create_engine(os.environ["DATABASE_URL"].replace(
        "postgresql://", "postgresql+psycopg://"))
    with SaSession(sa) as session:
        result = ComplianceEngine().run_check(project_id, ORG_ID, session)
        session.commit()
    return {
        "check_run_id": result.check_run_id,
        "status": result.status,
        "results": [
            {
                "check_key": r.check_key,
                "status": r.status,
                "threshold": r.threshold_value,
                "unit": r.threshold_unit,
                "measured": r.measured_value,
                "citation": r.citation,
                "note": r.note,
            }
            for r in result.results
        ],
    }


# ---------------------------------------------------------------------------
# db-state
# ---------------------------------------------------------------------------


def db_state(conn: psycopg.Connection) -> dict:
    head = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    extensions = [
        r[0]
        for r in conn.execute(
            "SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'vector') ORDER BY extname"
        ).fetchall()
    ]
    tables = [t[0] for t in conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename NOT LIKE 'procrastinate%' ORDER BY tablename"
    ).fetchall()]
    counts = {}
    for t in tables:
        counts[t] = conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]  # noqa: S608

    def group_counts(sql: str) -> dict[str, int]:
        return {str(row[0]): int(row[1]) for row in conn.execute(sql).fetchall()}

    def scalar_int(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])

    manifest_by_status = group_counts(
        "SELECT status, count(*) FROM target_manifest GROUP BY status ORDER BY status"
    )
    pending_target_manifest = int(manifest_by_status.get("pending", 0))
    auto_promoted_without_two_families = scalar_int(
        """
        SELECT count(*)
        FROM rule_candidates
        WHERE review_status = 'auto_promoted'
          AND (
            NOT (metadata_json ? 'families')
            OR jsonb_typeof(metadata_json -> 'families') <> 'array'
            OR jsonb_array_length(metadata_json -> 'families') < 2
          )
        """
    )
    open_conflict_findings = scalar_int(
        """
        SELECT count(*)
        FROM adversarial_findings
        WHERE status IN ('open', 'confirmed')
        """
    )

    def manifest_sample(status: str) -> list[dict[str, Any]]:
        return [
            {
                "id": str(row[0]),
                "instrument_name": row[1],
                "category": row[2],
                "issuing_authority": row[3],
                "canonical_url": row[4],
                "notes": row[5],
            }
            for row in conn.execute(
                """
                SELECT id, instrument_name, category, issuing_authority, canonical_url, notes
                FROM target_manifest
                WHERE status = %s
                ORDER BY issuing_authority, instrument_name
                LIMIT 200
                """,
                (status,),
            ).fetchall()
        ]

    return {
        "alembic_head": head[0] if head else None,
        "expected_alembic_head": EXPECTED_HEAD,
        "extensions": extensions,
        "row_counts": counts,
        "manifest_by_status": manifest_by_status,
        "manifest_by_category": group_counts(
            "SELECT category, count(*) FROM target_manifest GROUP BY category ORDER BY category"
        ),
        "manifest_by_issuing_authority_top": [
            {"issuing_authority": row[0], "count": int(row[1])}
            for row in conn.execute(
                """
                SELECT issuing_authority, count(*)
                FROM target_manifest
                GROUP BY issuing_authority
                ORDER BY count(*) DESC, issuing_authority
                LIMIT 100
                """
            ).fetchall()
        ],
        "pending_manifest_sample": manifest_sample("pending"),
        "blocked_manifest_sample": manifest_sample("blocked"),
        "metadata_only_manifest_sample": manifest_sample("metadata_only"),
        "out_of_scope_manifest_sample": manifest_sample("out_of_scope"),
        "failed_urls_sample": [
            {
                "source_fetch_log_id": str(row[0]),
                "status": row[1],
                "url": row[2],
                "source_title": row[3],
                "error": row[4],
                "requested_at": row[5].isoformat() if row[5] else None,
                "completed_at": row[6].isoformat() if row[6] else None,
            }
            for row in conn.execute(
                """
                SELECT sfl.id, sfl.status, sd.canonical_url, sd.title, sfl.error,
                       sfl.requested_at, sfl.completed_at
                FROM source_fetch_log sfl
                JOIN source_documents sd ON sd.id = sfl.source_id
                WHERE sfl.status NOT IN ('success', 'succeeded', 'ok')
                   OR sfl.error IS NOT NULL
                ORDER BY sfl.requested_at DESC
                LIMIT 200
                """
            ).fetchall()
        ],
        "source_versions_by_review_status": group_counts(
            "SELECT review_status, count(*) FROM source_versions GROUP BY review_status ORDER BY review_status"
        ),
        "source_versions_by_licence_status": group_counts(
            "SELECT licence_status, count(*) FROM source_versions GROUP BY licence_status ORDER BY licence_status"
        ),
        "source_versions_by_licence": group_counts(
            "SELECT coalesce(licence, ''), count(*) FROM source_versions GROUP BY coalesce(licence, '') ORDER BY coalesce(licence, '')"
        ),
        "source_citations_by_kind": group_counts(
            "SELECT citation_kind, count(*) FROM source_citations GROUP BY citation_kind ORDER BY citation_kind"
        ),
        "clauses_by_disposition": group_counts(
            "SELECT disposition, count(*) FROM clauses GROUP BY disposition ORDER BY disposition"
        ),
        "rule_candidates_by_review_status": group_counts(
            "SELECT review_status, count(*) FROM rule_candidates GROUP BY review_status ORDER BY review_status"
        ),
        "rules_by_lifecycle_status": group_counts(
            "SELECT lifecycle_status, count(*) FROM rules GROUP BY lifecycle_status ORDER BY lifecycle_status"
        ),
        "review_items_by_status": group_counts(
            "SELECT status, count(*) FROM review_items GROUP BY status ORDER BY status"
        ),
        "spend_events_by_provider": group_counts(
            "SELECT provider, count(*) FROM spend_events GROUP BY provider ORDER BY provider"
        ),
        "citation_summary": {
            "source_citations": int(counts.get("source_citations", 0)),
            "legal_edges": int(counts.get("legal_edges", 0)),
            "legal_edges_by_review_status": group_counts(
                "SELECT review_status, count(*) FROM legal_edges GROUP BY review_status ORDER BY review_status"
            ),
        },
        "wp6_summary": {
            "clauses": int(counts.get("clauses", 0)),
            "rule_candidates": int(counts.get("rule_candidates", 0)),
            "rules": int(counts.get("rules", 0)),
            "auto_promoted_candidates": scalar_int(
                "SELECT count(*) FROM rule_candidates WHERE review_status = 'auto_promoted'"
            ),
            "auto_promoted_without_two_model_families": auto_promoted_without_two_families,
        },
        "conflict_summary": {
            "adversarial_findings_by_status": group_counts(
                "SELECT status, count(*) FROM adversarial_findings GROUP BY status ORDER BY status"
            ),
            "open_conflict_findings": open_conflict_findings,
        },
        "acceptance": {
            "postgis_present": "postgis" in extensions,
            "vector_present": "vector" in extensions,
            "alembic_at_expected_head": (head[0] if head else None) == EXPECTED_HEAD,
            "target_manifest_pending": pending_target_manifest,
            "target_manifest_pending_zero": pending_target_manifest == 0,
            "auto_promoted_without_two_model_families": auto_promoted_without_two_families,
            "no_single_family_auto_promotions": auto_promoted_without_two_families == 0,
            "open_conflict_findings": open_conflict_findings,
            "no_open_conflict_findings": open_conflict_findings == 0,
        },
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

STEPS = {
    "skill-version": backfill_skill_version,
    "source-reviews": automated_licence_review,
    "legal-edges": populate_legal_edges,
    "golden-fixture": seed_golden_fixture,
    "run-check": run_check,
    "db-state": db_state,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=[*STEPS, "all"])
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    report: dict[str, Any] = {}
    with psycopg.connect(dsn()) as conn:
        steps = list(STEPS) if args.step == "all" else [args.step]
        for name in steps:
            print(f"== {name} ==", flush=True)
            report[name] = STEPS[name](conn)
            print(json.dumps(report[name], indent=2, default=str), flush=True)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())

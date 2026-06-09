"""
Seed legacy eval data into V3 database tables.

Strategy:
- rules: legacy JSONL has string IDs (sv_..., cl_...). We create stub
  source_versions + clauses rows keyed by a deterministic UUID derived from
  the legacy string ID, then insert rules referencing them.
- eval_cases: map legacy fields (id->case_key, track->suite_name/skill_name,
  name, input_json, expected_json, is_active->status)
- eval_runs: map to eval_case_id via case_key lookup, store legacy JSON in
  output_json/metrics_json

All inserts use ON CONFLICT DO NOTHING for idempotency.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

SEEDS_DIR = Path("/app/evals/seeds")
DATABASE_URL = os.environ["DATABASE_URL"]

# Deterministic UUID v5 namespace for legacy ID mapping
LEGACY_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def legacy_id_to_uuid(legacy_id: str) -> str:
    return str(uuid.uuid5(LEGACY_NS, legacy_id))


def parse_ts(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return s


def load_jsonl(path: Path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def seed_rules(cur, org_id: str) -> int:
    rows = load_jsonl(SEEDS_DIR / "rule_rows.jsonl")
    inserted = 0

    sv_ids = {r["source_version_id"] for r in rows}
    cl_ids = {r["clause_id"] for r in rows}

    cur.execute("SELECT id FROM source_documents LIMIT 1")
    src_doc_row = cur.fetchone()
    if not src_doc_row:
        print("  WARNING: no source_documents found, cannot seed rules", file=sys.stderr)
        return 0
    src_doc_id = str(src_doc_row["id"])

    now = datetime.now(timezone.utc).isoformat()

    for sv_id in sv_ids:
        sv_uuid = legacy_id_to_uuid(sv_id)
        cur.execute(
            """
            INSERT INTO source_versions
                (id, source_id, version_label, sha256, storage_manifest_json,
                 licence_status, review_status, fetched_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                sv_uuid,
                src_doc_id,
                "legacy-seed:" + sv_id,
                "legacy-seed-" + sv_id[:40],
                "{}",
                "approved",
                "approved",
                now, now, now,
            ),
        )

    for cl_id in cl_ids:
        cl_uuid = legacy_id_to_uuid(cl_id)
        matching_sv = next(
            (r["source_version_id"] for r in rows if r["clause_id"] == cl_id),
            list(sv_ids)[0],
        )
        sv_uuid = legacy_id_to_uuid(matching_sv)
        cur.execute(
            """
            INSERT INTO clauses
                (id, source_version_id, clause_key, clause_type, disposition,
                 text, metadata_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                cl_uuid,
                sv_uuid,
                cl_id,
                "clause",
                "approved",
                "Legacy seed clause: " + cl_id,
                "{}",
                now, now,
            ),
        )

    for row in rows:
        rule_id = legacy_id_to_uuid(row["id"])
        sv_uuid = legacy_id_to_uuid(row["source_version_id"])
        cl_uuid = legacy_id_to_uuid(row["clause_id"])

        value_json = row.get("value_json", "{}")
        if isinstance(value_json, str):
            try:
                json.loads(value_json)
            except Exception:
                value_json = "{}"
        else:
            value_json = json.dumps(value_json)

        condition_text = row.get("condition_text", "")
        condition_json = json.dumps({"text": condition_text}) if condition_text else "{}"

        cur.execute(
            """
            INSERT INTO rules
                (id, org_id, source_version_id, clause_id,
                 rule_key, rule_type, pathway, lifecycle_status,
                 operator, value_json, unit, condition_json, quote,
                 metadata_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                rule_id,
                org_id,
                sv_uuid,
                cl_uuid,
                row.get("rule_key", "unknown"),
                "requirement",
                "none",
                row.get("lifecycle_status", "approved"),
                row.get("operator"),
                value_json,
                row.get("unit"),
                condition_json,
                row.get("quote", ""),
                "{}",
                parse_ts(row.get("created_at")) or now,
                parse_ts(row.get("updated_at")) or now,
            ),
        )
        if cur.rowcount > 0:
            inserted += 1

    return inserted


def seed_eval_cases(cur):
    rows = load_jsonl(SEEDS_DIR / "golden_eval_cases.jsonl")
    inserted = 0
    case_id_map = {}

    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        legacy_id = row["id"]
        case_uuid = legacy_id_to_uuid(legacy_id)
        case_id_map[legacy_id] = case_uuid

        track = row.get("track", "retrieval")
        suite_name = "golden-" + track
        skill_name = track
        case_key = legacy_id
        name = row.get("name", legacy_id)

        input_json = row.get("input_json", "{}")
        if isinstance(input_json, str):
            try:
                input_json_parsed = json.loads(input_json)
            except Exception:
                input_json_parsed = {"raw": input_json}
        else:
            input_json_parsed = input_json

        expected_json = row.get("expected_json", "{}")
        if isinstance(expected_json, str):
            try:
                expected_json_parsed = json.loads(expected_json)
            except Exception:
                expected_json_parsed = {"raw": expected_json}
        else:
            expected_json_parsed = expected_json

        is_active = row.get("is_active", 1)
        status = "active" if is_active else "inactive"

        metadata = {
            "legacy_id": legacy_id,
            "name": name,
            "notes": row.get("notes", ""),
            "created_by": row.get("created_by", ""),
        }

        cur.execute(
            """
            INSERT INTO eval_cases
                (id, suite_name, case_key, skill_name, source_version_id,
                 input_json, expected_json, status, metadata_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NULL,
                    %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s)
            ON CONFLICT (suite_name, case_key) DO NOTHING
            """,
            (
                case_uuid,
                suite_name,
                case_key,
                skill_name,
                json.dumps(input_json_parsed),
                json.dumps(expected_json_parsed),
                status,
                json.dumps(metadata),
                parse_ts(row.get("created_at")) or now,
                parse_ts(row.get("updated_at")) or now,
            ),
        )
        if cur.rowcount > 0:
            inserted += 1

    return inserted, case_id_map


def seed_eval_runs(cur, case_id_map):
    rows = load_jsonl(SEEDS_DIR / "golden_eval_runs.jsonl")
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        run_id = legacy_id_to_uuid(row["id"])

        case_results_raw = row.get("case_results_json", "[]")
        if isinstance(case_results_raw, str):
            try:
                case_results = json.loads(case_results_raw)
            except Exception:
                case_results = []
        else:
            case_results = case_results_raw

        eval_case_id = None
        for cr in case_results:
            cid = cr.get("case_id")
            if cid and cid in case_id_map:
                eval_case_id = case_id_map[cid]
                break

        if not eval_case_id:
            print("  SKIP eval_run " + row["id"] + ": no matching eval_case found")
            continue

        status = "passed" if row.get("passed", 0) else "failed"
        metrics = row.get("metrics_json", "{}")
        if isinstance(metrics, str):
            try:
                metrics = json.loads(metrics)
            except Exception:
                metrics = {}

        output = {
            "legacy_id": row["id"],
            "track": row.get("track"),
            "case_count": row.get("case_count"),
            "passed_count": row.get("passed_count"),
            "failed_count": row.get("failed_count"),
            "engine_version": row.get("engine_version"),
            "run_by": row.get("run_by"),
            "commit_sha": row.get("commit_sha"),
            "model_version": row.get("model_version"),
            "case_results": case_results,
        }

        cur.execute(
            """
            INSERT INTO eval_runs
                (id, eval_case_id, skill_version_id, job_trace_id,
                 status, score, output_json, metrics_json,
                 started_at, finished_at, error)
            VALUES (%s, %s, NULL, NULL,
                    %s, NULL, %s::jsonb, %s::jsonb,
                    %s, %s, NULL)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                run_id,
                eval_case_id,
                status,
                json.dumps(output),
                json.dumps(metrics),
                parse_ts(row.get("started_at")) or now,
                parse_ts(row.get("finished_at")),
            ),
        )
        if cur.rowcount > 0:
            inserted += 1

    return inserted


def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("SELECT id FROM orgs ORDER BY created_at LIMIT 1")
        org_row = cur.fetchone()
        if not org_row:
            print("ERROR: no orgs found in database", file=sys.stderr)
            sys.exit(1)
        org_id = str(org_row["id"])
        print("Using org_id: " + org_id)

        print("Seeding rules...")
        rules_count = seed_rules(cur, org_id)
        print("  rules inserted: " + str(rules_count))

        print("Seeding eval_cases...")
        cases_count, case_id_map = seed_eval_cases(cur)
        print("  eval_cases inserted: " + str(cases_count))

        print("Seeding eval_runs...")
        runs_count = seed_eval_runs(cur, case_id_map)
        print("  eval_runs inserted: " + str(runs_count))

        conn.commit()
        print("\nDone. Committed.")

    except Exception as e:
        conn.rollback()
        print("ERROR: " + str(e), file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

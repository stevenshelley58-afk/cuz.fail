"""Run the mechanical middle of the council recipe for one council:

    structure pass -> decode (gpt-4o-mini) -> promote -> scope

Stops BEFORE the correction pass (which is calibration-gated: pilot with
--limit 25 --debug and eyeball before --apply). Idempotent throughout.

Run inside the api container (long: use a detached shell):
    python /app/scripts/run_council_pipeline.py --council "City of Fremantle"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, "/app/src")

import psycopg  # noqa: E402


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    tail = (r.stdout or r.stderr).strip()[-400:]
    print(tail, flush=True)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True)
    ap.add_argument("--decode-workers", type=int, default=12)
    args = ap.parse_args()
    council = args.council

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sv.id::text FROM source_versions sv
            JOIN source_documents sd ON sv.source_id = sd.id
            WHERE sd.local_government = %s
              AND NOT EXISTS (SELECT 1 FROM clauses cl WHERE cl.source_version_id = sv.id)
            """,
            (council,),
        )
        need_structure = [r[0] for r in cur.fetchall()]
    print(f"[1/4] structure pass: {len(need_structure)} versions", flush=True)
    for sv in need_structure:
        rc = run(["python", "/app/scripts/wp6_extract.py", "--source-version", sv, "--structure-only"])
        if rc != 0:
            print(f"STRUCTURE FAILED for {sv} (continuing)", flush=True)

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT sv.id::text FROM source_versions sv
            JOIN source_documents sd ON sv.source_id = sd.id
            JOIN clauses cl ON cl.source_version_id = sv.id
            WHERE sd.local_government = %s
              AND cl.disposition = ANY(ARRAY['rule_bearing','procedural'])
              AND NOT EXISTS (
                SELECT 1 FROM rule_candidates rc
                WHERE rc.clause_id = cl.id
                  AND rc.extractor_model = 'openai:gpt-4o-mini:decode')
            """,
            (council,),
        )
        need_decode = [r[0] for r in cur.fetchall()]
    print(f"[2/4] decode: {len(need_decode)} versions", flush=True)
    failures = 0
    for sv in need_decode:
        rc = run([
            "python", "/app/scripts/wp6_decode.py", "--source-version", sv,
            "--workers", str(args.decode_workers),
            "--report", f"/app/reports/wp6_decode_{sv}.json",
        ])
        if rc != 0:
            failures += 1
            print(f"DECODE FAILED for {sv} (continuing)", flush=True)

    print("[3/4] promote", flush=True)
    run(["python", "/app/scripts/wp6_promote_decode.py", "--apply",
         "--report", f"/app/reports/wp6_promote_{council.replace(' ', '_')}.json"])

    print("[4/4] scope", flush=True)
    run(["python", "/app/scripts/wp_scope_council.py", "--council", council])

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM rules WHERE lifecycle_status='approved' AND council_scope=%s",
            (council,),
        )
        approved = cur.fetchone()[0]
    print(json.dumps({"council": council, "structure_versions": len(need_structure),
                      "decode_versions": len(need_decode), "decode_failures": failures,
                      "approved_scoped_rules": approved}), flush=True)
    print("PIPELINE_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

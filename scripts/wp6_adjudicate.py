"""WP6 v2 — re-adjudicate stored rule candidates (family-aware core voting).

The first full-corpus WP6 run left 1,220 validator-passing candidates and
846 pending atoms stranded because consensus was demanded on the FULL atom
signature (including applicability metadata) and because two temp-0 passes
of the same model counted as two votes. This script re-runs adjudication
over what is already in rule_candidates using the corrected policy in
draftcheck.extraction.adjudication. NO LLM calls — pure DB.

Idempotent: a (clause, core) that already has a promoted wp6 rule is
skipped, so this is safe to run on every deploy (infra/v3/deploy.sh does).

    docker compose exec -T api python scripts/wp6_adjudicate.py            # dry run
    docker compose exec -T api python scripts/wp6_adjudicate.py --apply \
        --report /app/reports/wp6_adjudication.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import psycopg  # noqa: E402
from psycopg.types.json import Json, Jsonb  # noqa: E402

from draftcheck.extraction.adjudication import (  # noqa: E402
    PROMOTE,
    Vote,
    adjudicate,
    core_of,
)
from draftcheck.extraction.vocabulary import RULE_KEYS  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA


def fetch_votes(conn: psycopg.Connection) -> list[dict]:
    """Raw per-pass validator-passing wp6 candidates (the actual votes)."""
    rows = conn.execute(
        """
        SELECT id, source_version_id, clause_id, source_chunk_id, rule_key, rule_type,
               pathway, operator, (value_json->>'value')::float AS value, unit,
               condition_json, quote, extractor_model
        FROM rule_candidates
        WHERE metadata_json->>'wp6' = 'true'
          AND review_status = 'validators_passed'
          AND extraction_pass IS NOT NULL
          AND value_json->>'value' IS NOT NULL
        """,
    ).fetchall()
    cols = ("id", "source_version_id", "clause_id", "source_chunk_id", "rule_key",
            "rule_type", "pathway", "operator", "value", "unit", "condition_json",
            "quote", "extractor_model")
    return [dict(zip(cols, r)) for r in rows]


def already_promoted(conn: psycopg.Connection) -> set[tuple]:
    """(clause_id, core) pairs that already have an approved wp6 rule."""
    rows = conn.execute(
        """
        SELECT clause_id, value_json->>'base_rule_key', operator,
               (value_json->>'value')::float, unit
        FROM rules
        WHERE metadata_json->>'wp6' = 'true' AND lifecycle_status = 'approved'
        """,
    ).fetchall()
    return {
        (str(cl), (bk, op, round(val, 4), unit))
        for cl, bk, op, val, unit in rows
        if bk is not None and val is not None
    }


def to_vote(row: dict) -> Vote:
    cond = row["condition_json"] or {}
    return Vote(
        rule_key=row["rule_key"] or "",
        rule_type=row["rule_type"] or "standard",
        pathway=row["pathway"] or "none",
        operator=row["operator"] or "",
        value=float(row["value"]),
        unit=row["unit"],
        density_codes=tuple(sorted(str(c) for c in (cond.get("density_codes") or []))),
        dwelling_type=str(cond.get("dwelling_type") or "any"),
        model=row["extractor_model"] or "unknown",
        ref=str(row["id"]),
    )


def promote(conn: psycopg.Connection, group_rows: list[dict], decision) -> str | None:
    """Insert the approved rule + clause link; mirrors wp6_extract.promote_rule."""
    rep = max(group_rows, key=lambda r: len(r["quote"] or ""))
    codes = list(decision.density_codes)
    suffix = "_".join(c.replace("-", "").replace(".", "p") for c in codes) or "all"
    dw = decision.dwelling_type or "any"
    rule_key = f"{rep['rule_key']}.{suffix}" + ("" if dw == "any" else f".{dw}")
    applicability = {
        **(rep["condition_json"] or {}),
        "density_codes": codes,
        "dwelling_type": dw,
    }
    row = conn.execute(
        """
        INSERT INTO rules (id, org_id, source_version_id, clause_id, candidate_id, rule_key,
            rule_type, pathway, lifecycle_status, operator, value_json, unit, condition_json,
            quote, extractor_model, metadata_json, applicable_r_codes, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, 'approved', %s, %s, %s, %s, %s,
                %s, %s, %s, now(), now())
        ON CONFLICT (source_version_id, rule_key) DO UPDATE
            SET value_json = EXCLUDED.value_json, operator = EXCLUDED.operator,
                unit = EXCLUDED.unit, quote = EXCLUDED.quote, updated_at = now()
        RETURNING id
        """,
        (
            ORG_ID, rep["source_version_id"], rep["clause_id"], rep["id"], rule_key,
            decision.rule_type, decision.pathway, rep["operator"],
            Json({"value": float(rep["value"]), "applicability": applicability,
                  "confidence": decision.confidence, "base_rule_key": rep["rule_key"]}),
            rep["unit"], Json(applicability), rep["quote"],
            "ensemble:" + "+".join(decision.families),
            Json({"wp6": True, "adjudication": "v2-core-family",
                  "confidence": decision.confidence,
                  "families": list(decision.families),
                  "dissent": list(decision.dissent),
                  "vote_candidate_ids": [str(r["id"]) for r in group_rows]}),
            Json(codes) if codes else None,
        ),
    ).fetchone()
    rule_id = str(row[0]) if row else None
    if rule_id:
        conn.execute(
            """
            INSERT INTO rule_clause_links (id, rule_id, clause_id, source_version_id, link_type,
                quote, confidence, metadata_json, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, %s, 'primary', %s, %s, '{}', now(), now())
            ON CONFLICT (rule_id, clause_id, link_type) DO NOTHING
            """,
            (rule_id, rep["clause_id"], rep["source_version_id"], rep["quote"],
             decision.confidence),
        )
        conn.execute(
            """
            UPDATE rule_candidates
            SET review_status = 'auto_promoted', confidence = %s, auto_promoted_at = now(),
                metadata_json = metadata_json || %s, updated_at = now()
            WHERE id = ANY(%s)
            """,
            (decision.confidence,
             Jsonb({"adjudication": "v2-core-family", "promoted_rule_id": rule_id}),
             [r["id"] for r in group_rows]),
        )
    return rule_id


def resolve_review_items(conn: psycopg.Connection, clause_ids: list) -> int:
    """Close open wp6 review items for clauses with no remaining unresolved votes."""
    if not clause_ids:
        return 0
    cur = conn.execute(
        """
        UPDATE review_items ri
        SET status = 'resolved', updated_at = now(),
            metadata_json = metadata_json || '{"resolved_by": "wp6_adjudicate_v2"}'::jsonb
        WHERE ri.subject_type = 'clause_extraction'
          AND ri.status = 'open'
          AND ri.metadata_json->>'wp6' = 'true'
          AND ri.subject_id = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM rule_candidates rc
              WHERE rc.clause_id = ri.subject_id
                AND rc.review_status = 'validators_passed'
          )
        """,
        (clause_ids,),
    )
    return cur.rowcount or 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    report: dict[str, Any] = {"mode": "apply" if args.apply else "dry_run"}

    with psycopg.connect(dsn) as conn:
        rows = fetch_votes(conn)
        promoted_cores = already_promoted(conn)
        rules_before = conn.execute(
            "SELECT count(*) FROM rules WHERE metadata_json->>'wp6' = 'true'"
        ).fetchone()[0]

        groups: dict[tuple, list[dict]] = defaultdict(list)
        skipped_unknown_key = 0
        for r in rows:
            if r["rule_key"] not in RULE_KEYS:
                skipped_unknown_key += 1
                continue
            v = to_vote(r)
            groups[(str(r["clause_id"]), core_of(v))].append(r)

        promoted = 0
        skipped_already = 0
        pending_by_reason: Counter = Counter()
        promoted_clauses: list = []
        per_source: Counter = Counter()

        for (clause_id, core), group_rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
            if (clause_id, core) in promoted_cores:
                skipped_already += 1
                continue
            decision = adjudicate([to_vote(r) for r in group_rows])
            if decision.outcome == PROMOTE:
                promoted += 1
                per_source[str(group_rows[0]["source_version_id"])] += 1
                promoted_clauses.append(group_rows[0]["clause_id"])
                if args.apply:
                    promote(conn, group_rows, decision)
            else:
                pending_by_reason[decision.reason] += 1
                if args.apply:
                    conn.execute(
                        """
                        UPDATE rule_candidates
                        SET metadata_json = metadata_json || %s, updated_at = now()
                        WHERE id = ANY(%s)
                        """,
                        (Jsonb({"adjudication": "v2-core-family",
                               "pending_reason": decision.reason}),
                         [r["id"] for r in group_rows]),
                    )

        resolved_items = 0
        if args.apply:
            conn.commit()
            resolved_items = resolve_review_items(conn, promoted_clauses)
            conn.commit()

        rules_after = conn.execute(
            "SELECT count(*) FROM rules WHERE metadata_json->>'wp6' = 'true'"
        ).fetchone()[0]

        report.update({
            "vote_rows": len(rows),
            "core_groups": len(groups),
            "skipped_unknown_rule_key_votes": skipped_unknown_key,
            "skipped_already_promoted_groups": skipped_already,
            "promoted_groups": promoted,
            "pending_by_reason": dict(pending_by_reason),
            "review_items_resolved": resolved_items,
            "wp6_rules_before": rules_before,
            "wp6_rules_after": rules_after,
            "top_sources_by_promotions": per_source.most_common(10),
        })

    out = json.dumps(report, indent=2, default=str)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

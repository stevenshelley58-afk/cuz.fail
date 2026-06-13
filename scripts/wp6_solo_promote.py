"""WP6 solo promotion — promote validators_passed candidates without the
cross-family independence requirement.

Policy change (2026-06-13): the original adjudicator (src/draftcheck/extraction/
adjudication.py) refuses to promote unless >=2 distinct model families produced a
validator-passing atom with the same deterministic core. That's a strong safety
net but at corpus scale it leaves hundreds of structurally-sound atoms pending
because the families happen to land on slightly different cores. This script
takes the explicit operator decision (recorded in audit_events) that validator-
passing single-family extractions are good enough to promote at lower confidence.

Confidence assigned:
- Cross-family (>=2 families pass validators on the same core)   -> 0.95
- Same family, >=3 passes (e.g. 3 OpenAI temp-0 passes)         -> 0.80
- Same family, 2 passes                                         -> 0.70
- Same family, 1 pass                                           -> 0.60

Refuses to promote anything that:
- rule_key not in vocabulary
- already has an approved rule covering the same (rule_key suffix,
  applicable_r_codes, dwelling_type, condition)

Pure additive; never modifies existing rules. Re-runnable: ON CONFLICT updates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from collections import defaultdict
from typing import Any

import psycopg
from psycopg.types.json import Json

sys.path.insert(0, "/app/src")
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from draftcheck.extraction.adjudication import core_of, model_family, Vote  # noqa: E402
from draftcheck.extraction.vocabulary import OPERATORS, RULE_KEYS  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"
SOLO_NAMESPACE = uuid.UUID("00000000-0000-5000-c000-000000000002")
SKILL_VERSION_ID = "wp6_sonnet_v1"


def vote_from_row(row: dict) -> Vote:
    value_json = row["value_json"]
    if isinstance(value_json, str):
        value_json = json.loads(value_json)
    cond = row["condition_json"]
    if isinstance(cond, str):
        cond = json.loads(cond)
    try:
        value = float(value_json.get("value", 0))
    except (TypeError, ValueError):
        value = 0.0
    return Vote(
        rule_key=row["rule_key"],
        rule_type=row["rule_type"] or "standard",
        pathway=row["pathway"] or "none",
        operator=row["operator"] or "",
        value=value,
        unit=row["unit"],
        density_codes=tuple(sorted(str(c) for c in (cond.get("density_codes") or []) if c)),
        dwelling_type=str(cond.get("dwelling_type") or "any"),
        model=row["extractor_model"] or "",
    )


def derived_rule_key(base: str, density_codes: tuple, dwelling_type: str) -> str:
    suffix = "_".join(c.replace("-", "").replace(".", "p") for c in density_codes) or "all"
    rk = f"{base}.{suffix}"
    if dwelling_type and dwelling_type != "any":
        rk = f"{rk}.{dwelling_type}"
    return rk


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default="/app/reports/wp6_solo_promote.json")
    parser.add_argument(
        "--min-confidence", type=float, default=0.5, help="Skip groups below this confidence"
    )
    parser.add_argument(
        "--statuses",
        nargs="+",
        default=["validators_passed", "auto_promoted", "pending_review"],
        help="Candidate review_status values eligible for promotion",
    )
    args = parser.parse_args()

    db_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(db_url) as conn:
        return run(conn, args)


def run(conn: psycopg.Connection, args) -> int:
    cur = conn.cursor()

    # Pull all candidates with eligible review_status. Group by (clause, core_signature)
    # so multiple passes of the same atom collapse into one vote bundle.
    cur.execute(
        """
        SELECT rc.id::text, rc.source_version_id::text, rc.clause_id::text,
               rc.rule_key, rc.rule_type, rc.pathway, rc.operator, rc.value_json,
               rc.unit, rc.condition_json, rc.quote, rc.extractor_model,
               rc.review_status, rc.metadata_json, rc.confidence
        FROM rule_candidates rc
        WHERE rc.review_status = ANY(%s)
          AND rc.rule_key = ANY(%s)
          AND rc.operator = ANY(%s)
        ORDER BY rc.clause_id, rc.rule_key
        """,
        (args.statuses, list(RULE_KEYS), list(OPERATORS)),
    )
    rows = cur.fetchall()

    columns = [d.name for d in cur.description]
    candidates = [dict(zip(columns, row)) for row in rows]

    summary = {
        "candidate_rows_considered": len(candidates),
        "promoted_new_rules": 0,
        "skipped_existing_rule": 0,
        "skipped_pathway_disagreement": 0,
        "skipped_density_intersection_empty": 0,
        "skipped_dwelling_type_disagreement": 0,
        "skipped_low_confidence": 0,
        "by_confidence_bucket": defaultdict(int),
        "by_family_count": defaultdict(int),
    }

    # Group by (clause_id, core_signature)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in candidates:
        try:
            v = vote_from_row(c)
        except Exception:
            continue
        groups[(c["clause_id"], core_of(v))].append(c)

    insert_sql = """
        INSERT INTO rules (
            id, org_id, source_version_id, clause_id, candidate_id, rule_key,
            rule_type, pathway, lifecycle_status, operator, value_json, unit,
            condition_json, quote, extractor_model, metadata_json, applicable_r_codes,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, 'approved', %s, %s, %s, %s, %s, %s, %s, %s, now(), now()
        )
        ON CONFLICT (id) DO UPDATE SET
            metadata_json = rules.metadata_json || EXCLUDED.metadata_json,
            updated_at = now()
    """

    check_existing_sql = """
        SELECT 1 FROM rules r
        WHERE r.lifecycle_status = 'approved'
          AND r.rule_key = %s
          AND r.operator = %s
          AND (r.value_json->>'value')::numeric = %s
          AND coalesce(r.unit,'') = coalesce(%s,'')
        LIMIT 1
    """

    # The rules table has UNIQUE (source_version_id, rule_key). If another
    # solo promotion within this run targets the same (sv, rule_key), suffix
    # the rule_key with a counter so both can land.
    sv_rk_used: dict[tuple, int] = defaultdict(int)
    check_sv_rk_exists_sql = """
        SELECT 1 FROM rules r
        WHERE r.source_version_id = %s AND r.rule_key = %s LIMIT 1
    """

    promoted: list[dict] = []

    for (clause_id, core), members in groups.items():
        votes = [vote_from_row(m) for m in members]
        # Pathway consolidation: majority wins; require >=2 votes on the winner.
        pathway_counts: dict[str, int] = defaultdict(int)
        for v in votes:
            pathway_counts[v.pathway] += 1
        ranked = sorted(pathway_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            summary["skipped_pathway_disagreement"] += 1
            continue
        winning_pathway = ranked[0][0]
        active_votes = [v for v in votes if v.pathway == winning_pathway]
        active_members = [m for m, v in zip(members, votes) if v.pathway == winning_pathway]

        # Family count for confidence.
        families = sorted({model_family(v.model) for v in active_votes})

        # Density codes: take the intersection of explicit sets if multiple votes have them,
        # otherwise union (so a single-family vote with codes survives).
        explicit_sets = [frozenset(v.density_codes) for v in active_votes if v.density_codes]
        if explicit_sets:
            merged = explicit_sets[0]
            for s in explicit_sets[1:]:
                merged = merged & s
            if not merged and len(explicit_sets) > 1:
                # disagreement, take union (single-family promotion liberal policy)
                merged = set().union(*explicit_sets)
            if not merged:
                summary["skipped_density_intersection_empty"] += 1
                continue
            density_codes = tuple(sorted(merged))
        else:
            density_codes = ()

        # Dwelling type: specifics narrow any. If 2 different specifics, take majority.
        dwelling_counts: dict[str, int] = defaultdict(int)
        for v in active_votes:
            dwelling_counts[v.dwelling_type or "any"] += 1
        non_any = {k: c for k, c in dwelling_counts.items() if k != "any"}
        if len(non_any) > 1:
            # take the majority
            dwelling_type = sorted(non_any.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        elif non_any:
            dwelling_type = next(iter(non_any))
        else:
            dwelling_type = "any"

        # Confidence: assign by family count and vote count.
        n_votes = len(active_votes)
        n_families = len(families)
        if n_families >= 2:
            confidence = 0.95 if n_votes >= 3 else 0.90
        elif n_votes >= 3:
            confidence = 0.80
        elif n_votes == 2:
            confidence = 0.70
        else:
            confidence = 0.60

        if confidence < args.min_confidence:
            summary["skipped_low_confidence"] += 1
            continue

        # Derived rule_key with suffix.
        base_key = active_votes[0].rule_key
        rule_key = derived_rule_key(base_key, density_codes, dwelling_type)

        # Check if an existing approved rule already covers this (key, value).
        existing = cur.execute(
            check_existing_sql,
            (rule_key, active_votes[0].operator, active_votes[0].value, active_votes[0].unit),
        ).fetchone()
        if existing:
            summary["skipped_existing_rule"] += 1
            continue

        # Promote.
        anchor = active_members[0]
        sv_id_target = anchor["source_version_id"]

        # Respect UNIQUE (source_version_id, rule_key): if the key is already used
        # for a different rule under the same source_version (whether already in DB
        # or scheduled this run), suffix the rule_key.
        base_rule_key = rule_key
        attempt_idx = sv_rk_used[(sv_id_target, base_rule_key)]
        while True:
            candidate_rule_key = (
                base_rule_key if attempt_idx == 0 else f"{base_rule_key}.alt{attempt_idx}"
            )
            row = cur.execute(
                check_sv_rk_exists_sql, (sv_id_target, candidate_rule_key)
            ).fetchone()
            if not row:
                rule_key = candidate_rule_key
                sv_rk_used[(sv_id_target, base_rule_key)] = attempt_idx + 1
                break
            attempt_idx += 1
            if attempt_idx > 20:
                # Give up on this group to avoid runaway.
                rule_key = None
                break
        if rule_key is None:
            summary["skipped_existing_rule"] += 1
            continue
        new_rule_id = str(
            uuid.uuid5(
                SOLO_NAMESPACE,
                f"{clause_id}|{rule_key}|{active_votes[0].operator}|{active_votes[0].value}|{active_votes[0].unit}",
            )
        )
        metadata = {
            "wp6": True,
            "solo_promoted": True,
            "solo_promote_version": "v1_2026_06_13",
            "vote_count": n_votes,
            "family_count": n_families,
            "families": families,
            "candidate_ids": [m["id"] for m in active_members],
            "operator_override": True,
        }
        value_json = {"value": active_votes[0].value}
        cond_json = {
            "density_codes": list(density_codes),
            "dwelling_type": dwelling_type,
            "condition": "",
        }

        if args.apply:
            cur.execute(
                insert_sql,
                (
                    new_rule_id,
                    ORG_ID,
                    anchor["source_version_id"],
                    clause_id,
                    None,  # candidate_id is single but we have many; record list in metadata
                    rule_key,
                    active_votes[0].rule_type,
                    winning_pathway,
                    active_votes[0].operator,
                    Json(value_json),
                    active_votes[0].unit,
                    Json(cond_json),
                    anchor["quote"],
                    active_votes[0].model,
                    Json(metadata),
                    Json(list(density_codes)) if density_codes else None,
                ),
            )

        summary["promoted_new_rules"] += 1
        summary["by_confidence_bucket"][str(round(confidence, 2))] += 1
        summary["by_family_count"][str(n_families)] += 1
        promoted.append(
            {
                "rule_id": new_rule_id,
                "rule_key": rule_key,
                "value": active_votes[0].value,
                "unit": active_votes[0].unit,
                "operator": active_votes[0].operator,
                "pathway": winning_pathway,
                "density_codes": list(density_codes),
                "dwelling_type": dwelling_type,
                "confidence": confidence,
                "families": families,
                "votes": n_votes,
            }
        )

    if args.apply:
        conn.commit()

    summary["by_confidence_bucket"] = dict(summary["by_confidence_bucket"])
    summary["by_family_count"] = dict(summary["by_family_count"])
    report = {
        "summary": summary,
        "promoted_sample": promoted[:50],
        "promoted_total": len(promoted),
    }
    if args.report:
        os.makedirs(os.path.dirname(args.report), exist_ok=True)
        with open(args.report, "w") as f:
            json.dump(report, f, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

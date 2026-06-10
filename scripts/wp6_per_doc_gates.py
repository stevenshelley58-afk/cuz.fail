#!/usr/bin/env python3
"""WP6 — per-document acceptance gate checker (CORPUS_COMPLETENESS_PLAN Phase 4, read-only).

Evaluates EVERY active source_version (superseded_by_version_id IS NULL and
effective_to open) against the per-doc acceptance gate the plan makes a CI
assertion:

  1. clause_dispositions       — 100% clause dispositions (no 'manual_review'
                                 rows; a version with zero clauses fails because
                                 the structure pass has not run).
  2. orphan_numbers            — 0 unclaimed numbers: every numeric token in a
                                 Tier-1-topic rule-bearing clause must appear in
                                 a claimed quote (auto_promoted candidates +
                                 approved rules). Same sweep as
                                 wp6_extract.audit(), ported standalone.
  3. exception_language        — 0 unresolved exception-language clauses: every
                                 rule-bearing clause containing exception words
                                 (notwithstanding/despite/except where/unless/…)
                                 must have an approved rule_type='exception'
                                 atom linked to it (rules.clause_id or
                                 rule_clause_links).
  4. pending_review_drained    — 0 rule_candidates with review_status =
                                 'pending_review' for the version.

Writes reports/per_doc_gates.json: per-doc pass/fail with failing criterion
counts plus a corpus summary. Always exits 0 (it is a report; CI decides),
unless --strict is passed and any doc fails.

Runs INSIDE the api container like wp6_extract.py:

    docker exec draftcheck-wa-v3-api-1 python /app/scripts/wp6_per_doc_gates.py \
        --report /app/reports/per_doc_gates.json [--strict]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from typing import Iterable

sys.path.insert(0, "/app/src")
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from draftcheck.extraction.normalize import whitespace_normalize  # noqa: E402
from wp6_extract import EXCEPTION_WORDS, TIER1_TOPIC_RE  # noqa: E402

GATE_CRITERIA = (
    "clause_dispositions",
    "orphan_numbers",
    "exception_language",
    "pending_review_drained",
)

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_YEAR_RE = re.compile(r"(19|20)\d\d")


# ---------------------------------------------------------------------------
# Pure gate logic (unit-tested on plain dicts in tests/test_rule_matrix.py)
# ---------------------------------------------------------------------------


def orphan_number_sweep(
    rule_bearing_clauses: list[dict], claimed_quotes: Iterable[str], detail_limit: int = 10
) -> dict:
    """No-orphan-numbers sweep over Tier-1-topic rule-bearing clauses.

    Ported from wp6_extract.audit(): a numeric token is claimed when it appears
    in the whitespace-normalised concatenation of the claimed quotes. Zero and
    year-like tokens (19xx/20xx) are ignored.
    """
    claimed = whitespace_normalize(" ".join(q for q in claimed_quotes if q))
    orphan_clauses: list[dict] = []
    total_numbers = claimed_numbers = 0
    for clause in rule_bearing_clauses:
        text = clause.get("text") or ""
        if not TIER1_TOPIC_RE.search(text):
            continue
        nums = set(_NUM_RE.findall(whitespace_normalize(text)))
        nums = {n for n in nums if float(n) != 0 and not _YEAR_RE.fullmatch(n)}
        if not nums:
            continue
        total_numbers += len(nums)
        missing = sorted(n for n in nums if n not in claimed)
        claimed_numbers += len(nums) - len(missing)
        if missing:
            orphan_clauses.append(
                {"clause_path": clause.get("clause_path"), "orphan_numbers": missing[:20]}
            )
    return {
        "tier1_numeric_tokens": total_numbers,
        "claimed": claimed_numbers,
        "clauses_with_orphans": len(orphan_clauses),
        "detail": orphan_clauses[:detail_limit],
    }


def evaluate_doc(
    clauses: list[dict],
    claimed_quotes: Iterable[str],
    pending_review_count: int,
    exception_resolved_clause_ids: Iterable[str],
    detail_limit: int = 10,
) -> dict:
    """Evaluate the 4-criterion per-doc gate on plain rows (no DB).

    clauses: dicts with id, clause_path, disposition, text.
    Returns {"pass": bool, "failing_criteria": [...], "criteria": {...}}.
    """
    total = len(clauses)
    undispositioned = sum(
        1 for c in clauses if (c.get("disposition") or "manual_review") == "manual_review"
    )
    disp_pass = total > 0 and undispositioned == 0

    rule_bearing = [c for c in clauses if c.get("disposition") == "rule_bearing"]
    sweep = orphan_number_sweep(rule_bearing, claimed_quotes, detail_limit=detail_limit)

    resolved = {str(i) for i in exception_resolved_clause_ids}
    exception_clauses = [
        c for c in rule_bearing
        if any(w in (c.get("text") or "").lower() for w in EXCEPTION_WORDS)
    ]
    unresolved = [c for c in exception_clauses if str(c.get("id")) not in resolved]

    criteria = {
        "clause_dispositions": {
            "pass": disp_pass,
            "clauses_total": total,
            "undispositioned": undispositioned,
            "note": None if total else "no clauses extracted — structure pass has not run",
        },
        "orphan_numbers": {
            "pass": sweep["clauses_with_orphans"] == 0,
            **sweep,
        },
        "exception_language": {
            "pass": not unresolved,
            "exception_clauses": len(exception_clauses),
            "unresolved": len(unresolved),
            "unresolved_paths": [c.get("clause_path") for c in unresolved[:detail_limit]],
        },
        "pending_review_drained": {
            "pass": pending_review_count == 0,
            "pending_review": pending_review_count,
        },
    }
    failing = [k for k in GATE_CRITERIA if not criteria[k]["pass"]]
    return {"pass": not failing, "failing_criteria": failing, "criteria": criteria}


def summarize(doc_reports: list[dict]) -> dict:
    """Corpus summary over per-doc gate reports."""
    failing_by_criterion = {k: 0 for k in GATE_CRITERIA}
    docs_failing = 0
    for doc in doc_reports:
        if not doc["pass"]:
            docs_failing += 1
        for k in doc["failing_criteria"]:
            failing_by_criterion[k] += 1
    return {
        "docs_evaluated": len(doc_reports),
        "docs_passing": len(doc_reports) - docs_failing,
        "docs_failing": docs_failing,
        "failing_by_criterion": failing_by_criterion,
    }


# ---------------------------------------------------------------------------
# DB plumbing
# ---------------------------------------------------------------------------


def fetch_active_source_versions(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT sv.id, sd.title, sv.version_label
        FROM source_versions sv
        JOIN source_documents sd ON sd.id = sv.source_id
        WHERE sv.superseded_by_version_id IS NULL
          AND (sv.effective_to IS NULL OR sv.effective_to > now())
        ORDER BY sd.title, sv.fetched_at
        """,
    ).fetchall()
    return [{"id": str(r[0]), "title": r[1], "version_label": r[2]} for r in rows]


def gather_doc_inputs(conn, sv_id: str) -> dict:
    clauses = [
        {"id": str(r[0]), "clause_path": r[1], "disposition": r[2], "text": r[3]}
        for r in conn.execute(
            "SELECT id, clause_path, disposition, text FROM clauses "
            "WHERE source_version_id = %s",
            (sv_id,),
        ).fetchall()
    ]
    claimed_quotes = [
        r[0]
        for r in conn.execute(
            "SELECT quote FROM rule_candidates "
            "WHERE source_version_id = %s AND review_status = 'auto_promoted' "
            "UNION ALL "
            "SELECT quote FROM rules "
            "WHERE source_version_id = %s AND lifecycle_status = 'approved'",
            (sv_id, sv_id),
        ).fetchall()
    ]
    pending_review_count = conn.execute(
        "SELECT count(*) FROM rule_candidates "
        "WHERE source_version_id = %s AND review_status = 'pending_review'",
        (sv_id,),
    ).fetchone()[0]
    exception_resolved_clause_ids = {
        str(r[0])
        for r in conn.execute(
            "SELECT clause_id FROM rules "
            "WHERE source_version_id = %s AND lifecycle_status = 'approved' "
            "AND rule_type = 'exception' "
            "UNION "
            "SELECT rcl.clause_id FROM rule_clause_links rcl "
            "JOIN rules r ON r.id = rcl.rule_id "
            "WHERE rcl.source_version_id = %s AND r.lifecycle_status = 'approved' "
            "AND r.rule_type = 'exception'",
            (sv_id, sv_id),
        ).fetchall()
    }
    return {
        "clauses": clauses,
        "claimed_quotes": claimed_quotes,
        "pending_review_count": pending_review_count,
        "exception_resolved_clause_ids": exception_resolved_clause_ids,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", default="reports/per_doc_gates.json")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any active source_version fails the gate")
    ap.add_argument("--detail-limit", type=int, default=10,
                    help="max orphan/unresolved detail entries per doc")
    args = ap.parse_args()

    import psycopg

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    doc_reports: list[dict] = []
    with psycopg.connect(dsn) as conn:
        versions = fetch_active_source_versions(conn)
        for i, sv in enumerate(versions, start=1):
            inputs = gather_doc_inputs(conn, sv["id"])
            verdict = evaluate_doc(
                inputs["clauses"],
                inputs["claimed_quotes"],
                inputs["pending_review_count"],
                inputs["exception_resolved_clause_ids"],
                detail_limit=args.detail_limit,
            )
            doc_reports.append(
                {
                    "source_version_id": sv["id"],
                    "title": sv["title"],
                    "version_label": sv["version_label"],
                    **verdict,
                }
            )
            print(
                f"[{i}/{len(versions)}] {sv['id']} "
                f"{'PASS' if verdict['pass'] else 'FAIL ' + ','.join(verdict['failing_criteria'])}",
                flush=True,
            )

    summary = summarize(doc_reports)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "gate_criteria": list(GATE_CRITERIA),
        "summary": summary,
        "docs": doc_reports,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
        fh.write("\n")
    print(json.dumps({"report": args.report, **summary}, indent=2))

    if args.strict and summary["docs_failing"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

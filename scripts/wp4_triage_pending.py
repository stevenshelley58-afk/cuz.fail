"""WP4 blocked/pending manifest triage.

Classifies manifest rows that cannot currently be acquired by ``wp4_acquire``.
This is intentionally conservative: rows are only marked ``metadata_only`` or
``out_of_scope`` when the category/name makes that disposition mechanical.
Everything else remains/gets ``blocked`` with a one-command unblock note.

Run inside the api container:
    python /app/scripts/wp4_triage_pending.py --apply --include-blocked \
        --report /app/reports/wp4_triage_pending.json
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

DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "wp4_triage_pending.json"

PLANNING_TERMS = (
    "planning",
    "development",
    "r-codes",
    "residential design codes",
    "local planning scheme",
    "region scheme",
    "metropolitan region scheme",
    "peel region scheme",
    "greater bunbury region scheme",
    "subdivision",
    "building",
    "bushfire",
    "heritage",
)

STANDARDS_TERMS = (
    "as ",
    "as/nzs",
    "australian standard",
    "standards australia",
)

SUPERSESSION_TERMS = (
    "amendment",
    "commencement",
    "citation published",
    "repeal",
    "repealed",
    "repealing",
    "reprint of",
    "validation",
    "savings",
    "transitional",
)

FRAGMENT_PREFIXES = (
    "act and the ",
    "despite the ",
)


@dataclass(frozen=True)
class ManifestRow:
    id: str
    instrument_name: str
    category: str | None
    issuing_authority: str | None
    status: str
    canonical_url: str | None
    notes: str | None = None


@dataclass(frozen=True)
class TriageDecision:
    manifest_id: str
    instrument_name: str
    current_status: str
    recommended_status: str
    reason: str
    unblock: str | None


def norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def has_url(row: ManifestRow) -> bool:
    return bool((row.canonical_url or "").strip())


def classify_row(row: ManifestRow) -> TriageDecision:
    name = norm(row.instrument_name)
    category = norm(row.category)

    if category == "standard" or any(term in name for term in STANDARDS_TERMS):
        return TriageDecision(
            manifest_id=row.id,
            instrument_name=row.instrument_name,
            current_status=row.status,
            recommended_status="metadata_only",
            reason="Likely Standards Australia or paid/licensed standard; full text not stored.",
            unblock=None,
        )

    if category in {"act", "regulations"} and (
        any(term in name for term in SUPERSESSION_TERMS)
        or any(name.startswith(prefix) for prefix in FRAGMENT_PREFIXES)
    ):
        return TriageDecision(
            manifest_id=row.id,
            instrument_name=row.instrument_name,
            current_status=row.status,
            recommended_status="out_of_scope",
            reason="Amendment/repeal/commencement/reprint or extracted citation fragment without consolidated text.",
            unblock=None,
        )

    if category in {"act", "regulations"} and not any(term in name for term in PLANNING_TERMS):
        disposition = "out_of_scope"
        reason = "Cited WA legislation outside declared planning/building corpus scope."
        return TriageDecision(
            manifest_id=row.id,
            instrument_name=row.instrument_name,
            current_status=row.status,
            recommended_status=disposition,
            reason=reason,
            unblock=None,
        )

    if has_url(row):
        return TriageDecision(
            manifest_id=row.id,
            instrument_name=row.instrument_name,
            current_status=row.status,
            recommended_status="pending",
            reason="Has canonical_url; re-run WP4 acquisition.",
            unblock="python scripts/wp4_acquire.py --limit 20",
        )

    return TriageDecision(
        manifest_id=row.id,
        instrument_name=row.instrument_name,
        current_status=row.status,
        recommended_status="blocked",
        reason="No resolvable canonical_url for an in-scope or ambiguous planning instrument.",
        unblock=(
            "Set target_manifest.canonical_url to the official document URL, "
            "set status='pending', then run scripts/wp4_acquire.py"
        ),
    )


def database_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def load_rows(database_url_value: str, include_blocked: bool) -> list[ManifestRow]:
    statuses = ("pending", "blocked") if include_blocked else ("pending",)
    engine = create_engine(database_url_value)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id::text, instrument_name, category, issuing_authority,
                       status, canonical_url, notes
                FROM target_manifest
                WHERE status = ANY(:statuses)
                ORDER BY status, category, instrument_name
                """
            ),
            {"statuses": list(statuses)},
        ).mappings()
        return [
            ManifestRow(
                id=str(row["id"]),
                instrument_name=str(row["instrument_name"]),
                category=row["category"],
                issuing_authority=row["issuing_authority"],
                status=str(row["status"]),
                canonical_url=row["canonical_url"],
                notes=row["notes"],
            )
            for row in rows
        ]


def apply_decisions(database_url_value: str, decisions: list[TriageDecision]) -> int:
    engine = create_engine(database_url_value)
    changed = 0
    with engine.begin() as conn:
        for decision in decisions:
            if decision.recommended_status == "pending":
                continue
            result = conn.execute(
                text(
                    """
                    UPDATE target_manifest
                    SET status = :status,
                        notes = :notes,
                        metadata_json = COALESCE(metadata_json, '{}'::jsonb)
                            || CAST(:metadata AS jsonb),
                        last_checked_at = now(),
                        updated_at = now(),
                        claimed_by = NULL,
                        lease_expires_at = NULL
                    WHERE id = CAST(:id AS uuid)
                      AND status IN ('pending', 'blocked')
                    """
                ),
                {
                    "id": decision.manifest_id,
                    "status": decision.recommended_status,
                    "notes": (
                        f"WP4 triage: {decision.reason}"
                        + (f" UNBLOCK: {decision.unblock}" if decision.unblock else "")
                    ),
                    "metadata": json.dumps(
                        {
                            "wp4_triage": True,
                            "reason": decision.reason,
                            "unblock": decision.unblock,
                        }
                    ),
                },
            )
            changed += result.rowcount or 0
    return changed


def report_for(decisions: list[TriageDecision], *, mode: str, rows_scanned: int, changed: int) -> dict[str, Any]:
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
    parser.add_argument("--include-blocked", action="store_true")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    rows = load_rows(database_url(), include_blocked=args.include_blocked)
    decisions = [classify_row(row) for row in rows]
    changed = apply_decisions(database_url(), decisions) if args.apply else 0
    report = report_for(
        decisions,
        mode="apply" if args.apply else "dry_run",
        rows_scanned=len(rows),
        changed=changed,
    )
    output = json.dumps(report, indent=2, default=str)
    print(output)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

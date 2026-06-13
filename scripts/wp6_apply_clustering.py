"""WP-D apply canonical rule-key map.

Dry-run is the default. With ``--apply``, updates
``rule_candidates.canonical_rule_key`` and ``rules.canonical_rule_key`` from
the CSV emitted by ``wp6_cluster_keys.py``. Updates are idempotent and only
touch rows whose stored canonical key differs from the map.

Run inside the api container:
    python /app/scripts/wp6_apply_clustering.py --apply --report /app/reports/key_clustering_apply.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402


DEFAULT_MAP_INPUT = Path(__file__).resolve().parent.parent / "data" / "extraction" / "key_canonical_map.csv"
DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "key_clustering_apply.json"


@dataclass(frozen=True)
class KeyMapping:
    rule_key: str
    canonical_rule_key: str


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def load_map(path: Path) -> list[KeyMapping]:
    mappings: list[KeyMapping] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"rule_key", "canonical_rule_key"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"map CSV missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            rule_key = (row.get("rule_key") or "").strip()
            canonical_rule_key = (row.get("canonical_rule_key") or "").strip()
            if not rule_key or not canonical_rule_key:
                continue
            if rule_key in seen:
                raise ValueError(f"duplicate rule_key in map CSV: {rule_key}")
            seen.add(rule_key)
            mappings.append(KeyMapping(rule_key=rule_key, canonical_rule_key=canonical_rule_key[:160]))
    return mappings


def count_candidate_pending(conn: Connection, mapping: KeyMapping) -> int:
    row = conn.execute(
        text(
            """
            SELECT count(*)
            FROM rule_candidates
            WHERE rule_key = :rule_key
              AND canonical_rule_key IS DISTINCT FROM :canonical_rule_key
            """
        ),
        {"rule_key": mapping.rule_key, "canonical_rule_key": mapping.canonical_rule_key},
    ).first()
    return int(row[0]) if row else 0


def count_rule_pending(conn: Connection, mapping: KeyMapping) -> int:
    row = conn.execute(
        text(
            """
            SELECT count(*)
            FROM rules
            WHERE COALESCE(value_json->>'base_rule_key', split_part(rule_key, '.', 1)) = :rule_key
              AND canonical_rule_key IS DISTINCT FROM :canonical_rule_key
            """
        ),
        {"rule_key": mapping.rule_key, "canonical_rule_key": mapping.canonical_rule_key},
    ).first()
    return int(row[0]) if row else 0


def apply_candidate_mapping(conn: Connection, mapping: KeyMapping) -> int:
    result = conn.execute(
        text(
            """
            UPDATE rule_candidates
            SET canonical_rule_key = :canonical_rule_key
            WHERE rule_key = :rule_key
              AND canonical_rule_key IS DISTINCT FROM :canonical_rule_key
            """
        ),
        {"rule_key": mapping.rule_key, "canonical_rule_key": mapping.canonical_rule_key},
    )
    return int(result.rowcount or 0)


def apply_rule_mapping(conn: Connection, mapping: KeyMapping) -> int:
    result = conn.execute(
        text(
            """
            UPDATE rules
            SET canonical_rule_key = :canonical_rule_key
            WHERE COALESCE(value_json->>'base_rule_key', split_part(rule_key, '.', 1)) = :rule_key
              AND canonical_rule_key IS DISTINCT FROM :canonical_rule_key
            """
        ),
        {"rule_key": mapping.rule_key, "canonical_rule_key": mapping.canonical_rule_key},
    )
    return int(result.rowcount or 0)


def apply_or_report(conn: Connection, mappings: list[KeyMapping], apply: bool) -> dict[str, int]:
    summary = {
        "map_rows": len(mappings),
        "rule_candidates_matched_for_update": 0,
        "rules_matched_for_update": 0,
    }
    for mapping in mappings:
        if apply:
            summary["rule_candidates_matched_for_update"] += apply_candidate_mapping(conn, mapping)
            summary["rules_matched_for_update"] += apply_rule_mapping(conn, mapping)
        else:
            summary["rule_candidates_matched_for_update"] += count_candidate_pending(conn, mapping)
            summary["rules_matched_for_update"] += count_rule_pending(conn, mapping)
    return summary


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-input", default=str(DEFAULT_MAP_INPUT))
    parser.add_argument("--apply", action="store_true", help="write canonical keys to the database")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    mappings = load_map(Path(args.map_input))
    engine = create_engine(database_url())
    with engine.begin() as conn:
        summary = apply_or_report(conn, mappings, apply=args.apply)

    report = {
        "wp": "WP-D",
        "apply": args.apply,
        "map_input": str(Path(args.map_input)),
        "summary": summary,
        "notes": [
            "Dry-run only; no database rows changed."
            if not args.apply
            else "Database rows were updated only where canonical_rule_key differed.",
        ],
    }
    write_report(Path(args.report), report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

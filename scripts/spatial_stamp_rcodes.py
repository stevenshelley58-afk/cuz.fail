"""WP-G conservative R-code stamping for zone planning features.

Dry-run by default:
    python scripts/spatial_stamp_rcodes.py

Apply metadata_json.r_code and metadata_json.density_code updates:
    python scripts/spatial_stamp_rcodes.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


R_CODE_RE = re.compile(
    r"(?<![A-Z0-9])("
    r"R\s*-?\s*AC\s*-?\s*\d{0,2}|"
    r"RAC\s*-?\s*\d{0,2}|"
    r"R\s*\d{1,3}|"
    r"RR"
    r")(?![A-Z0-9])",
    re.IGNORECASE,
)

TRUSTED_NUMERIC_KEYS = {
    "rcode_no",
    "r_code_no",
    "r-code_no",
    "rcode",
    "r_code",
    "density_code",
    "residential_density_code",
}

TEXT_KEY_HINTS = ("code", "label", "name", "zone", "density", "rcode", "r_code", "description", "desc")
MAX_SAMPLE_COUNT = 25


@dataclass(frozen=True)
class RCodeStamp:
    r_code: str
    density_code: str
    source_field: str
    source_value: str


def normalize_database_url(database_url: str) -> str:
    return (
        database_url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )


def normalize_r_code(raw: str) -> str | None:
    token = re.sub(r"\s+", "", raw.strip().upper())
    token = token.replace("_", "-")

    if token == "RR":
        return "RR"

    rac = re.fullmatch(r"R-?AC-?(\d{0,2})", token)
    if rac:
        suffix = rac.group(1)
        return f"R-AC{suffix}" if suffix else "R-AC"

    residential = re.fullmatch(r"R(\d{1,3})", token)
    if residential:
        number = int(residential.group(1))
        if number > 0:
            return f"R{number}"

    return None


def stamp_from_value(field: str, value: Any) -> RCodeStamp | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    key = field.rsplit(".", 1)[-1].casefold()
    if key in TRUSTED_NUMERIC_KEYS and re.fullmatch(r"\d{1,3}", text):
        normalized = normalize_r_code(f"R{text}")
        if normalized is not None:
            return RCodeStamp(normalized, normalized, field, text)

    matches = {
        normalized
        for match in R_CODE_RE.finditer(text)
        if (normalized := normalize_r_code(match.group(1))) is not None
    }
    if len(matches) != 1:
        return None

    normalized = next(iter(matches))
    return RCodeStamp(normalized, normalized, field, text)


def candidate_fields(
    code: Any = None,
    label: Any = None,
    metadata: dict[str, Any] | None = None,
) -> list[tuple[str, Any]]:
    fields: list[tuple[str, Any]] = [("code", code), ("label", label)]
    if not isinstance(metadata, dict):
        return fields

    for key, value in sorted(metadata.items()):
        key_text = str(key)
        lowered = key_text.casefold()
        if key_text in {"r_code", "density_code"}:
            continue
        if any(hint in lowered for hint in TEXT_KEY_HINTS):
            fields.append((f"metadata_json.{key_text}", value))
    return fields


def parse_r_code(
    code: Any = None,
    label: Any = None,
    metadata: dict[str, Any] | None = None,
) -> RCodeStamp | None:
    stamps: list[RCodeStamp] = []
    seen_codes: set[str] = set()
    for field, value in candidate_fields(code=code, label=label, metadata=metadata):
        stamp = stamp_from_value(field, value)
        if stamp is None or stamp.r_code in seen_codes:
            continue
        stamps.append(stamp)
        seen_codes.add(stamp.r_code)

    if len(stamps) != 1:
        return None
    return stamps[0]


def needs_update(metadata: dict[str, Any], stamp: RCodeStamp) -> bool:
    return metadata.get("r_code") != stamp.r_code or metadata.get("density_code") != stamp.density_code


def sample_row(row: dict[str, Any], stamp: RCodeStamp | None = None) -> dict[str, Any]:
    sample = {
        "id": str(row["id"]),
        "code": row.get("code"),
        "label": row.get("label"),
    }
    if stamp is not None:
        sample.update(
            {
                "r_code": stamp.r_code,
                "density_code": stamp.density_code,
                "source_field": stamp.source_field,
                "source_value": stamp.source_value,
            }
        )
    return sample


def load_zone_rows(conn: psycopg.Connection[Any], limit: int | None) -> list[dict[str, Any]]:
    sql = """
        SELECT id::text AS id, code, label, metadata_json
        FROM planning_features
        WHERE layer_type = 'zone'
        ORDER BY id
    """
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT %s"
        params = (limit,)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def build_report(
    rows: list[dict[str, Any]],
    apply: bool,
    conn: psycopg.Connection[Any] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": "apply" if apply else "dry_run",
        "considered": 0,
        "matched": 0,
        "updated": 0,
        "would_update": 0,
        "unchanged": 0,
        "unmatched": 0,
        "matched_samples": [],
        "unmatched_samples": [],
    }

    for row in rows:
        report["considered"] += 1
        metadata = row.get("metadata_json") if isinstance(row.get("metadata_json"), dict) else {}
        stamp = parse_r_code(row.get("code"), row.get("label"), metadata)
        if stamp is None:
            report["unmatched"] += 1
            if len(report["unmatched_samples"]) < MAX_SAMPLE_COUNT:
                report["unmatched_samples"].append(sample_row(row))
            continue

        report["matched"] += 1
        if len(report["matched_samples"]) < MAX_SAMPLE_COUNT:
            report["matched_samples"].append(sample_row(row, stamp))

        if not needs_update(metadata, stamp):
            report["unchanged"] += 1
            continue

        if apply:
            if conn is None:
                raise RuntimeError("conn is required when apply=True")
            updated_metadata = {**metadata, "r_code": stamp.r_code, "density_code": stamp.density_code}
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE planning_features
                    SET metadata_json = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (Jsonb(updated_metadata), row["id"]),
                )
            report["updated"] += 1
        else:
            report["would_update"] += 1

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write metadata_json stamps")
    parser.add_argument("--limit", type=int, default=None, help="limit scanned zone rows")
    parser.add_argument("--report", default="", help="optional JSON report output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(normalize_database_url(database_url), row_factory=dict_row) as conn:
        rows = load_zone_rows(conn, args.limit)
        report = build_report(rows, apply=args.apply, conn=conn if args.apply else None)
        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    output = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""WP-D deterministic rule-key clustering scaffold.

Reads distinct ``rule_candidates.rule_key`` values, groups lightweight spelling
variants, and writes a JSON report plus a CSV canonical-key map. Heavy
clustering packages are intentionally optional; this first pass always has a
deterministic fallback and does not require new dependencies.

Run inside the api container:
    python /app/scripts/wp6_cluster_keys.py --report /app/reports/key_clusters.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402


DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "key_clusters.json"
DEFAULT_MAP_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "extraction" / "key_canonical_map.csv"

TOKEN_ALIASES = {
    "pct": "percent",
    "percentage": "percent",
    # NB: do NOT alias bare "per" / "cent" to "percent" — in planning rule_keys
    # "per" almost always means "per dwelling / per storey" (e.g.
    # parking_bays_per_dwelling), not a percentage.  Aliasing it corrupts those
    # canonical keys.  Only explicit pct/percentage map to percent.
    "metre": "m",
    "metres": "m",
    "meter": "m",
    "meters": "m",
    "maximum": "max",
    "minimum": "min",
    "setbacks": "setback",
    "requirements": "requirement",
}
DROP_TOKENS = {"rule", "rules", "req"}


@dataclass(frozen=True)
class KeyCluster:
    cluster_id: str
    normalized_key: str
    canonical_rule_key: str
    rule_keys: tuple[str, ...]
    total_candidates: int


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def optional_cluster_backend() -> dict[str, bool]:
    availability: dict[str, bool] = {}
    for module_name in ("sentence_transformers", "hdbscan"):
        try:
            __import__(module_name)
        except ImportError:
            availability[module_name] = False
        else:
            availability[module_name] = True
    return availability


def normalize_rule_key(value: str | None) -> str:
    raw = (value or "").casefold().strip()
    raw = raw.replace("&", " and ")
    tokens = re.findall(r"[a-z0-9]+", raw)
    normalized: list[str] = []
    for token in tokens:
        token = TOKEN_ALIASES.get(token, token)
        if token in DROP_TOKENS:
            continue
        if token.endswith("s") and len(token) > 4 and not re.fullmatch(r"r\d+s?", token):
            token = token[:-1]
        if normalized and normalized[-1] == token:
            continue
        normalized.append(token)
    return "_".join(normalized)


def canonical_from_normalized(normalized_key: str) -> str:
    return normalized_key[:160]


def cluster_rule_keys(rows: list[dict[str, Any]]) -> list[KeyCluster]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        normalized_key = normalize_rule_key(str(row["rule_key"]))
        if normalized_key:
            grouped[normalized_key].append(row)

    clusters: list[KeyCluster] = []
    for idx, normalized_key in enumerate(sorted(grouped), start=1):
        members = sorted(grouped[normalized_key], key=lambda row: str(row["rule_key"]).casefold())
        clusters.append(
            KeyCluster(
                cluster_id=f"key-{idx:05d}",
                normalized_key=normalized_key,
                canonical_rule_key=canonical_from_normalized(normalized_key),
                rule_keys=tuple(str(row["rule_key"]) for row in members),
                total_candidates=sum(int(row.get("candidate_count") or 0) for row in members),
            )
        )
    return clusters


def load_rule_keys(conn: Connection) -> list[dict[str, Any]]:
    result = conn.execute(
        text(
            """
            SELECT rule_key, count(*) AS candidate_count
            FROM rule_candidates
            WHERE rule_key IS NOT NULL AND btrim(rule_key) <> ''
            GROUP BY rule_key
            ORDER BY rule_key
            """
        )
    )
    return [dict(row._mapping) for row in result]


def write_report(path: Path, clusters: list[KeyCluster], backend: dict[str, bool]) -> dict[str, Any]:
    report = {
        "wp": "WP-D",
        "mode": "deterministic_rule_key_scaffold",
        "optional_backends_available": backend,
        "summary": {
            "clusters": len(clusters),
            "rule_keys": sum(len(cluster.rule_keys) for cluster in clusters),
            "variant_clusters": sum(1 for cluster in clusters if len(cluster.rule_keys) > 1),
            "candidate_rows": sum(cluster.total_candidates for cluster in clusters),
        },
        "clusters": [
            {
                "cluster_id": cluster.cluster_id,
                "normalized_key": cluster.normalized_key,
                "canonical_rule_key": cluster.canonical_rule_key,
                "rule_keys": list(cluster.rule_keys),
                "total_candidates": cluster.total_candidates,
            }
            for cluster in clusters
        ],
        "notes": [
            "No ML clustering was required or applied in this scaffold pass.",
            "canonical_rule_key values are deterministic normalizations of rule_key variants.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def write_map(path: Path, clusters: list[KeyCluster]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rule_key",
                "canonical_rule_key",
                "normalized_key",
                "cluster_id",
                "cluster_size",
            ],
        )
        writer.writeheader()
        rows = 0
        for cluster in clusters:
            for rule_key in cluster.rule_keys:
                writer.writerow(
                    {
                        "rule_key": rule_key,
                        "canonical_rule_key": cluster.canonical_rule_key,
                        "normalized_key": cluster.normalized_key,
                        "cluster_id": cluster.cluster_id,
                        "cluster_size": len(cluster.rule_keys),
                    }
                )
                rows += 1
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--map-output", default=str(DEFAULT_MAP_OUTPUT))
    args = parser.parse_args()

    engine = create_engine(database_url())
    with engine.begin() as conn:
        rows = load_rule_keys(conn)

    clusters = cluster_rule_keys(rows)
    backend = optional_cluster_backend()
    report = write_report(Path(args.report), clusters, backend)
    map_rows = write_map(Path(args.map_output), clusters)
    report["map_output"] = str(Path(args.map_output))
    report["summary"]["map_rows"] = map_rows
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

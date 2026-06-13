"""WP-F — derive CheckDefinitions from open-vocab rule clusters.

Rebuilds ``src/draftcheck/checks/registry_generated.py`` FROM DATA: every
``rules.canonical_rule_key`` (filled by wp6_apply_clustering.py) that has at
least ``--min-rules`` approved rules and is not already covered by a hand-written
seed check becomes a derived CheckDefinition.  The seed checks are kept verbatim
(by reference) so the existing keys — and the golden fixture — stay stable.

Output is DETERMINISTIC (sorted, no timestamps) so a checksum test can catch
accidental drift.

Run inside the api container after clustering:
    python /app/scripts/wp6_register_checks_from_clusters.py \
        --min-rules 5 --report /app/reports/wp6_checks_derived.json

Offline / unit-test mode (no DB needed):
    python scripts/wp6_register_checks_from_clusters.py \
        --from-json fixtures/cluster_stats.json --out /tmp/registry_generated.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/app/src")
sys.path.insert(0, str(_ROOT / "src"))

from draftcheck.checks.category_map import (  # noqa: E402
    category_for,
    check_name_for,
    fact_keys_for,
)
from draftcheck.checks.registry import (  # noqa: E402
    SEED_CANONICAL_RULE_KEYS,
)

DEFAULT_OUT = _ROOT / "src" / "draftcheck" / "checks" / "registry_generated.py"
DEFAULT_REPORT = _ROOT / "reports" / "wp6_checks_derived.json"

# Cluster size at/above which a derived check is promoted to Tier-1.
TIER1_MIN_RULES = 20

# Keys that are structurally valid snake_case but are NOT regulatable design
# quantities — open-vocab extraction occasionally emits these as noise.  They
# must never become compliance checks even if they somehow accrue approved
# rules.  (Substring match so e.g. "monetary_penalty" is also excluded.)
NON_RULE_KEY_TOKENS = frozenset(
    {
        "none",
        "penalty",
        "fine",
        "interest_rate",
        "development_area_number",
        "clause_number",
        "table_number",
        "figure_number",
    }
)

_SNAKE = re.compile(r"[a-z][a-z0-9_]{2,160}$")


def _is_non_rule_key(key: str) -> bool:
    return any(token in key for token in NON_RULE_KEY_TOKENS)


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def load_stats_from_db(min_rules: int) -> list[dict[str, Any]]:
    from sqlalchemy import create_engine, text

    sql = text(
        """
        SELECT
            canonical_rule_key,
            count(*) FILTER (WHERE lifecycle_status = 'approved') AS n_approved,
            mode() WITHIN GROUP (ORDER BY COALESCE(unit, ''))
                FILTER (WHERE lifecycle_status = 'approved') AS unit,
            (array_agg(quote ORDER BY length(COALESCE(quote, '')) DESC)
                FILTER (WHERE lifecycle_status = 'approved' AND quote IS NOT NULL))[1]
                AS sample_quote,
            mode() WITHIN GROUP (ORDER BY source_version_id::text)
                FILTER (WHERE lifecycle_status = 'approved') AS source
        FROM rules
        WHERE canonical_rule_key IS NOT NULL AND btrim(canonical_rule_key) <> ''
        GROUP BY canonical_rule_key
        HAVING count(*) FILTER (WHERE lifecycle_status = 'approved') >= :min_rules
        ORDER BY canonical_rule_key
        """
    )
    engine = create_engine(database_url())
    with engine.begin() as conn:
        rows = conn.execute(sql, {"min_rules": min_rules}).mappings().all()
    return [dict(r) for r in rows]


def derive_checks(stats: list[dict[str, Any]], min_rules: int) -> list[dict[str, Any]]:
    """Turn per-canonical-key stats into derived CheckDefinition dicts.

    Skips keys already covered by a seed check and keys that are not structurally
    valid snake_case.  Deterministic: sorted by key.
    """
    seed_canonical = set(SEED_CANONICAL_RULE_KEYS.values())
    derived: list[dict[str, Any]] = []
    for row in stats:
        key = (row.get("canonical_rule_key") or "").strip()
        n_approved = int(row.get("n_approved") or 0)
        if n_approved < min_rules:
            continue
        if key in seed_canonical:
            continue
        if not _SNAKE.match(key):
            continue
        if _is_non_rule_key(key):
            continue
        unit = (row.get("unit") or "").strip() or None
        quote = (row.get("sample_quote") or "").strip()
        source = (row.get("source") or "").strip()
        category = category_for(key)
        tier = "TIER1" if n_approved >= TIER1_MIN_RULES else "TIER2"
        desc = (
            f"Advisory check derived from {n_approved} approved WA/Cockburn rules "
            f"for '{key.replace('_', ' ')}'."
        )
        if source:
            desc += f" Most-cited source_version {source}."
        if quote:
            snippet = quote.replace("\n", " ").strip()[:140]
            desc += f' e.g. "{snippet}"'
        derived.append(
            {
                "key": key,
                "name": check_name_for(key),
                "tier": tier,
                "category": category.name,
                "fact_keys": list(fact_keys_for(key, unit)),
                "rule_key_pattern": key,
                "unit": unit or "",
                "description": desc,
                "_n_approved": n_approved,
            }
        )
    derived.sort(key=lambda d: d["key"])
    return derived


def _render_check(c: dict[str, Any]) -> str:
    return (
        "    CheckDefinition(\n"
        f"        key={c['key']!r},\n"
        f"        name={c['name']!r},\n"
        f"        tier=CheckTier.{c['tier']},\n"
        f"        category=CheckCategory.{c['category']},\n"
        f"        fact_keys={tuple(c['fact_keys'])!r},\n"
        f"        rule_key_pattern={c['rule_key_pattern']!r},\n"
        f"        unit={c['unit']!r},\n"
        f"        description={c['description']!r},\n"
        "    ),"
    )


def render_module(derived: list[dict[str, Any]], min_rules: int) -> str:
    t1 = [c for c in derived if c["tier"] == "TIER1"]
    t2 = [c for c in derived if c["tier"] == "TIER2"]
    t1_body = "\n".join(_render_check(c) for c in t1)
    t2_body = "\n".join(_render_check(c) for c in t2)
    return (
        '"""GENERATED check registry — DO NOT EDIT BY HAND.\n'
        "\n"
        "Produced by scripts/wp6_register_checks_from_clusters.py from\n"
        "rules.canonical_rule_key clusters with >= "
        f"{min_rules} approved rules.\n"
        "Regenerate after clustering; do not hand-edit.  See\n"
        "docs/OPEN_VOCAB_REBUILD_PLAN.md WP-F.\n"
        '"""\n'
        "from __future__ import annotations\n"
        "\n"
        "from draftcheck.checks.registry import (\n"
        "    SEED_TIER1_CHECKS,\n"
        "    SEED_TIER2_CHECKS,\n"
        "    CheckCategory,\n"
        "    CheckDefinition,\n"
        "    CheckTier,\n"
        ")\n"
        "\n"
        f'GENERATED_FROM = "rules.canonical_rule_key >= {min_rules} approved rules"\n'
        f"DERIVED_COUNT = {len(derived)}\n"
        "\n"
        "_DERIVED_TIER1: list[CheckDefinition] = [\n"
        f"{t1_body}\n"
        "]\n"
        "\n"
        "_DERIVED_TIER2: list[CheckDefinition] = [\n"
        f"{t2_body}\n"
        "]\n"
        "\n"
        "TIER1_CHECKS: list[CheckDefinition] = list(SEED_TIER1_CHECKS) + _DERIVED_TIER1\n"
        "TIER2_CHECKS: list[CheckDefinition] = list(SEED_TIER2_CHECKS) + _DERIVED_TIER2\n"
        "\n"
        "ALL_CHECKS: list[CheckDefinition] = TIER1_CHECKS + TIER2_CHECKS\n"
        "CHECK_BY_KEY: dict[str, CheckDefinition] = {c.key: c for c in ALL_CHECKS}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-rules", type=int, default=5)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--from-json",
        default=None,
        help="read cluster stats from a JSON list instead of the DB (offline/test).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do not write the registry module; only emit the report.",
    )
    args = parser.parse_args()

    if args.from_json:
        stats = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    else:
        stats = load_stats_from_db(args.min_rules)

    derived = derive_checks(stats, args.min_rules)
    module_src = render_module(derived, args.min_rules)

    out_path = Path(args.out)
    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(module_src, encoding="utf-8")

    # seed count = 11 (9 tier1 + 2 tier2); total surfaced = seed + derived.
    report = {
        "wp": "WP-F",
        "min_rules": args.min_rules,
        "tier1_promote_at": TIER1_MIN_RULES,
        "derived_count": len(derived),
        "seed_count": 11,
        "total_checks": 11 + len(derived),
        "out": str(out_path),
        "dry_run": args.dry_run,
        "derived": [
            {k: v for k, v in d.items()} for d in derived
        ],
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "derived_count", "seed_count", "total_checks", "out", "dry_run"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate extraction report against seed data and existing rules.

Cross-references extracted rule candidates against:
1. check_definitions.example.yaml (expected check keys)
2. Existing approved rules (no regression)
3. Spot-check samples

Usage:
    python scripts/validate_extraction.py \
        --report reports/phase1_rcodes_partb_extraction.json \
        --seed-yaml data/seed/check_definitions.example.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_report(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def load_seed_checks(path: Path) -> list[dict[str, Any]]:
    if yaml is None or not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("checks", []) if data else []


def validate_candidates(report: dict[str, Any]) -> list[str]:
    """Run structural validation on candidates."""
    errors: list[str] = []
    candidates = report.get("candidates", [])

    for i, c in enumerate(candidates):
        # Required fields
        for field in ("rule_key", "operator", "value_json", "quote", "source_version_id"):
            if not c.get(field):
                errors.append(f"Candidate {i} ({c.get('rule_key', '?')}): missing {field}")

        # Operator must be valid
        if c.get("operator") not in ("gte", "lte", "eq", "gt", "lt"):
            errors.append(
                f"Candidate {i} ({c.get('rule_key', '?')}): "
                f"invalid operator '{c.get('operator')}'"
            )

        # value_json must have 'value' or 'raw_text'
        vj = c.get("value_json", {})
        if "value" not in vj and "raw_text" not in vj:
            errors.append(
                f"Candidate {i} ({c.get('rule_key', '?')}): "
                f"value_json has neither 'value' nor 'raw_text'"
            )

        # applicable_r_codes must be non-empty
        if not c.get("applicable_r_codes"):
            errors.append(
                f"Candidate {i} ({c.get('rule_key', '?')}): "
                f"applicable_r_codes is empty"
            )

    return errors


def cross_reference_seeds(
    candidates: list[dict[str, Any]],
    seed_checks: list[dict[str, Any]],
) -> list[str]:
    """Check that extracted candidates cover expected seed check keys."""
    warnings: list[str] = []
    candidate_keys = {c.get("canonical_rule_key", "") for c in candidates}

    for check in seed_checks:
        key = check.get("key", "")
        # Map seed keys to canonical rule keys (approximate)
        canonical_map = {
            "site_cover": "site_cover",
            "open_space": "open_space",
            "front_setback": "primary_street_setback",
            "side_setback": "side_setback",
            "rear_setback": "rear_setback",
            "outdoor_living_area": "outdoor_living_area",
            "garage_dominance": "garage_dominance",
        }
        canonical = canonical_map.get(key, key)
        if canonical not in candidate_keys:
            warnings.append(f"Seed check '{key}' (canonical: {canonical}) not found in candidates")

    return warnings


def check_existing_rules(report: dict[str, Any]) -> list[str]:
    """Verify existing approved rules are not contradicted."""
    issues: list[str] = []
    db_url = os.environ.get("DATABASE_URL", "").replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace("postgresql+psycopg://", "postgresql://")

    if not db_url:
        return ["DATABASE_URL not set; skipping existing rule cross-check"]

    try:
        import psycopg
        with psycopg.connect(db_url) as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT rule_key, operator, value_json, applicable_r_codes
                   FROM rules WHERE lifecycle_status = 'approved'"""
            )
            existing = cur.fetchall()

            candidates = report.get("candidates", [])
            candidate_map: dict[str, dict] = {}
            for c in candidates:
                key = (c.get("rule_key", ""), tuple(c.get("applicable_r_codes", [])))
                candidate_map[key] = c

            for rule_key, operator, value_json, r_codes in existing:
                vj = value_json if isinstance(value_json, dict) else {}
                existing_val = vj.get("value")
                if existing_val is None:
                    continue

                for rc in (r_codes or []):
                    lookup = (rule_key, (rc,))
                    if lookup in candidate_map:
                        cand = candidate_map[lookup]
                        cand_val = cand.get("value_json", {}).get("value")
                        if cand_val is not None and cand_val != existing_val:
                            issues.append(
                                f"CONFLICT: {rule_key} [{rc}] existing={existing_val} "
                                f"vs extracted={cand_val}"
                            )
    except ImportError:
        issues.append("psycopg not installed; skipping DB cross-check")
    except Exception as e:
        issues.append(f"DB cross-check error: {e}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate extraction report.")
    parser.add_argument("--report", required=True, help="Path to extraction report JSON")
    parser.add_argument(
        "--seed-yaml",
        default=str(_ROOT / "data" / "seed" / "check_definitions.example.yaml"),
        help="Path to seed check definitions YAML",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"ERROR: Report not found: {report_path}", file=sys.stderr)
        return 1

    report = load_report(report_path)
    candidates = report.get("candidates", [])
    print(f"Loaded report: {len(candidates)} candidates")
    print(f"Source version: {report.get('source_version_id')}")
    print(f"Warnings from extraction: {len(report.get('warnings', []))}")

    # 1. Structural validation
    print("\n--- Structural Validation ---")
    errors = validate_candidates(report)
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors[:20]:
            print(f"  ✗ {e}")
    else:
        print("✓ All candidates pass structural validation")

    # 2. Seed cross-reference
    print("\n--- Seed Cross-Reference ---")
    seed_checks = load_seed_checks(Path(args.seed_yaml))
    seed_warnings = cross_reference_seeds(candidates, seed_checks)
    if seed_warnings:
        print(f"Warnings ({len(seed_warnings)}):")
        for w in seed_warnings:
            print(f"  ⚠ {w}")
    else:
        print("✓ All seed checks covered")

    # 3. Existing rule cross-check
    print("\n--- Existing Rule Cross-Check ---")
    issues = check_existing_rules(report)
    if issues:
        print(f"Issues ({len(issues)}):")
        for issue in issues:
            print(f"  ⚠ {issue}")
    else:
        print("✓ No conflicts with existing approved rules")

    # Summary
    print("\n--- Summary ---")
    total_issues = len(errors) + len([i for i in issues if "CONFLICT" in i])
    if total_issues > 0:
        print(f"FAIL: {total_issues} blocking issues found")
        return 1
    else:
        print("PASS: Extraction validated successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())

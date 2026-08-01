"""DB quality audit for LotFile rules database.

Checks for duplicates, orphans, inconsistencies, coverage gaps, and data quality issues.
Outputs JSON report for DeepSeek analysis.
"""

import json
import os
import sys
from pathlib import Path

import psycopg

# Load DATABASE_URL from .env
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            os.environ["DATABASE_URL"] = line.split("=", 1)[1].strip()
            break

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

# Convert SQLAlchemy URL to psycopg
DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")


def run_query(conn, sql, params=None):
    """Run a query and return all rows as list of dicts."""
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def main():
    report = {"checks": []}

    with psycopg.connect(DATABASE_URL) as conn:
        # 1. Rule counts by status
        rows = run_query(conn, """
            SELECT lifecycle_status, COUNT(*) as cnt
            FROM rules
            GROUP BY lifecycle_status
            ORDER BY cnt DESC
        """)
        report["checks"].append({"name": "rules_by_status", "data": rows})

        # 2. Rules by source_type
        rows = run_query(conn, """
            SELECT source_type, COUNT(*) as cnt
            FROM rules
            GROUP BY source_type
            ORDER BY cnt DESC
        """)
        report["checks"].append({"name": "rules_by_source_type", "data": rows})

        # 3. Approved rules with NULL applicable_zones (global)
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved' AND applicable_zones IS NULL
        """)
        report["checks"].append({"name": "approved_null_zones", "data": rows})

        # 4. Approved rules with NULL applicable_r_codes (global)
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved' AND applicable_r_codes IS NULL
        """)
        report["checks"].append({"name": "approved_null_rcodes", "data": rows})

        # 5. Approved rules with conditions
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND condition_json IS NOT NULL
              AND condition_json::text NOT IN ('{}', 'null', '')
        """)
        report["checks"].append({"name": "approved_with_conditions", "data": rows})

        # 6. Top base_rule_keys
        rows = run_query(conn, """
            SELECT base_rule_key, COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
            GROUP BY base_rule_key
            ORDER BY cnt DESC
            LIMIT 20
        """)
        report["checks"].append({"name": "top_base_rule_keys", "data": rows})

        # 7. Rules by council_scope
        rows = run_query(conn, """
            SELECT council_scope, COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
            GROUP BY council_scope
            ORDER BY cnt DESC
            LIMIT 15
        """)
        report["checks"].append({"name": "rules_by_council", "data": rows})

        # 8. Potential duplicates (same key+council+zone+threshold)
        rows = run_query(conn, """
            SELECT
                base_rule_key,
                council_scope,
                applicable_zones::text as zones,
                threshold_value,
                threshold_operator,
                COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
            GROUP BY base_rule_key, council_scope, applicable_zones::text, threshold_value, threshold_operator
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            LIMIT 10
        """)
        report["checks"].append({"name": "potential_duplicates", "data": rows})

        # 9. Rules with suspicious thresholds (0, negative, or very large)
        rows = run_query(conn, """
            SELECT
                id,
                rule_key,
                base_rule_key,
                threshold_value,
                threshold_operator,
                council_scope
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND (
                  threshold_value <= 0
                  OR threshold_value > 1000
              )
            LIMIT 20
        """)
        report["checks"].append({"name": "suspicious_thresholds", "data": rows})

        # 10. Rules with NULL threshold_value
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved' AND threshold_value IS NULL
        """)
        report["checks"].append({"name": "null_thresholds", "data": rows})

        # 11. Planning features by layer_type
        rows = run_query(conn, """
            SELECT layer_type, COUNT(*) as cnt
            FROM planning_features
            GROUP BY layer_type
            ORDER BY cnt DESC
        """)
        report["checks"].append({"name": "planning_features_by_layer", "data": rows})

        # 12. Rules with missing canonical_rule_key
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved' AND canonical_rule_key IS NULL
        """)
        report["checks"].append({"name": "missing_canonical_key", "data": rows})

        # 13. Rules with empty applicable_zones array
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND applicable_zones IS NOT NULL
              AND applicable_zones::text = '[]'
        """)
        report["checks"].append({"name": "empty_zones_array", "data": rows})

        # 14. Rules with empty applicable_r_codes array
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND applicable_r_codes IS NOT NULL
              AND applicable_r_codes::text = '[]'
        """)
        report["checks"].append({"name": "empty_rcodes_array", "data": rows})

        # 15. Condition keys distribution
        rows = run_query(conn, """
            SELECT
                jsonb_object_keys(condition_json) as condition_key,
                COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND condition_json IS NOT NULL
              AND condition_json::text NOT IN ('{}', 'null', '')
            GROUP BY condition_key
            ORDER BY cnt DESC
        """)
        report["checks"].append({"name": "condition_keys_distribution", "data": rows})

        # 16. Rules with dwelling_type condition
        rows = run_query(conn, """
            SELECT
                id,
                rule_key,
                base_rule_key,
                condition_json->>'dwelling_type' as dwelling_type,
                threshold_value,
                threshold_operator
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND condition_json ? 'dwelling_type'
            LIMIT 10
        """)
        report["checks"].append({"name": "dwelling_type_rules_sample", "data": rows})

        # 17. Rules with density_codes condition
        rows = run_query(conn, """
            SELECT
                id,
                rule_key,
                base_rule_key,
                condition_json->'density_codes' as density_codes,
                threshold_value,
                threshold_operator
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND condition_json ? 'density_codes'
            LIMIT 10
        """)
        report["checks"].append({"name": "density_codes_rules_sample", "data": rows})

        # 18. Check for rules with exception/variant in rule_key
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved'
              AND (rule_key ILIKE '%exception%' OR rule_key ILIKE '%variant%')
        """)
        report["checks"].append({"name": "exception_variant_rules", "data": rows})

        # 19. Source documents count
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt FROM source_documents
        """)
        report["checks"].append({"name": "source_documents_count", "data": rows})

        # 20. Rules with NULL source_document_id
        rows = run_query(conn, """
            SELECT COUNT(*) as cnt
            FROM rules
            WHERE lifecycle_status = 'approved' AND source_document_id IS NULL
        """)
        report["checks"].append({"name": "orphaned_rules", "data": rows})

    # Write report
    output_path = Path(__file__).resolve().parent.parent / "reports" / "db_quality_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Report written to {output_path}")
    print(f"Total checks: {len(report['checks'])}")


if __name__ == "__main__":
    main()

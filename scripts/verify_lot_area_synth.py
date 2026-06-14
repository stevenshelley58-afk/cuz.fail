"""Parcel-inject verification harness for the lot-AREA checks.

The real Beeliar address does not currently resolve to a parcel in prod (G-NAF
gap), so ``verify_beeliar.py`` returns all-needs_more_info.  This harness instead
INJECTS the confirmed spatial PropertyFacts a resolved parcel would synthesise
(lot area + R-code + council), then runs the compliance engine — exactly the
shapes ``draftcheck.domain.spatial.synth_facts`` writes.  It lets us prove the
WP-E operator curation + the ``site_area -> lot_area_m2`` FACT_KEY_OVERRIDE make
``site_area`` evaluate correctly: a 708 m2 lot at R20 should ``likely_pass`` a
450 m2 minimum.

Run inside the api container (matches the verify_beeliar.py invocation):
    docker exec -i draftcheck-wa-v3-api-1 python - --lot-area 708 --r-code R20 \
        < scripts/verify_lot_area_synth.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, "/app/src")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from draftcheck.checks.engine import ComplianceEngine  # noqa: E402
from draftcheck.checks.registry import ALL_CHECKS, CHECK_BY_KEY, REGISTRY_SOURCE  # noqa: E402
from draftcheck.db.models import Project, PropertyFact  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA

# Lot-area family checks we want to inspect explicitly in the report.
LOT_AREA_CHECK_KEYS = ("site_area", "min_lot_area_per_dwelling", "average_lot_size")


def _db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lot-area", type=float, default=708.0)
    ap.add_argument("--r-code", default="R20")
    ap.add_argument("--council", default="Cockburn")
    args = ap.parse_args()

    engine = create_engine(_db_url())
    project_id = str(uuid.uuid4())
    org_uuid = uuid.UUID(ORG_ID)

    # 1. throwaway project, scoped to the council so the engine's council filter
    #    behaves as it would for a real Beeliar (Cockburn) resolution.
    with Session(engine) as s:
        s.add(Project(id=uuid.UUID(project_id), org_id=org_uuid,
                      name="lot-area synth verify", status="draft",
                      council_scope=args.council))
        s.commit()

    report: dict = {
        "registry_source": REGISTRY_SOURCE,
        "registry_checks": len(ALL_CHECKS),
        "injected": {"lot_area_m2": args.lot_area, "r_code": args.r_code,
                     "council_scope": args.council},
    }
    try:
        # 2. inject the confirmed facts a resolved parcel would synthesise.
        with Session(engine) as s:
            def _fact(fact_type: str, value: dict) -> PropertyFact:
                return PropertyFact(
                    org_id=org_uuid, project_id=uuid.UUID(project_id),
                    fact_type=fact_type, value_json=value, confidence=0.9,
                    method="spatial_derived",
                    provenance_json={"method": "spatial_derived", "advisory_only": True,
                                     "harness": "verify_lot_area_synth"},
                    review_status="confirmed",
                )
            s.add_all([
                _fact("lot_area_m2", {"value": round(args.lot_area, 2), "unit": "m2"}),
                _fact("r_code", {"code": args.r_code, "label": args.r_code}),
                _fact("zone", {"code": "Residential", "name": "Residential"}),
                _fact("local_government", {"name": args.council}),
            ])
            s.commit()

        # 3. run the compliance engine.
        with Session(engine) as s:
            result = ComplianceEngine().run_check(project_id=project_id, org_id=ORG_ID, session=s)
            s.commit()
            statuses: dict[str, int] = {}
            lot_rows = []
            for item in result.results:
                statuses[item.status] = statuses.get(item.status, 0) + 1
                if item.check_key in LOT_AREA_CHECK_KEYS:
                    lot_rows.append({
                        "check_key": item.check_key,
                        "status": item.status,
                        "measured": item.measured_value,
                        "note": item.note,
                        "threshold": item.threshold_value,
                        "unit": item.threshold_unit,
                        "fact_keys": list(CHECK_BY_KEY[item.check_key].fact_keys),
                        "citation": item.citation,
                        "quote": (item.rule_quote or "")[:120],
                    })
            report["status_breakdown"] = statuses
            report["pass_or_fail"] = statuses.get("likely_pass", 0) + statuses.get("likely_fail", 0)
            report["lot_area_results"] = lot_rows
    finally:
        # 4. cleanup (cascade deletes injected facts + check rows).
        with Session(engine) as s:
            proj = s.get(Project, uuid.UUID(project_id))
            if proj is not None:
                s.delete(proj)
                s.commit()

    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""WP-I — Beeliar end-to-end verification harness.

Creates a throwaway project under the DraftCheck WA org, resolves the Beeliar
address (which synthesises confirmed spatial facts), runs the compliance engine,
and reports the real counts the canary gate pins. Cleans up the test project.

Run inside the api container:
    python /app/scripts/verify_beeliar.py --address "1 BLACK SWAN RISE BEELIAR"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from draftcheck.checks.engine import ComplianceEngine  # noqa: E402
from draftcheck.checks.registry import ALL_CHECKS, REGISTRY_SOURCE  # noqa: E402
from draftcheck.db.models import Project, PropertyFact  # noqa: E402
from draftcheck.domain.address import AddressResolutionService  # noqa: E402
from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA


def _db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default="1 BLACK SWAN RISE BEELIAR")
    args = ap.parse_args()

    engine = create_engine(_db_url())
    project_id = str(uuid.uuid4())

    # 1. create throwaway project
    with Session(engine) as s:
        s.add(Project(id=uuid.UUID(project_id), org_id=uuid.UUID(ORG_ID),
                      name="WP-I Beeliar canary", status="draft"))
        s.commit()

    report: dict = {"address": args.address, "project_id": project_id,
                    "registry_source": REGISTRY_SOURCE, "registry_checks": len(ALL_CHECKS)}
    try:
        # 2. resolve address -> synth confirmed facts
        store = PostGISSpatialDatasetStore(engine)
        svc = AddressResolutionService(store=store)
        profile = svc.resolve_address(org_id=ORG_ID, project_id=project_id, address=args.address)
        report["resolution_status"] = str(profile.resolution_status)
        report["parcel_id"] = profile.parcel_id
        report["local_government"] = profile.local_government

        # 3. inspect synth facts
        with Session(engine) as s:
            facts = (s.query(PropertyFact)
                     .filter(PropertyFact.project_id == uuid.UUID(project_id),
                             PropertyFact.review_status == "confirmed").all())
            report["synth_property_facts"] = len(facts)
            report["synth_fact_types"] = sorted({f.fact_type for f in facts})
            rcode = next((f.value_json.get("code") for f in facts
                          if f.fact_type == "r_code" and isinstance(f.value_json, dict)), None)
            report["r_code"] = rcode

        # 4. run compliance engine
        with Session(engine) as s:
            result = ComplianceEngine().run_check(project_id=project_id, org_id=ORG_ID, session=s)
            s.commit()
            statuses: dict[str, int] = {}
            results = []
            for item in result.results:
                statuses[item.status] = statuses.get(item.status, 0) + 1
                results.append({"check_key": item.check_key, "status": item.status,
                                "citation": item.citation,
                                "measured": item.measured_value, "threshold": item.threshold_value})
            report["categories_evaluated"] = len(result.results)
            report["status_breakdown"] = statuses
            report["pass_or_fail"] = statuses.get("likely_pass", 0) + statuses.get("likely_fail", 0)
            report["results"] = results
    finally:
        # 5. cleanup throwaway project (cascade deletes facts/checks)
        with Session(engine) as s:
            proj = s.get(Project, uuid.UUID(project_id))
            if proj is not None:
                s.delete(proj)
                s.commit()

    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

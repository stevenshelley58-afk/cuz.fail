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
from draftcheck.db.models import Project, PropertyFact, Rule  # noqa: E402
from draftcheck.domain.address import AddressResolutionService  # noqa: E402
from draftcheck.domain.address.postgis_store import PostGISSpatialDatasetStore  # noqa: E402

ORG_ID = "1d31c315-5087-47df-a8d4-ebfd08efad5d"  # DraftCheck WA


def _db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://")


def _run_for_project(engine, project_id: str, address: str | None, org_id: str) -> dict:
    """Resolve address (when provided) and run the engine for one project."""
    report: dict = {"address": address, "project_id": project_id}
    if address:
        store = PostGISSpatialDatasetStore(engine)
        svc = AddressResolutionService(store=store)
        profile = svc.resolve_address(org_id=org_id, project_id=project_id, address=address)
        report["resolution_status"] = str(profile.resolution_status)
        report["parcel_id"] = profile.parcel_id
        report["local_government"] = profile.local_government

    with Session(engine) as s:
        facts = (s.query(PropertyFact)
                 .filter(PropertyFact.project_id == uuid.UUID(project_id),
                         PropertyFact.review_status == "confirmed").all())
        report["synth_property_facts"] = len(facts)
        report["synth_fact_types"] = sorted({f.fact_type for f in facts})
        rcode = next((f.value_json.get("code") for f in facts
                      if f.fact_type == "r_code" and isinstance(f.value_json, dict)), None)
        report["r_code"] = rcode

    with Session(engine) as s:
        result = ComplianceEngine().run_check(project_id=project_id, org_id=org_id, session=s)
        s.commit()
        statuses: dict[str, int] = {}
        by_check_type: dict[str, int] = {}
        numeric_results = []
        advisory_samples = []
        for item in result.results:
            statuses[item.status] = statuses.get(item.status, 0) + 1
            ct = item.check_type or "numeric_threshold"
            by_check_type[ct] = by_check_type.get(ct, 0) + 1
            if item.check_type and item.check_type != "numeric_threshold":
                if len(advisory_samples) < 8:
                    advisory_samples.append({
                        "check_key": item.check_key, "check_type": item.check_type,
                        "status": item.status, "what_it_means": item.what_it_means,
                        "how_to_query": item.how_to_query, "citation": item.citation})
            else:
                numeric_results.append({"check_key": item.check_key, "status": item.status,
                                        "citation": item.citation, "measured": item.measured_value,
                                        "threshold": item.threshold_value})
        report["categories_evaluated"] = len(result.results)
        report["status_breakdown"] = statuses
        report["by_check_type"] = by_check_type
        report["numeric_checks"] = len(numeric_results)
        report["advisory_rules_surfaced"] = sum(
            v for k, v in by_check_type.items() if k != "numeric_threshold")
        report["pass_or_fail"] = statuses.get("likely_pass", 0) + statuses.get("likely_fail", 0)
        report["numeric_results"] = numeric_results
        report["advisory_samples"] = advisory_samples
        report["rule_ids"] = [str(item.rule_id) for item in result.results if item.rule_id]
        report["council_scope_source"] = None
        # Pull the council_scope_source from any persisted ResolvedRule selection trace.
        from draftcheck.db.models import ResolvedRule  # noqa: E402
        rr = (s.query(ResolvedRule)
              .filter(ResolvedRule.project_id == uuid.UUID(project_id))
              .order_by(ResolvedRule.created_at)
              .first())
        if rr and isinstance(rr.selection_trace_json, dict):
            report["council_scope_source"] = rr.selection_trace_json.get("council_scope_source")
            report["council_scope"] = rr.selection_trace_json.get("council_scope")
    return report


def _assert_no_foreign_council_rules(engine, project_id: str, allowed_scope: str | None) -> list[str]:
    """Return a list of foreign council_scope values found among surfaced rules."""
    with Session(engine) as s:
        # Re-run engine to get the latest result for this project.
        result = ComplianceEngine().run_check(project_id=project_id, org_id=ORG_ID, session=s)
        s.commit()
        rule_ids = [UUID(item.rule_id) for item in result.results if item.rule_id]
        if not rule_ids:
            return []
        scopes = (
            s.query(Rule.council_scope)
            .filter(Rule.id.in_(rule_ids), Rule.council_scope.isnot(None))
            .distinct()
            .all()
        )
        foreign = []
        for (scope,) in scopes:
            if allowed_scope is None or scope != allowed_scope:
                foreign.append(scope)
        return foreign


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", default="1 BLACK SWAN RISE BEELIAR")
    ap.add_argument("--other-council", default="City of Melville")
    args = ap.parse_args()

    engine = create_engine(_db_url())

    # ------------------------------------------------------------------
    # 1. Canary project for the primary address.
    # ------------------------------------------------------------------
    project_id = str(uuid.uuid4())
    with Session(engine) as s:
        s.add(Project(id=uuid.UUID(project_id), org_id=uuid.UUID(ORG_ID),
                      name="WP-I Beeliar canary", status="draft"))
        s.commit()

    report: dict = {"registry_source": REGISTRY_SOURCE, "registry_checks": len(ALL_CHECKS)}
    try:
        report["primary"] = _run_for_project(engine, project_id, args.address, ORG_ID)
    finally:
        with Session(engine) as s:
            proj = s.get(Project, uuid.UUID(project_id))
            if proj is not None:
                s.delete(proj)
                s.commit()

    # ------------------------------------------------------------------
    # 2. Cross-council leakage gate: a project whose scope is a different
    #    council must NOT surface Cockburn-scoped local rules.
    # ------------------------------------------------------------------
    other_project_id = str(uuid.uuid4())
    with Session(engine) as s:
        s.add(Project(
            id=uuid.UUID(other_project_id), org_id=uuid.UUID(ORG_ID),
            name="WP-0 cross-council leakage gate", status="draft",
            metadata_json={"council_scope": args.other_council},
        ))
        s.commit()
    try:
        other_report = _run_for_project(engine, other_project_id, None, ORG_ID)
        report["cross_council"] = {
            "project_council_scope": args.other_council,
            "categories_evaluated": other_report["categories_evaluated"],
            "foreign_council_scopes_found": _assert_no_foreign_council_rules(
                engine, other_project_id, args.other_council
            ),
        }
    finally:
        with Session(engine) as s:
            proj = s.get(Project, uuid.UUID(other_project_id))
            if proj is not None:
                s.delete(proj)
                s.commit()

    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

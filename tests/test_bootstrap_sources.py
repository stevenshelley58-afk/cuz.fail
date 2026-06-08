from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_compliance.resolved_rules import ResolvedRuleService
from draftcheck_compliance.service import ComplianceService
from draftcheck_core.bootstrap_sources import (
    BOOTSTRAP_BUSHFIRE_BAL_BASIC_GUIDANCE_VERSION_ID,
    BOOTSTRAP_OPEN_SPACE_RULE_ROW_ID,
    BOOTSTRAP_OUTDOOR_LIVING_RULE_ROW_ID,
    BOOTSTRAP_NATURAL_VENTILATION_GUIDANCE_VERSION_ID,
    BOOTSTRAP_SITE_COVER_CITATION_ID,
    BOOTSTRAP_SITE_COVER_CHUNK_ID,
    BOOTSTRAP_SITE_COVER_CLAUSE_ID,
    BOOTSTRAP_SITE_COVER_DISPOSITION_ID,
    BOOTSTRAP_SITE_COVER_RULE_ROW_ID,
    BOOTSTRAP_SIDE_SETBACK_GUIDANCE_VERSION_ID,
    BOOTSTRAP_SOLAR_GUIDANCE_VERSION_ID,
    BOOTSTRAP_VOL2_A4_GUIDANCE_VERSION_ID,
    BOOTSTRAP_VOL2_A5_GUIDANCE_VERSION_ID,
    ensure_demo_source_library,
)
from draftcheck_core.database import Base
from draftcheck_core.models import (
    AddressProfile,
    Clause,
    ClauseDisposition,
    ExtractedMeasurement,
    Project,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceVersion,
)
from draftcheck_core.ops import OpsDashboardService
from draftcheck_core.source_support import source_version_can_support_citable_retrieval
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import ResolvedRulesRequest


def test_demo_source_bootstrap_creates_citable_rule_backed_source():
    db = _session()
    try:
        before = RetrievalService(db).ask("Front setback rules?")
        assert before.status == "unsupported"
        assert "No accepted current source versions are available for citable retrieval." in before.missing_information

        result = ensure_demo_source_library(db)

        assert result["created"] is True
        version = db.scalar(select(SourceVersion).where(SourceVersion.id == result["source_version_id"]))
        assert version is not None
        assert source_version_can_support_citable_retrieval(db, version.id) is True

        dashboard = OpsDashboardService(db).dashboard()
        assert dashboard.sources["citable_retrieval"]["readiness_status"] == "ready"
        assert dashboard.sources["citable_retrieval"]["supported_versions"] == 7
        assert "no_citable_source_versions_available" not in dashboard.issues
        for source_version_id in [
            BOOTSTRAP_SOLAR_GUIDANCE_VERSION_ID,
            BOOTSTRAP_NATURAL_VENTILATION_GUIDANCE_VERSION_ID,
            BOOTSTRAP_BUSHFIRE_BAL_BASIC_GUIDANCE_VERSION_ID,
            BOOTSTRAP_SIDE_SETBACK_GUIDANCE_VERSION_ID,
            BOOTSTRAP_VOL2_A4_GUIDANCE_VERSION_ID,
            BOOTSTRAP_VOL2_A5_GUIDANCE_VERSION_ID,
        ]:
            assert source_version_can_support_citable_retrieval(db, source_version_id) is True

        answer = RetrievalService(db).ask("What is the front setback for an R30 single house?")
        assert answer.status == "needs_human_review"
        assert answer.citations
        assert answer.source_version_ids == [version.id]
        assert "R30 primary street setback: 4m" in answer.answer
        _assert_clear_supported_answer(answer.answer)

        site_cover = RetrievalService(db).ask("What is the site cover requirement for R30?")
        assert site_cover.status == "needs_human_review"
        assert site_cover.citations
        assert site_cover.source_version_ids == [version.id]
        assert "R30 site cover: 60%" in site_cover.answer
        _assert_clear_supported_answer(site_cover.answer)

        open_space = RetrievalService(db).ask("What is the open space requirement for an R30 single house?")
        assert open_space.status == "needs_human_review"
        assert open_space.citations
        assert open_space.source_version_ids == [version.id]
        assert "R30 open space: 45%" in open_space.answer

        outdoor_living = RetrievalService(db).ask(
            "What is the outdoor living area requirement for an R30 single house?"
        )
        assert outdoor_living.status == "needs_human_review"
        assert outdoor_living.citations
        assert outdoor_living.source_version_ids == [version.id]
        assert "R30 outdoor living area: 24m2 minimum area; 4m minimum dimension" in outdoor_living.answer

        solar = RetrievalService(db).ask("How do I demonstrate solar access?")
        assert solar.status == "needs_human_review"
        assert solar.citations
        assert solar.source_version_ids == [BOOTSTRAP_SOLAR_GUIDANCE_VERSION_ID]
        assert solar.answer.startswith("The approved guidance shows how solar access can be demonstrated")
        assert "solar access can be demonstrated" in solar.answer
        _assert_clear_supported_answer(solar.answer)

        solar_requirement = RetrievalService(db).ask("What are the solar access requirements?")
        assert solar_requirement.status == "unsupported"
        assert solar_requirement.citations == []

        natural_ventilation = RetrievalService(db).ask("How should I orient apartments for natural ventilation?")
        assert natural_ventilation.status == "needs_human_review"
        assert natural_ventilation.citations
        assert natural_ventilation.source_version_ids == [BOOTSTRAP_NATURAL_VENTILATION_GUIDANCE_VERSION_ID]
        assert natural_ventilation.answer.startswith("For natural ventilation")
        assert "45 to 90 degrees" in natural_ventilation.answer
        _assert_clear_supported_answer(natural_ventilation.answer)

        side_setback = RetrievalService(db).ask("How do I calculate average side setbacks?")
        assert side_setback.status == "needs_human_review"
        assert side_setback.citations
        assert side_setback.citations[0].source_version_id == BOOTSTRAP_SIDE_SETBACK_GUIDANCE_VERSION_ID
        assert side_setback.answer.startswith("The approved guidance provides a method")
        assert "average side setback" in side_setback.answer
        _assert_clear_supported_answer(side_setback.answer)

        bushfire_bal_report = RetrievalService(db).ask("bushfire prone areas BAL report")
        assert bushfire_bal_report.status == "needs_human_review"
        assert bushfire_bal_report.citations
        assert bushfire_bal_report.source_version_ids == [BOOTSTRAP_BUSHFIRE_BAL_BASIC_GUIDANCE_VERSION_ID]
        assert bushfire_bal_report.answer.startswith("For a BAL Assessment (Basic) Report")
        assert "100 metres" in bushfire_bal_report.answer
        assert "BAL-LOW" in bushfire_bal_report.answer
        _assert_clear_supported_answer(bushfire_bal_report.answer)

        bushfire_construction_requirements = RetrievalService(db).ask(
            "What BAL construction requirements apply?"
        )
        assert bushfire_construction_requirements.status == "unsupported"
        assert bushfire_construction_requirements.citations == []
        assert "AS 3959" in bushfire_construction_requirements.answer

        design_review = RetrievalService(db).ask(
            "What information should be provided for R-Codes Volume 2 design review?"
        )
        assert design_review.status == "needs_human_review"
        assert design_review.citations
        assert design_review.source_version_ids == [BOOTSTRAP_VOL2_A4_GUIDANCE_VERSION_ID]
        assert design_review.answer.startswith("For R-Codes Volume 2 design review")
        _assert_clear_supported_answer(design_review.answer)

        development_application = RetrievalService(db).ask(
            "What materials are needed for a development application under R-Codes Volume 2?"
        )
        assert development_application.status == "needs_human_review"
        assert development_application.citations
        assert set(development_application.source_version_ids) == {
            BOOTSTRAP_VOL2_A4_GUIDANCE_VERSION_ID,
            BOOTSTRAP_VOL2_A5_GUIDANCE_VERSION_ID,
        }
        assert development_application.answer.startswith("For an R-Codes Volume 2 development application")
        _assert_clear_supported_answer(development_application.answer)

        rule_rows = {
            row.id: row for row in db.scalars(select(RuleRow).where(RuleRow.source_version_id == version.id))
        }
        assert rule_rows[BOOTSTRAP_OPEN_SPACE_RULE_ROW_ID].rule_key == "open_space"
        assert rule_rows[BOOTSTRAP_OUTDOOR_LIVING_RULE_ROW_ID].rule_key == "outdoor_living_area"
    finally:
        db.close()


def test_demo_source_bootstrap_backfills_existing_site_cover_excerpt():
    db = _session()
    try:
        ensure_demo_source_library(db)
        for model, row_id in [
            (SourceCitation, BOOTSTRAP_SITE_COVER_CITATION_ID),
            (SourceChunk, BOOTSTRAP_SITE_COVER_CHUNK_ID),
            (RuleRow, BOOTSTRAP_SITE_COVER_RULE_ROW_ID),
            (ClauseDisposition, BOOTSTRAP_SITE_COVER_DISPOSITION_ID),
            (Clause, BOOTSTRAP_SITE_COVER_CLAUSE_ID),
        ]:
            row = db.get(model, row_id)
            assert row is not None
            db.delete(row)
        db.flush()

        result = ensure_demo_source_library(db)

        assert result["created"] is False
        assert result["updated"] is True
        answer = RetrievalService(db).ask("What are the WA residential R-Code site cover rules?")
        assert answer.status == "needs_human_review"
        assert answer.citations
        assert "maximum site cover" in answer.answer
    finally:
        db.close()


def test_demo_source_bootstrap_rule_rows_drive_traced_compliance_when_resolved():
    db = _session()
    try:
        ensure_demo_source_library(db)
        project = Project(
            project_name="Bootstrap compliance",
            address="1 Example Street, Perth WA",
            local_government="Perth",
            project_type="single_house",
            stage="concept",
            r_code_density="R30",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
        )
        db.add(project)
        db.flush()
        profile = AddressProfile(
            project_id=project.id,
            input_address=project.address,
            formatted_address=project.address,
            resolution_status="resolved",
            confidence="high",
            local_government="Perth",
            resolver_sources_json="[]",
            dataset_version_ids_json="[]",
            issues_json="[]",
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
        )
        db.add(profile)
        db.flush()

        resolved = ResolvedRuleService(db).resolve_for_project(
            project.id,
            ResolvedRulesRequest(address_profile_id=profile.id, as_of_date="2026-06-06"),
        )

        assert resolved.status == "needs_human_review"
        assert {
            BOOTSTRAP_OPEN_SPACE_RULE_ROW_ID,
            BOOTSTRAP_OUTDOOR_LIVING_RULE_ROW_ID,
            BOOTSTRAP_SITE_COVER_RULE_ROW_ID,
        }.issubset({row.rule_row_id for row in resolved.resolved_rules})

        for key, value, unit in [
            ("site_area_m2", 500, "m2"),
            ("building_footprint_m2", 250, "m2"),
            ("open_space_m2", 230, "m2"),
            ("front_setback_m", 4, "m"),
            ("outdoor_living_area_m2", 24, "m2"),
            ("outdoor_living_min_dimension_m", 4, "m"),
        ]:
            db.add(
                ExtractedMeasurement(
                    project_id=project.id,
                    key=key,
                    value=value,
                    unit=unit,
                    source="manual",
                    evidence_ref=f"manual:{key}",
                )
            )
        db.flush()

        matrix = ComplianceService(db).run_checks(project.id)
        results = {row.check_key: row for row in matrix.results}

        assert results["open_space"].status == "likely_pass"
        assert results["open_space"].rule_ids == [BOOTSTRAP_OPEN_SPACE_RULE_ROW_ID]
        assert results["open_space"].decision_trace_id
        assert results["outdoor_living_area"].status == "likely_pass"
        assert results["outdoor_living_area"].rule_ids == [BOOTSTRAP_OUTDOOR_LIVING_RULE_ROW_ID]
        assert results["outdoor_living_area"].decision_trace_id
    finally:
        db.close()


def test_demo_source_bootstrap_seeds_missing_excerpt_into_non_empty_source_library():
    db = _session()
    try:
        db.add(
            SourceDocument(
                title="Existing Source",
                authority="Example authority",
                source_type="guidance",
                canonical_url="https://example.test/existing",
            )
        )
        db.flush()

        result = ensure_demo_source_library(db)

        assert result["created"] is True
        assert db.scalar(select(SourceDocument).where(SourceDocument.title == "Existing Source")) is not None
        assert db.scalar(select(SourceDocument).where(SourceDocument.title == "R-Codes Volume 1 bootstrap excerpt")) is not None

        answer = RetrievalService(db).ask("What is the open space requirement for R30?")
        assert answer.status == "needs_human_review"
        assert "R30 open space: 45%" in answer.answer
    finally:
        db.close()


def test_demo_source_bootstrap_uses_stable_ids_across_empty_databases():
    first = _bootstrap_snapshot()
    second = _bootstrap_snapshot()

    assert first == second
    assert first["source_document_id"] == "src_bootstrap_rcodes_v1_excerpt"
    assert first["source_version_id"] == "sv_bootstrap_rcodes_v1_20260410_excerpt"
    assert first["citation_source_version_id"] == first["source_version_id"]


def _bootstrap_snapshot() -> dict[str, str]:
    db = _session()
    try:
        result = ensure_demo_source_library(db)
        citation = db.scalar(select(SourceCitation))
        assert citation is not None
        return {
            "source_document_id": result["source_document_id"],
            "source_version_id": result["source_version_id"],
            "rule_row_id": result["rule_row_id"],
            "citation_id": citation.id,
            "citation_source_version_id": citation.source_version_id,
            "citation_json": citation.citation_json,
        }
    finally:
        db.close()


def _assert_clear_supported_answer(answer: str) -> None:
    assert not answer.startswith("Based on the matched approved source chunks:")
    assert "Source:" in answer or "Sources:" in answer
    assert "This is assistive only" in answer


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return session_factory()

"""Schema contract tests for governance tables (PR-2).

Mirrors the style of tests/test_v3_schema_contract.py. Verifies that
the metadata declared in src/draftcheck/db/models.py matches the design
in docs/process-control/implementation-map.md.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
)

from draftcheck.db.models import (
    Base,
    GovernanceControl,
    GovernanceFinding,
    GovernanceKpi,
    GovernanceKpiResult,
    GovernancePipelineStep,
    GovernanceReview,
    GovernanceRisk,
)


def test_governance_pipeline_steps_table_contract() -> None:
    tables = Base.metadata.tables
    assert "governance_pipeline_steps" in tables
    table = tables["governance_pipeline_steps"]

    # Required columns
    for col in ("id", "stage", "function_path", "is_critical", "owner_role"):
        assert col in table.c, f"missing column {col!r}"

    # is_critical must default to false (server side is the migration's concern;
    # the model sets default False).
    assert table.c.is_critical.default.arg is False
    assert table.c.owner_role.default.arg == "operator"

    # function_path must be unique
    unique_names = {
        c.name for c in table.constraints if isinstance(c, UniqueConstraint)
    }
    assert "uq_governance_pipeline_steps_function" in unique_names

    # Indexes per map §5.4
    index_names = {idx.name for idx in table.indexes}
    assert "ix_governance_pipeline_steps_stage" in index_names
    assert "ix_governance_pipeline_steps_critical" in index_names


def test_governance_risks_table_contract() -> None:
    tables = Base.metadata.tables
    assert "governance_risks" in tables
    table = tables["governance_risks"]

    for col in ("id", "code", "name", "severity", "default_owner_role"):
        assert col in table.c, f"missing column {col!r}"

    # code is unique by Index (uq_governance_risks_code in migration;
    # SQLAlchemy unique=True on the column is what we assert here).
    assert table.c.code.unique is True
    assert table.c.severity.default.arg == "major"
    assert table.c.default_owner_role.default.arg == "operator"


def test_governance_controls_table_contract() -> None:
    tables = Base.metadata.tables
    assert "governance_controls" in tables
    table = tables["governance_controls"]

    for col in (
        "id",
        "code",
        "name",
        "control_type",
        "control_function_path",
        "owner_role",
        "test_frequency_days",
        "last_tested_at",
        "metadata_json",
    ):
        assert col in table.c, f"missing column {col!r}"

    # code FKs to governance_risks.code
    fk_targets = {fk.target_fullname for fk in table.c.code.foreign_keys}
    assert "governance_risks.code" in fk_targets

    # control_type CHECK constraint exists
    check_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    assert "ck_governance_controls_type" in check_names

    # name is unique
    unique_names = {
        c.name for c in table.constraints if isinstance(c, UniqueConstraint)
    }
    assert "uq_governance_controls_name" in unique_names

    # Indexes
    index_names = {idx.name for idx in table.indexes}
    assert "ix_governance_controls_risk" in index_names
    assert "ix_governance_controls_last_tested" in index_names


def test_governance_kpis_table_contract() -> None:
    tables = Base.metadata.tables
    assert "governance_kpis" in tables
    assert "governance_kpi_results" in tables

    kpis = tables["governance_kpis"]
    for col in (
        "id",
        "code",
        "name",
        "sql_template",
        "warning_threshold",
        "breach_threshold",
        "review_cadence_days",
        "owner_role",
    ):
        assert col in kpis.c, f"missing kpis column {col!r}"
    assert kpis.c.code.unique is True

    results = tables["governance_kpi_results"]
    for col in (
        "id",
        "kpi_id",
        "period_start",
        "period_end",
        "value",
        "status",
        "evidence_id",
        "computed_at",
    ):
        assert col in results.c, f"missing kpi_results column {col!r}"

    # status CHECK
    check_names = {
        c.name for c in results.constraints if isinstance(c, CheckConstraint)
    }
    assert "ck_governance_kpi_results_status" in check_names

    # kpi_id FKs to governance_kpis
    fk_targets = {fk.target_fullname for fk in results.c.kpi_id.foreign_keys}
    assert "governance_kpis.id" in fk_targets

    # evidence_id FKs to artifacts
    evidence_fks = {fk.target_fullname for fk in results.c.evidence_id.foreign_keys}
    assert "artifacts.id" in evidence_fks


def test_governance_findings_table_contract() -> None:
    tables = Base.metadata.tables
    assert "governance_findings" in tables
    table = tables["governance_findings"]

    for col in (
        "id",
        "org_id",
        "risk_code",
        "severity",
        "subject_type",
        "subject_id",
        "summary",
        "evidence_refs_json",
        "proposed_remediation",
        "proposed_by_job_trace_id",
        "proposed_by_model",
        "skill_version_id",
        "status",
        "decision_user_id",
        "decision_reason",
        "decision_evidence_id",
        "decision_at",
        "linked_capa_id",
        "created_at",
    ):
        assert col in table.c, f"missing column {col!r}"

    # FK targets
    fk_targets = {fk.column.table.name + "." + fk.column.name for fk in table.foreign_keys}
    assert "orgs.id" in fk_targets
    assert "governance_risks.code" in fk_targets
    assert "job_traces.id" in fk_targets
    assert "artifacts.id" in fk_targets
    assert "review_items.id" in fk_targets

    # CHECK constraints
    check_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    assert "ck_governance_findings_status" in check_names
    assert "ck_governance_findings_severity" in check_names

    # Partial unique index for proposed (subject, risk) pairs
    index_names = {idx.name for idx in table.indexes}
    assert "uq_governance_findings_subject_risk_proposed" in index_names

    # Status default is 'proposed'
    assert table.c.status.default.arg == "proposed"

    # Severity default is 'major'
    assert table.c.severity.default.arg == "major"


def test_governance_reviews_table_contract() -> None:
    tables = Base.metadata.tables
    assert "governance_reviews" in tables
    table = tables["governance_reviews"]

    for col in (
        "id",
        "review_type",
        "period_start",
        "period_end",
        "chair_user_id",
        "summary",
        "decisions_json",
        "open_actions_json",
        "evidence_pack_refs_json",
        "created_at",
    ):
        assert col in table.c, f"missing column {col!r}"

    # chair_user_id FKs to users
    chair_fks = {fk.target_fullname for fk in table.c.chair_user_id.foreign_keys}
    assert "users.id" in chair_fks

    # review_type CHECK
    check_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    assert "ck_governance_reviews_type" in check_names

    # Indexes
    index_names = {idx.name for idx in table.indexes}
    assert "ix_governance_reviews_period" in index_names
    assert "ix_governance_reviews_chair" in index_names

    assert table.c.review_type.default.arg == "ad_hoc"


def test_governance_models_have_no_create_all() -> None:
    """Defence-in-depth: the new governance SQLAlchemy classes must not call create_all."""
    import re
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[1] / "src" / "draftcheck"
    pattern = re.compile(r"(?<![\w\.])create_all\s*\(")
    offenders = [
        path
        for path in src_root.rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_governance_classes_are_registered() -> None:
    """The new ORM classes are present and mapped to the right tables."""
    assert GovernancePipelineStep.__tablename__ == "governance_pipeline_steps"
    assert GovernanceRisk.__tablename__ == "governance_risks"
    assert GovernanceControl.__tablename__ == "governance_controls"
    assert GovernanceKpi.__tablename__ == "governance_kpis"
    assert GovernanceKpiResult.__tablename__ == "governance_kpi_results"
    assert GovernanceFinding.__tablename__ == "governance_findings"
    assert GovernanceReview.__tablename__ == "governance_reviews"

from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.json_utils import to_json
from draftcheck_core.models import Clause, Project, ResolvedRule, RuleRow, SourceVersion
from draftcheck_ingestion.service import SourceIngestionService
from draftcheck_shared.schemas import SourceDocumentCreate


def test_source_supersession_marks_rule_rows_and_resolved_rules_stale():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = session_factory()
    try:
        service = SourceIngestionService(db)
        first = service.ingest_source(
            SourceDocumentCreate(
                title="Superseded Policy",
                authority="Fixture authority",
                source_type="local_planning_policy",
                canonical_url="https://example.test/superseded-policy",
                licence_notes="Public fixture.",
                access_type="public",
                version_label="v1",
                content="5.1.3 Site cover\nSite cover maximum percentage requirement.",
            )
        )
        old_version = db.get(SourceVersion, first.source_version_id)
        assert old_version is not None
        clause = db.scalar(select(Clause).where(Clause.source_version_id == old_version.id))
        assert clause is not None

        project = Project(
            project_name="Supersession project",
            address="1 Example Street",
            local_government="Fixture",
            project_type="single_house",
            stage="concept",
        )
        db.add(project)
        db.flush()
        rule = RuleRow(
            rule_key="site_cover",
            operator="<=",
            value_json=to_json({"max_percent": 55}),
            unit="percent",
            condition_text="single house",
            quote="Site cover maximum percentage requirement.",
            clause_id=clause.id,
            source_version_id=old_version.id,
            lifecycle_status="approved",
            approved_by="reviewer",
            approved_at=old_version.retrieved_at,
        )
        db.add(rule)
        db.flush()
        resolved_rule = ResolvedRule(
            project_id=project.id,
            rule_row_id=rule.id,
            as_of_date="2026-06-06",
            assessment_basis="current_rules",
            applies_reason="Fixture resolved rule.",
            status="needs_human_review",
            citations_json=to_json([{"source_version_id": old_version.id, "clause_id": clause.clause_id}]),
        )
        db.add(resolved_rule)
        db.flush()

        second = service.ingest_source(
            SourceDocumentCreate(
                title="Superseded Policy",
                authority="Fixture authority",
                source_type="local_planning_policy",
                canonical_url="https://example.test/superseded-policy",
                licence_notes="Public fixture.",
                access_type="public",
                version_label="v2",
                content="5.1.3 Site cover\nChanged site cover text that requires review.",
            )
        )

        db.refresh(old_version)
        db.refresh(rule)
        db.refresh(resolved_rule)
        assert second.source_version_id != old_version.id
        assert old_version.is_superseded is True
        assert old_version.superseded_by_id == second.source_version_id
        assert rule.lifecycle_status == "stale"
        assert rule.approved_by is None
        assert rule.approved_at is None
        assert resolved_rule.status == "stale"
        assert second.source_version_id in resolved_rule.applies_reason
    finally:
        db.close()

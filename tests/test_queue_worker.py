from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.hermes import HermesAdapter
from draftcheck_core.json_utils import to_json
from draftcheck_core.models import (
    AuditEvent,
    BackgroundJob,
    JobTrace,
    ResponseDraft,
    RfiItem,
    SourceDocument,
    SourceFetchLog,
    SourceUpdateEvent,
    SourceVersion,
)
from draftcheck_core.queue import EnqueueResult, queue_handle
from draftcheck_ingestion.service import SourceIngestionService
from draftcheck_scraper.lawful_fetcher import FetchResult
from draftcheck_shared.schemas import SourceDocumentCreate


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_queue_handle_uses_rq_enabled_not_hermes_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_ENABLED", "true")
    monkeypatch.delenv("RQ_ENABLED", raising=False)

    disabled = queue_handle("source_ingestion")
    assert disabled.backend == "local-disabled"
    assert disabled.redis_url is None

    monkeypatch.setenv("RQ_ENABLED", "true")
    monkeypatch.setenv("RQ_REDIS_URL", "redis://queue.example/0")

    enabled = queue_handle("source_ingestion")
    assert enabled.backend == "redis-rq"
    assert enabled.redis_url == "redis://queue.example/0"


def test_worker_readiness_reports_rq_and_handler_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    from draftcheck_worker import main as worker_main

    monkeypatch.setenv("RQ_ENABLED", "true")
    monkeypatch.setattr(
        worker_main,
        "check_rq_ready",
        lambda settings=None: {"status": "ok", "backend": "redis-rq", "detail": "redis://queue"},
    )
    monkeypatch.setattr(worker_main, "registered_job_types", lambda: {"source_freshness_audit"})
    monkeypatch.setattr(worker_main, "missing_required_job_types", lambda: {"council_pack"})

    result = worker_main.check_worker_ready()

    assert result["status"] == "ok"
    assert result["checks"]["rq"]["status"] == "ok"
    assert result["checks"]["missing_job_types"] == {
        "status": "warning",
        "detail": "council_pack",
    }


def test_required_worker_job_handlers_are_registered() -> None:
    from draftcheck_worker import jobs as worker_jobs

    assert worker_jobs.missing_required_job_types() == set()
    assert {
        "source_ingestion",
        "council_pack",
        "rfi_analysis",
        "source_freshness_audit",
    }.issubset(worker_jobs.registered_job_types())


def test_hermes_adapter_enqueues_local_rq_when_enabled(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_ENABLED", "false")
    monkeypatch.setenv("RQ_ENABLED", "true")
    calls: list[dict] = []

    def fake_enqueue_background_job(
        job_id: str,
        job_type: str,
        payload: dict,
        *,
        queue_name: str | None = None,
        settings=None,
    ) -> EnqueueResult:
        calls.append(
            {
                "job_id": job_id,
                "job_type": job_type,
                "payload": payload,
                "queue_name": queue_name,
                "rq_enabled": settings.rq_enabled if settings else None,
            }
        )
        return EnqueueResult(
            job_type=job_type,
            queue_name=queue_name or job_type,
            backend="redis-rq",
            status="queued",
            rq_job_id="rq-123",
            payload=payload,
        )

    monkeypatch.setattr("draftcheck_core.hermes.enqueue_background_job", fake_enqueue_background_job)
    monkeypatch.setattr(
        "draftcheck_core.hermes.fetch_rq_job_status",
        lambda remote_job_id, settings=None: {"id": remote_job_id, "status": "queued", "error": None},
    )

    status = HermesAdapter(db).enqueue_rfi_analysis_job("proj_1", {"rfi_item_count": 2})

    assert status.status == "queued"
    assert status.provider == "local-rq"
    assert status.remote_job_id == "rq-123"
    assert status.error is None
    assert calls == [
        {
            "job_id": status.id,
            "job_type": "rfi_analysis",
            "payload": {"rfi_item_count": 2},
            "queue_name": "rfi_analysis",
            "rq_enabled": True,
        }
    ]

    trace = db.scalar(select(JobTrace).where(JobTrace.job_id == status.id))
    assert trace is not None
    assert trace.provider == "local-rq"
    assert trace.status == "queued"


def test_local_rq_retry_reenqueues_failed_job(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_ENABLED", "false")
    monkeypatch.setenv("RQ_ENABLED", "true")

    job = BackgroundJob(
        job_type="source_freshness_audit",
        status="failed",
        correlation_id="corr_retry",
        provider="local-rq",
        payload_json=to_json({"source_document_id": "src_1"}),
        remote_job_id="rq-old",
        error="previous failure",
    )
    db.add(job)
    db.flush()

    def fake_enqueue_background_job(
        job_id: str,
        job_type: str,
        payload: dict,
        *,
        queue_name: str | None = None,
        settings=None,
    ) -> EnqueueResult:
        return EnqueueResult(
            job_type=job_type,
            queue_name=queue_name or job_type,
            backend="redis-rq",
            status="queued",
            rq_job_id="rq-new",
            payload=payload,
        )

    monkeypatch.setattr("draftcheck_core.hermes.enqueue_background_job", fake_enqueue_background_job)

    status = HermesAdapter(db).retry_failed_job(job.id)

    assert status.status == "queued"
    assert status.remote_job_id == "rq-new"
    assert status.error is None


def test_worker_marks_unregistered_handler_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)
    monkeypatch.setattr(worker_jobs, "HANDLERS", {})

    with SessionLocal() as session:
        job = BackgroundJob(
            job_type="source_ingestion",
            status="queued",
            correlation_id="corr_worker",
            provider="local-rq",
            payload_json=to_json({"source_version_id": "sv_1"}),
        )
        session.add(job)
        session.commit()
        job_id = job.id

    result = worker_jobs.run_background_job(job_id)

    assert result["status"] == "failed"
    assert result["error"] == "No worker handler registered for source_ingestion"

    with SessionLocal() as session:
        job = session.get(BackgroundJob, job_id)
        assert job is not None
        assert job.status == "failed"
        assert job.error == "No worker handler registered for source_ingestion"

        trace_statuses = [
            trace.status
            for trace in session.scalars(select(JobTrace).where(JobTrace.job_id == job_id)).all()
        ]
        assert trace_statuses == ["running", "failed"]

        audit_actions = [
            event.action
            for event in session.scalars(select(AuditEvent).where(AuditEvent.target_id == job_id)).all()
        ]
        assert audit_actions == ["job.started", "job.failed"]


def test_source_ingestion_worker_handler_ingests_source_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)

    with SessionLocal() as session:
        job = BackgroundJob(
            job_type="source_ingestion",
            status="queued",
            correlation_id="corr_source_ingestion",
            provider="local-rq",
            payload_json=to_json(
                {
                    "source": {
                        "title": "Worker Ingested Policy",
                        "authority": "WA Fixture",
                        "source_type": "local_planning_policy",
                        "canonical_url": "https://www.wa.gov.au/worker-ingested-policy",
                        "licence_notes": "Public fixture.",
                        "access_type": "public",
                        "content": "1.0 Worker policy\nPublic source text.",
                        "review_status": "pending_review",
                    }
                }
            ),
        )
        session.add(job)
        session.commit()
        job_id = job.id

    result = worker_jobs.run_background_job(job_id)

    assert result["status"] == "completed"
    assert result["result"]["status"] == "ingested"
    assert result["result"]["requires_human_review"] is True
    assert result["result"]["source_artifacts_created"] == 1
    assert result["result"]["rule_dispositions_created"] == 1
    assert result["result"]["rule_candidates_created"] == 0
    assert result["result"]["rule_candidates_existing"] == 0

    with SessionLocal() as session:
        job = session.get(BackgroundJob, job_id)
        assert job is not None
        assert job.source_version_id

        version = session.get(SourceVersion, job.source_version_id)
        assert version is not None
        assert version.review_status == "pending_review"
        assert version.raw_text == "1.0 Worker policy\nPublic source text."


def test_rfi_analysis_worker_handler_summarizes_existing_rfi_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)

    with SessionLocal() as session:
        item = RfiItem(
            project_id="proj_worker_rfi",
            item_number=1,
            issue_summary="Confirm site cover",
            requested_action="Please confirm the site cover calculation.",
            missing_evidence_json=to_json(["confirmed measurement", "revised drawing reference"]),
        )
        job = BackgroundJob(
            job_type="rfi_analysis",
            status="queued",
            correlation_id="corr_rfi_analysis",
            provider="local-rq",
            project_id="proj_worker_rfi",
            payload_json=to_json({"rfi_item_count": 1}),
        )
        session.add_all([item, job])
        session.commit()
        job_id = job.id

    result = worker_jobs.run_background_job(job_id)

    assert result["status"] == "completed"
    assert result["result"] == {
        "status": "completed",
        "project_id": "proj_worker_rfi",
        "rfi_item_count": 1,
        "open_item_count": 1,
        "source_requirement_candidate_count": 0,
        "missing_evidence": ["confirmed measurement", "revised drawing reference"],
        "requires_human_review": True,
    }


def test_council_pack_worker_handler_keeps_response_draft_human_review_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)

    with SessionLocal() as session:
        draft = ResponseDraft(
            project_id="proj_worker_pack",
            title="Draft council response",
            draft_text="Draft only.",
            missing_information_json=to_json(["human signoff"]),
            citations_json=to_json([]),
            requires_human_review=True,
        )
        session.add(draft)
        session.flush()
        job = BackgroundJob(
            job_type="council_pack",
            status="queued",
            correlation_id="corr_council_pack",
            provider="local-rq",
            project_id="proj_worker_pack",
            payload_json=to_json({"response_draft_id": draft.id}),
        )
        session.add(job)
        session.commit()
        job_id = job.id
        draft_id = draft.id

    result = worker_jobs.run_background_job(job_id)

    assert result["status"] == "completed"
    assert result["result"] == {
        "status": "draft_ready",
        "project_id": "proj_worker_pack",
        "response_draft_id": draft_id,
        "citation_count": 0,
        "missing_information_count": 1,
        "requires_human_review": True,
    }


def test_source_freshness_handler_ingests_changed_public_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)

    async def fake_fetch_public_content(
        url: str,
        licence_notes: str = "",
        access_type: str = "public",
    ) -> FetchResult:
        assert url == "https://www.wa.gov.au/fresh-policy"
        assert access_type == "public"
        return FetchResult(
            url=url,
            content_type="text/plain",
            content=b"1.0 Updated policy\nChanged public source text.",
            status_code=200,
            robots_allowed=True,
        )

    monkeypatch.setattr(worker_jobs, "fetch_public_content", fake_fetch_public_content)

    with SessionLocal() as session:
        initial = SourceIngestionService(session).ingest_source(
            SourceDocumentCreate(
                title="Freshness Policy",
                authority="WA Fixture",
                source_type="local_planning_policy",
                canonical_url="https://www.wa.gov.au/fresh-policy",
                licence_notes="Public fixture.",
                access_type="public",
                content="1.0 Old policy\nOriginal public source text.",
                review_status="accepted",
            )
        )
        job = BackgroundJob(
            job_type="source_freshness_audit",
            status="queued",
            correlation_id="corr_fresh",
            provider="local-rq",
            payload_json=to_json({"source_document_id": initial.source_document_id}),
        )
        session.add(job)
        session.commit()
        old_version_id = initial.source_version_id
        job_id = job.id

    result = worker_jobs.run_background_job(job_id)

    assert result["status"] == "completed"
    assert result["result"]["status"] == "changed"
    assert result["result"]["requires_human_review"] is True

    with SessionLocal() as session:
        old_version = session.get(SourceVersion, old_version_id)
        assert old_version is not None
        assert old_version.is_superseded is True

        versions = session.scalars(
            select(SourceVersion).where(SourceVersion.source_document_id == initial.source_document_id)
        ).all()
        assert len(versions) == 2
        new_version = next(version for version in versions if version.id != old_version_id)
        assert new_version.review_status == "pending_review"
        assert new_version.raw_text == "1.0 Updated policy\nChanged public source text."

        fetch_log = session.scalar(select(SourceFetchLog).where(SourceFetchLog.source_document_id == initial.source_document_id))
        assert fetch_log is not None
        assert fetch_log.status == "success"
        assert fetch_log.http_status == 200
        assert fetch_log.content_sha256 == new_version.content_sha256

        event_types = {
            event.event_type
            for event in session.scalars(
                select(SourceUpdateEvent).where(
                    SourceUpdateEvent.source_document_id == initial.source_document_id
                )
            ).all()
        }
        assert "freshness_changed" in event_types


def test_source_freshness_handler_records_unchanged_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)

    content = "1.0 Current policy\nCurrent public source text."

    async def fake_fetch_public_content(
        url: str,
        licence_notes: str = "",
        access_type: str = "public",
    ) -> FetchResult:
        return FetchResult(
            url=url,
            content_type="text/plain",
            content=content.encode(),
            status_code=200,
            robots_allowed=True,
        )

    monkeypatch.setattr(worker_jobs, "fetch_public_content", fake_fetch_public_content)

    with SessionLocal() as session:
        initial = SourceIngestionService(session).ingest_source(
            SourceDocumentCreate(
                title="Unchanged Policy",
                authority="WA Fixture",
                source_type="local_planning_policy",
                canonical_url="https://www.wa.gov.au/unchanged-policy",
                licence_notes="Public fixture.",
                access_type="public",
                content=content,
                review_status="accepted",
            )
        )
        job = BackgroundJob(
            job_type="source_freshness_audit",
            status="queued",
            correlation_id="corr_unchanged",
            provider="local-rq",
            payload_json=to_json({"source_document_id": initial.source_document_id}),
        )
        session.add(job)
        session.commit()
        job_id = job.id

    result = worker_jobs.run_background_job(job_id)

    assert result["status"] == "completed"
    assert result["result"]["status"] == "unchanged"
    assert result["result"]["source_version_id"] == initial.source_version_id

    with SessionLocal() as session:
        versions = session.scalars(
            select(SourceVersion).where(SourceVersion.source_document_id == initial.source_document_id)
        ).all()
        assert len(versions) == 1
        job = session.get(BackgroundJob, job_id)
        assert job is not None
        assert job.source_version_id == initial.source_version_id

        event = session.scalar(
            select(SourceUpdateEvent).where(
                SourceUpdateEvent.source_document_id == initial.source_document_id,
                SourceUpdateEvent.event_type == "freshness_unchanged",
            )
        )
        assert event is not None


def test_source_freshness_handler_refuses_scrape_disallowed_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)

    with SessionLocal() as session:
        source = SourceDocument(
            title="Blocked Source",
            authority="WA Fixture",
            source_type="local_planning_policy",
            canonical_url="https://www.wa.gov.au/blocked",
            licence_notes="Public fixture but scraping disabled.",
            access_type="public",
            scrape_allowed=False,
        )
        session.add(source)
        session.flush()
        job = BackgroundJob(
            job_type="source_freshness_audit",
            status="queued",
            correlation_id="corr_blocked",
            provider="local-rq",
            payload_json=to_json({"source_document_id": source.id}),
        )
        session.add(job)
        session.commit()
        job_id = job.id

    result = worker_jobs.run_background_job(job_id)

    assert result["status"] == "completed"
    assert result["result"] == {
        "status": "blocked",
        "source_document_id": source.id,
        "reason": "Source document is marked scrape_allowed=false",
    }

    with SessionLocal() as session:
        job = session.get(BackgroundJob, job_id)
        assert job is not None
        assert job.status == "completed"
        assert job.error is None
        fetch_log = session.scalar(select(SourceFetchLog))
        assert fetch_log is not None
        assert fetch_log.status == "blocked"
        assert fetch_log.error_message == "Source document is marked scrape_allowed=false"


def test_source_freshness_handler_blocks_unknown_access_and_restricted_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from draftcheck_worker import jobs as worker_jobs

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(worker_jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(worker_jobs, "init_database", lambda: None)

    async def fake_fetch_public_content(*args, **kwargs) -> FetchResult:
        raise AssertionError("blocked freshness audits must not fetch")

    monkeypatch.setattr(worker_jobs, "fetch_public_content", fake_fetch_public_content)

    with SessionLocal() as session:
        unknown = SourceDocument(
            title="Unknown Access Source",
            authority="WA Fixture",
            source_type="local_planning_policy",
            canonical_url="https://www.wa.gov.au/unknown",
            licence_notes="Needs review.",
            access_type="unknown",
            scrape_allowed=True,
        )
        restricted = SourceDocument(
            title="Restricted Notes Source",
            authority="WA Fixture",
            source_type="local_planning_policy",
            canonical_url="https://www.wa.gov.au/restricted",
            licence_notes="Subscription and no redistribution.",
            access_type="public",
            scrape_allowed=True,
        )
        session.add_all([unknown, restricted])
        session.flush()
        unknown_job = BackgroundJob(
            job_type="source_freshness_audit",
            status="queued",
            correlation_id="corr_unknown",
            provider="local-rq",
            payload_json=to_json({"source_document_id": unknown.id}),
        )
        restricted_job = BackgroundJob(
            job_type="source_freshness_audit",
            status="queued",
            correlation_id="corr_restricted",
            provider="local-rq",
            payload_json=to_json({"source_document_id": restricted.id}),
        )
        session.add_all([unknown_job, restricted_job])
        session.commit()
        unknown_job_id = unknown_job.id
        restricted_job_id = restricted_job.id

    unknown_result = worker_jobs.run_background_job(unknown_job_id)
    restricted_result = worker_jobs.run_background_job(restricted_job_id)

    assert unknown_result["result"]["status"] == "blocked"
    assert "access_type=unknown" in unknown_result["result"]["reason"]
    assert restricted_result["result"]["status"] == "blocked"
    assert restricted_result["result"]["reason"] == "Source licence or access notes indicate restricted reuse"

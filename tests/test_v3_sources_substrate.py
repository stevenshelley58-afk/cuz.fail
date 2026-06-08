from __future__ import annotations

from hashlib import sha256

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from draftcheck.ai import (
    CircuitBreaker,
    InMemoryJobTraceStore,
    LocalDeterministicModelAdapter,
    ModelAdapter,
    ModelRequest,
    ModelResponse,
    SpendCaps,
)
from draftcheck.api.auth import get_current_session, require_reviewer_session
from draftcheck.api.sources import create_sources_router
from draftcheck.domain.identity import ActiveSession, IdentityRole, InMemoryIdentityStore
from draftcheck.domain.sources import (
    AnswerStatus,
    ArtifactKind,
    ArtifactSubjectType,
    ContentAddressedArtifact,
    EmbeddingConfig,
    InMemorySourceLibrary,
    InMemorySourceSearchService,
    LicenceStatus,
    SourceAnswer,
    SourceReviewStatus,
    content_addressed_path,
)

ORIGIN_HEADERS = {"origin": "http://localhost:5173"}


def test_content_addressed_artifact_uses_sha256_storage_path() -> None:
    digest = sha256(b"abc").hexdigest()

    artifact = ContentAddressedArtifact.from_bytes(
        subject_type=ArtifactSubjectType.SOURCE_VERSION,
        subject_id="sv_fixture",
        kind=ArtifactKind.CANONICAL_TEXT,
        content=b"abc",
        media_type="text/plain",
    )

    assert content_addressed_path(digest) == f"{digest[:2]}/{digest}"
    assert artifact.sha256 == digest
    assert artifact.storage_path == f"{digest[:2]}/{digest}"
    assert artifact.size_bytes == 3


def test_content_identical_sources_keep_distinct_artifact_provenance() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())

    first = library.import_source(
        source_id="src_artifact_one",
        title="Artifact One",
        content="Shared source text.",
        licence_status=LicenceStatus.OPEN,
    )
    second = library.import_source(
        source_id="src_artifact_two",
        title="Artifact Two",
        content="Shared source text.",
        licence_status=LicenceStatus.OPEN,
    )

    first_artifact = first.artifacts[0]
    second_artifact = second.artifacts[0]
    assert first_artifact.sha256 == second_artifact.sha256
    assert first_artifact.storage_path == second_artifact.storage_path
    assert first_artifact.id != second_artifact.id
    assert first_artifact.subject_id == first.version.id
    assert second_artifact.subject_id == second.version.id


def test_search_ask_refuses_until_source_version_is_approved_and_citable() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    search = InMemorySourceSearchService(library)

    imported = library.import_source(
        title="Fixture Planning Policy",
        content="Primary street setbacks are discussed in this approved-source fixture.",
        licence_status=LicenceStatus.OPEN,
        review_status=SourceReviewStatus.PENDING_REVIEW,
    )

    refused = search.ask("primary street setbacks")
    assert refused.status is AnswerStatus.UNSUPPORTED
    assert refused.citations == ()
    assert refused.source_version_ids == ()
    assert "approved source version citation" in refused.missing_information

    library.review_source(
        source_id=imported.source.id,
        source_version_id=imported.version.id,
        review_status=SourceReviewStatus.APPROVED,
        licence_status=LicenceStatus.VERIFIED_OPEN,
        reviewer_id="reviewer-fixture",
    )

    answered = search.ask("primary street setbacks")
    assert answered.status is AnswerStatus.SUPPORTED_BY_APPROVED_SOURCES
    assert answered.citations
    assert answered.source_version_ids == (imported.version.id,)
    assert answered.citations[0].source_version_id == imported.version.id


def test_superseded_approved_source_versions_do_not_support_retrieval() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    search = InMemorySourceSearchService(library)

    first = library.import_source(
        title="Fixture Planning Policy",
        content="The superseded source text mentions old-site-cover wording.",
        source_id="src_fixture_policy",
        licence_status=LicenceStatus.OPEN,
    )
    library.review_source(
        source_id=first.source.id,
        source_version_id=first.version.id,
        review_status=SourceReviewStatus.APPROVED,
        licence_status=LicenceStatus.VERIFIED_OPEN,
        reviewer_id="reviewer-fixture",
    )
    second = library.import_source(
        title="Fixture Planning Policy",
        content="The current source text mentions current-open-space wording.",
        source_id=first.source.id,
        licence_status=LicenceStatus.OPEN,
    )
    answer_while_replacement_pending = search.ask("old-site-cover")
    library.review_source(
        source_id=second.source.id,
        source_version_id=second.version.id,
        review_status=SourceReviewStatus.APPROVED,
        licence_status=LicenceStatus.VERIFIED_OPEN,
        reviewer_id="reviewer-fixture",
    )

    old_answer = search.ask("old-site-cover")
    current_answer = search.ask("current-open-space")

    assert library.get_version(first.version.id).superseded_by_version_id == second.version.id
    assert answer_while_replacement_pending.status is AnswerStatus.SUPPORTED_BY_APPROVED_SOURCES
    assert answer_while_replacement_pending.source_version_ids == (first.version.id,)
    assert old_answer.status is AnswerStatus.UNSUPPORTED
    assert old_answer.citations == ()
    assert current_answer.status is AnswerStatus.SUPPORTED_BY_APPROVED_SOURCES
    assert current_answer.source_version_ids == (second.version.id,)


def test_embedding_config_is_pinned_and_recorded_per_chunk() -> None:
    config = EmbeddingConfig(provider="local-test", model="hash-fixture-v1", dimension=6)
    library = InMemorySourceLibrary(embedding_config=config)

    imported = library.import_source(
        title="Embedding Fixture",
        content="Clause one text.\n\nClause two text.",
        licence_status=LicenceStatus.OPEN,
    )

    chunk = library.get_chunks_for_version(imported.version.id)[0]
    assert chunk.embedding_provider == "local-test"
    assert chunk.embedding_model == "hash-fixture-v1"
    assert chunk.embedding_dimension == 6
    assert len(chunk.embedding) == 6


def test_local_model_adapter_creates_job_trace_for_successful_call() -> None:
    trace_store = InMemoryJobTraceStore()
    adapter = LocalDeterministicModelAdapter(
        mode="local",
        trace_store=trace_store,
        spend_caps=SpendCaps(
            per_job_token_cap=100,
            daily_token_cap=1000,
            daily_cost_cap_cents=100,
        ),
    )

    response = adapter.complete(
        ModelRequest(
            job_id="job_sources_ask_1",
            job_type="search.ask",
            skill_version_id="sources-ask-substrate-v0",
            prompt="Draft only from supplied cited chunks.",
            max_output_tokens=20,
            input_artifact_ids=("art_fixture",),
        )
    )

    traces = trace_store.list_traces()
    assert response.status == "succeeded"
    assert len(traces) == 1
    assert response.trace_id == traces[0].id
    assert traces[0].job_id == "job_sources_ask_1"
    assert traces[0].skill_version_id == "sources-ask-substrate-v0"
    assert traces[0].model_provider == "local"
    assert traces[0].input_artifact_ids == ("art_fixture",)
    assert traces[0].total_tokens > 0


def test_daily_spend_cap_opens_breaker_and_refused_calls_are_traced() -> None:
    trace_store = InMemoryJobTraceStore()
    breaker = CircuitBreaker()
    adapter = LocalDeterministicModelAdapter(
        mode="local",
        trace_store=trace_store,
        circuit_breaker=breaker,
        spend_caps=SpendCaps(
            per_job_token_cap=100,
            daily_token_cap=5,
            daily_cost_cap_cents=100,
        ),
    )

    refused = adapter.complete(
        ModelRequest(
            job_id="job_over_cap",
            job_type="search.ask",
            skill_version_id="sources-ask-substrate-v0",
            prompt="one two three",
            max_output_tokens=10,
        )
    )
    refused_again = adapter.complete(
        ModelRequest(
            job_id="job_after_breaker",
            job_type="search.ask",
            skill_version_id="sources-ask-substrate-v0",
            prompt="short prompt",
            max_output_tokens=1,
        )
    )

    traces = trace_store.list_traces()
    assert refused.status == "refused"
    assert refused.refusal_reason == "daily_token_cap_exceeded"
    assert breaker.is_open
    assert breaker.reason == "daily_token_cap_exceeded"
    assert refused_again.status == "refused"
    assert refused_again.refusal_reason == "circuit_breaker_open"
    assert [trace.status for trace in traces] == ["refused", "refused"]


def test_api_search_ask_does_not_return_uncited_regulatory_answer() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    client = _client(library, reviewer=True)

    imported = client.post(
        "/api/v1/sources/import",
        json={
            "title": "Unapproved Fixture",
            "content": "Site cover is mentioned here but this source is not approved.",
            "licence_status": "open",
        },
    )
    asked = client.post("/api/v1/search/ask", json={"query": "site cover"})

    body = asked.json()
    assert imported.status_code == 200
    assert asked.status_code == 200
    assert body["status"] == "unsupported"
    assert body["citations"] == []
    assert body["source_version_ids"] == []
    assert body["missing_information"] == ["approved source version citation"]


def test_api_import_cannot_self_approve_source_versions() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    client = _client(library, reviewer=True)

    rejected = client.post(
        "/api/v1/sources/import",
        json={
            "title": "Injected Approval",
            "content": "Site cover is asserted in attacker-supplied text.",
            "licence_status": "open",
            "review_status": "approved",
        },
    )
    imported = client.post(
        "/api/v1/sources/import",
        json={
            "title": "Pending Fixture",
            "content": "Site cover is mentioned, but review remains pending.",
            "licence_status": "open",
        },
    )
    asked = client.post("/api/v1/search/ask", json={"query": "site cover"})

    assert rejected.status_code == 422
    assert imported.status_code == 200
    assert imported.json()["version"]["review_status"] == "pending_review"
    assert asked.status_code == 200
    assert asked.json()["status"] == "unsupported"


def test_api_source_review_requires_authenticated_reviewer() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    reviewer_client = _client(library, reviewer=True)
    imported = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Reviewer Gate Fixture",
            "content": "Open space is discussed in this fixture source.",
            "licence_status": "open",
        },
    ).json()

    client = _client(library)
    blocked = client.post(
        f"/api/v1/sources/{imported['source']['id']}/review",
        json={
            "source_version_id": imported["version"]["id"],
            "review_status": "approved",
            "licence_status": "verified_open",
            "reviewer_id": "attacker",
        },
    )
    asked_before = reviewer_client.post("/api/v1/search/ask", json={"query": "open space"})

    approved = reviewer_client.post(
        f"/api/v1/sources/{imported['source']['id']}/review",
        json={
            "source_version_id": imported["version"]["id"],
            "review_status": "approved",
            "licence_status": "verified_open",
        },
    )
    asked_after = reviewer_client.post("/api/v1/search/ask", json={"query": "open space"})

    assert blocked.status_code == 401
    assert asked_before.json()["status"] == "unsupported"
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["licence_status"] == "verified_open"
    assert asked_after.json()["status"] == "supported_by_approved_sources"
    assert asked_after.json()["citations"]


def test_api_source_import_and_refresh_require_authenticated_reviewer() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    client = _client(library)
    reviewer_client = _client(library, reviewer=True)

    blocked_import = client.post(
        "/api/v1/sources/import",
        json={
            "title": "Blocked Import",
            "content": "No unauthenticated mutation.",
            "licence_status": "open",
        },
    )
    imported = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Refresh Fixture",
            "content": "Refresh requires reviewer.",
            "licence_status": "open",
        },
    ).json()
    blocked_refresh = client.post(f"/api/v1/sources/{imported['source']['id']}/refresh")
    allowed_refresh = reviewer_client.post(f"/api/v1/sources/{imported['source']['id']}/refresh")

    assert blocked_import.status_code == 401
    assert blocked_refresh.status_code == 401
    assert allowed_refresh.status_code == 200
    assert allowed_refresh.json()["freshness_status"] == "refresh_requested"


def test_api_source_review_worklist_requires_reviewer_and_reports_pending_sources() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    reviewer_client = _client(library, reviewer=True)
    imported = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Review Worklist Fixture",
            "content": "Planning source content requires human source and licence review.",
            "licence_status": "pending_review",
        },
    ).json()
    metadata_only = library.import_source(
        title="Metadata Only Fixture",
        uri="https://example.test/metadata-only",
        licence_status=LicenceStatus.PENDING_REVIEW,
        review_status=SourceReviewStatus.PENDING_REVIEW,
        metadata_only=True,
    )

    blocked = _client(library).get("/api/v1/sources/review-worklist")
    response = reviewer_client.get("/api/v1/sources/review-worklist")

    assert blocked.status_code == 401
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["answer_policy"] == "cite_or_refuse"
    assert body["counts"]["review_items"] == 2
    assert body["counts"]["fetched_review_items"] == 1
    assert body["counts"]["pending_fetch_items"] == 1
    by_version = {item["source_version_id"]: item for item in body["items"]}
    fetched_item = by_version[imported["version"]["id"]]
    metadata_item = by_version[metadata_only.version.id]
    assert fetched_item["recommended_action"] == "human_source_review"
    assert "source_version_pending_review" in fetched_item["issue_codes"]
    assert "licence_pending_review" in fetched_item["issue_codes"]
    assert metadata_item["recommended_action"] == "lawful_fetch"
    assert "metadata_only_pending_fetch" in metadata_item["issue_codes"]
    assert not fetched_item["can_support_search"]


def test_api_source_mutations_reject_disallowed_origin() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    reviewer_client = _client(library, reviewer=True)

    blocked = reviewer_client.post(
        "/api/v1/sources/import",
        headers={"origin": "https://evil.example"},
        json={
            "title": "Origin Blocked",
            "content": "This mutation has a hostile Origin.",
            "licence_status": "open",
        },
    )

    assert blocked.status_code == 403


def test_api_search_requires_authenticated_session_and_origin() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    anonymous_client = _client(library)
    authenticated_without_origin = _client(library, reviewer=True, default_origin=False)

    blocked_ask = anonymous_client.post("/api/v1/search/ask", json={"query": "site cover"})
    blocked_chunks = anonymous_client.post("/api/v1/search/chunks", json={"query": "site cover"})
    blocked_origin = authenticated_without_origin.post(
        "/api/v1/search/ask",
        json={"query": "site cover"},
    )

    assert blocked_ask.status_code == 401
    assert blocked_chunks.status_code == 401
    assert blocked_origin.status_code == 403


def test_api_source_mutations_require_origin_header() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    reviewer_client = _client(library, reviewer=True, default_origin=False)

    blocked = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Origin Missing",
            "content": "This mutation has no Origin.",
            "licence_status": "open",
        },
    )

    assert blocked.status_code == 403


def test_api_source_import_rejects_whitespace_only_title() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    reviewer_client = _client(library, reviewer=True)

    response = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "   ",
            "content": "Whitespace titles should fail validation.",
            "licence_status": "open",
        },
    )

    assert response.status_code == 422


def test_api_supported_search_ask_creates_governed_trace() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    trace_store = InMemoryJobTraceStore()
    adapter = LocalDeterministicModelAdapter(
        mode="local",
        trace_store=trace_store,
        spend_caps=SpendCaps(
            per_job_token_cap=1000,
            daily_token_cap=1000,
            daily_cost_cap_cents=100,
        ),
    )
    reviewer_client = _client(library, reviewer=True, model_adapter=adapter)
    imported = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Traced Ask Fixture",
            "content": "Primary street setbacks are discussed in this approved fixture.",
            "licence_status": "open",
        },
    ).json()
    reviewer_client.post(
        f"/api/v1/sources/{imported['source']['id']}/review",
        json={
            "source_version_id": imported["version"]["id"],
            "review_status": "approved",
            "licence_status": "verified_open",
        },
    )

    asked = reviewer_client.post("/api/v1/search/ask", json={"query": "primary street setbacks"})

    traces = trace_store.list_traces()
    assert asked.status_code == 200
    assert asked.json()["status"] == "supported_by_approved_sources"
    assert asked.json()["trace_id"] == traces[0].id
    assert traces[0].job_type == "search.ask"
    assert traces[0].skill_version_id == "sources-ask-substrate-v0"
    assert traces[0].input_artifact_ids == tuple(imported["version"]["artifact_ids"])
    assert library.reviews[-1].org_id


def test_standards_australia_publisher_variants_are_metadata_only() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    imported = library.import_source(
        title="Paid Standard Variant",
        content="This full text must not become searchable.",
        publisher="Standards Australia Ltd",
        licence_status=LicenceStatus.OPEN,
        review_status=SourceReviewStatus.APPROVED,
    )
    answer = InMemorySourceSearchService(library).ask("full text searchable")

    assert imported.version.metadata_only is True
    assert imported.chunks == ()
    assert answer.status is AnswerStatus.UNSUPPORTED
    assert answer.citations == ()


def test_standards_australia_uri_and_title_variants_are_metadata_only() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    by_uri = library.import_source(
        title="Referenced Technical Document",
        content="This Standards URI text must not become searchable.",
        uri="https://www.standards.org.au/standards-catalogue/fixture",
        licence_status=LicenceStatus.OPEN,
        review_status=SourceReviewStatus.APPROVED,
    )
    by_title = library.import_source(
        title="Standards Australia Fixture Title",
        content="This Standards title text must not become searchable.",
        licence_status=LicenceStatus.OPEN,
        review_status=SourceReviewStatus.APPROVED,
    )

    answer = InMemorySourceSearchService(library).ask("searchable")

    assert by_uri.version.metadata_only is True
    assert by_uri.chunks == ()
    assert by_title.version.metadata_only is True
    assert by_title.chunks == ()
    assert answer.status is AnswerStatus.UNSUPPORTED
    assert answer.citations == ()


def test_australian_standard_code_title_is_metadata_only() -> None:
    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    imported = library.import_source(
        title="AS 3959:2018 Construction of buildings in bushfire-prone areas",
        content="Paid standard token must not become searchable.",
        licence_status=LicenceStatus.OPEN,
        review_status=SourceReviewStatus.APPROVED,
    )

    answer = InMemorySourceSearchService(library).ask("paid standard token")

    assert imported.version.metadata_only is True
    assert imported.chunks == ()
    assert answer.status is AnswerStatus.UNSUPPORTED
    assert answer.citations == ()


def test_api_supported_search_ask_rejects_blank_model_trace() -> None:
    class BlankTraceAdapter:
        def complete(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(
                status="succeeded",
                text="blank trace",
                trace_id="",
                input_tokens=1,
                output_tokens=1,
                cost_cents=0,
            )

    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    reviewer_client = _client(library, reviewer=True, model_adapter=BlankTraceAdapter())
    imported = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Blank Trace Fixture",
            "content": "Site cover is discussed in this approved fixture.",
            "licence_status": "open",
        },
    ).json()
    reviewer_client.post(
        f"/api/v1/sources/{imported['source']['id']}/review",
        json={
            "source_version_id": imported["version"]["id"],
            "review_status": "approved",
            "licence_status": "verified_open",
        },
    )

    asked = reviewer_client.post("/api/v1/search/ask", json={"query": "site cover"})

    assert asked.status_code == 200
    assert asked.json()["status"] == "unsupported"
    assert asked.json()["citations"] == []
    assert asked.json()["trace_id"] == ""


def test_api_supported_search_ask_rejects_unrecorded_model_trace() -> None:
    class FakeTraceAdapter:
        def complete(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(
                status="succeeded",
                text="fake trace",
                trace_id="trace_fake_not_recorded",
                input_tokens=1,
                output_tokens=1,
                cost_cents=0,
            )

    library = InMemorySourceLibrary(embedding_config=_embedding_config())
    reviewer_client = _client(library, reviewer=True, model_adapter=FakeTraceAdapter())
    imported = reviewer_client.post(
        "/api/v1/sources/import",
        json={
            "title": "Fake Trace Fixture",
            "content": "Setbacks are discussed in this approved fixture.",
            "licence_status": "open",
        },
    ).json()
    reviewer_client.post(
        f"/api/v1/sources/{imported['source']['id']}/review",
        json={
            "source_version_id": imported["version"]["id"],
            "review_status": "approved",
            "licence_status": "verified_open",
        },
    )

    asked = reviewer_client.post("/api/v1/search/ask", json={"query": "setbacks"})

    assert asked.status_code == 200
    assert asked.json()["status"] == "unsupported"
    assert asked.json()["missing_information"] == ["governed model trace"]
    assert asked.json()["trace_id"] == "trace_fake_not_recorded"


def test_model_adapter_rejects_unvalidated_request_objects() -> None:
    adapter = LocalDeterministicModelAdapter(
        mode="local",
        spend_caps=SpendCaps(
            per_job_token_cap=100,
            daily_token_cap=1000,
            daily_cost_cap_cents=100,
        ),
    )

    with pytest.raises(TypeError, match="ModelRequest"):
        adapter.complete(object())  # type: ignore[arg-type]


def test_supported_answer_value_object_rejects_missing_citations() -> None:
    with pytest.raises(ValueError, match="require approved source citations"):
        SourceAnswer(
            status=AnswerStatus.SUPPORTED_BY_APPROVED_SOURCES,
            answer="This would be an uncited regulatory answer.",
            citations=(),
            source_version_ids=(),
        )


def _embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig(provider="local-test", model="hash-fixture-v1", dimension=8)


def _client(
    library: InMemorySourceLibrary,
    *,
    reviewer: bool = False,
    model_adapter: ModelAdapter | None = None,
    default_origin: bool = True,
) -> TestClient:
    app = FastAPI()
    app.include_router(create_sources_router(library, model_adapter=model_adapter), prefix="/api/v1")
    if reviewer:
        store = InMemoryIdentityStore()
        org = store.get_or_create_org(slug="fixture")
        user = store.get_or_create_user(
            org=org,
            email="reviewer@example.test",
            role=IdentityRole.REVIEWER,
        )
        session_issue = store.create_session(user=user, org=org)
        active_session = ActiveSession(
            session=session_issue.session,
            user=session_issue.user,
            org=session_issue.org,
        )
        app.dependency_overrides[get_current_session] = lambda: active_session
        app.dependency_overrides[require_reviewer_session] = lambda: active_session
    return TestClient(app, headers=ORIGIN_HEADERS if default_origin else None)

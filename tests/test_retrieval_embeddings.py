from __future__ import annotations

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.models import SourceArtifact, SourceChunk, SourceChunkEmbedding, SourceVersion
from draftcheck_ingestion.service import SourceIngestionService
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import SourceDocumentCreate


def test_source_ingestion_stores_chunk_embeddings():
    with _session() as db:
        result = SourceIngestionService(db).ingest_source(
            SourceDocumentCreate(
                title="Accepted Garage Policy",
                authority="City of Cockburn",
                local_government="Cockburn",
                source_type="local_planning_policy",
                canonical_url="https://example.test/garage-policy",
                licence_notes="Public fixture.",
                access_type="public",
                review_status="accepted",
                content="5.2.2 Garage dominance\nGarage width, vehicle access, bulk, and street outcomes are described.",
            )
        )

        chunks = db.scalars(
            select(SourceChunk).where(SourceChunk.source_version_id == result.source_version_id)
        ).all()
        embeddings = db.scalars(
            select(SourceChunkEmbedding).where(
                SourceChunkEmbedding.source_version_id == result.source_version_id
            )
        ).all()

        assert chunks
        assert len(embeddings) == len(chunks)
        assert all(chunk.embedding_ref for chunk in chunks)
        assert all(embedding.dimensions == 16 for embedding in embeddings)


def test_retrieval_uses_embedding_candidates_for_semantic_source_search():
    with _session() as db:
        SourceIngestionService(db).ingest_source(
            SourceDocumentCreate(
                title="Accepted Garage Policy",
                authority="City of Cockburn",
                local_government="Cockburn",
                source_type="local_planning_policy",
                canonical_url="https://example.test/garage-policy",
                licence_notes="Public fixture.",
                access_type="public",
                review_status="accepted",
                content="5.2.2 Garage dominance\nGarage width, vehicle access, bulk, and street outcomes are described.",
            )
        )

        results = RetrievalService(db).search("vehicle bulk near street", limit=3)

        assert results
        assert results[0].citation.source_title == "Accepted Garage Policy"
        assert "Garage dominance" in results[0].text


def test_duplicate_source_ingestion_backfills_missing_embeddings():
    payload = SourceDocumentCreate(
        title="Accepted Garage Policy",
        authority="City of Cockburn",
        local_government="Cockburn",
        source_type="local_planning_policy",
        canonical_url="https://example.test/garage-policy",
        licence_notes="Public fixture.",
        access_type="public",
        review_status="accepted",
        content="5.2.2 Garage dominance\nGarage width, vehicle access, bulk, and street outcomes are described.",
    )
    with _session() as db:
        first = SourceIngestionService(db).ingest_source(payload)
        chunks = db.scalars(
            select(SourceChunk).where(SourceChunk.source_version_id == first.source_version_id)
        ).all()
        for chunk in chunks:
            chunk.embedding_ref = None
        db.execute(
            delete(SourceChunkEmbedding).where(
                SourceChunkEmbedding.source_version_id == first.source_version_id
            )
        )
        db.flush()

        duplicate = SourceIngestionService(db).ingest_source(payload)
        embeddings = db.scalars(
            select(SourceChunkEmbedding).where(
                SourceChunkEmbedding.source_version_id == first.source_version_id
            )
        ).all()

        assert duplicate.duplicate is True
        assert len(embeddings) == len(chunks)
        assert all(chunk.embedding_ref for chunk in chunks)


def test_source_ingestion_records_raw_and_parsed_artifacts():
    with _session() as db:
        result = SourceIngestionService(db).ingest_source(
            SourceDocumentCreate(
                title="Accepted Artifact Policy",
                authority="City of Cockburn",
                local_government="Cockburn",
                source_type="local_planning_policy",
                canonical_url="https://example.test/artifact-policy",
                licence_notes="Public fixture.",
                access_type="public",
                review_status="accepted",
                content="5.1.3 Front setback\nFront setback must be shown on plans.",
                raw_object_key="raw/artifact-policy.pdf",
                parsed_object_key="parsed/artifact-policy.txt",
            )
        )

        artifacts = db.scalars(
            select(SourceArtifact)
            .where(SourceArtifact.source_version_id == result.source_version_id)
            .order_by(SourceArtifact.kind)
        ).all()

        assert result.source_artifacts_created == 2
        assert {(artifact.kind, artifact.object_key) for artifact in artifacts} == {
            ("parsed_text", "parsed/artifact-policy.txt"),
            ("raw_pdf", "raw/artifact-policy.pdf"),
        }
        assert all(artifact.content_sha256 for artifact in artifacts)


def test_duplicate_source_ingestion_backfills_missing_source_artifacts():
    payload = SourceDocumentCreate(
        title="Accepted Artifact Backfill Policy",
        authority="City of Cockburn",
        local_government="Cockburn",
        source_type="local_planning_policy",
        canonical_url="https://example.test/artifact-backfill-policy",
        licence_notes="Public fixture.",
        access_type="public",
        review_status="accepted",
        content="5.1.3 Front setback\nFront setback must be shown on plans.",
    )
    with _session() as db:
        first = SourceIngestionService(db).ingest_source(payload)
        version = db.get(SourceVersion, first.source_version_id)
        assert version is not None
        version.raw_object_key = None
        version.parsed_object_key = None
        db.execute(delete(SourceArtifact).where(SourceArtifact.source_version_id == first.source_version_id))
        db.flush()

        duplicate = SourceIngestionService(db).ingest_source(
            payload.model_copy(
                update={
                    "raw_object_key": "raw/artifact-backfill-policy.pdf",
                    "parsed_object_key": "parsed/artifact-backfill-policy.txt",
                }
            )
        )
        artifacts = db.scalars(
            select(SourceArtifact)
            .where(SourceArtifact.source_version_id == first.source_version_id)
            .order_by(SourceArtifact.kind)
        ).all()

        assert duplicate.duplicate is True
        assert duplicate.source_artifacts_created == 2
        assert version.raw_object_key == "raw/artifact-backfill-policy.pdf"
        assert version.parsed_object_key == "parsed/artifact-backfill-policy.txt"
        assert {(artifact.kind, artifact.object_key) for artifact in artifacts} == {
            ("parsed_text", "parsed/artifact-backfill-policy.txt"),
            ("raw_pdf", "raw/artifact-backfill-policy.pdf"),
        }


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return Session(engine)

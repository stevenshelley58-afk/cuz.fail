from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.json_utils import hash_text, to_json
from draftcheck_core.models import (
    Clause,
    ClauseDisposition,
    ReviewQueueItem,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_retrieval.service import RetrievalService
from draftcheck_shared.schemas import Citation
from scripts.rebuild_source_search_index import rebuild_source_search_index


def test_rebuild_source_search_index_only_indexes_supported_sources():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        supported_chunk_id = _add_chunk(db, "Accepted Policy", "approved setback searchable")
        _add_chunk(db, "Pending Policy", "pending setback should not index", review_status="pending_review")
        _add_chunk(db, "Blocked Policy", "blocked setback should not index", blocking_review=True)
        _add_chunk(
            db,
            "Legacy Accepted Rule Gap Policy",
            "A wall must be set back at least 1.5 m unless exempt.",
        )
        db.commit()

    indexed = rebuild_source_search_index(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT chunk_id, content FROM source_chunk_fts")).all()

    assert indexed == 1
    assert len(rows) == 1
    assert rows[0][0] == supported_chunk_id
    assert "approved setback searchable" in rows[0][1]
    assert "pending setback" not in rows[0][1]
    assert "blocked setback" not in rows[0][1]
    assert "1.5 m unless exempt" not in rows[0][1]


def test_retrieval_falls_back_when_fts_candidates_are_stale():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        stale_chunk_id = _add_chunk(
            db,
            "Stale FTS Candidate",
            "primary street setback r30 single house stale candidate",
            review_status="pending_review",
        )
        _add_chunk(
            db,
            "Accepted R-Code Street Setback Table",
            "\n".join(
                [
                    "C3.3.3 Street setbacks",
                    "Table 3.3a Minimum setback of buildings from the street",
                    "Street type R30 R35 R40 R50 R60 R80",
                    "Primary street setback 4m 4m 3m 2m 2m 2m",
                ]
            ),
            source_type="r_code",
            approved_rule_quote="Primary street setback 4m 4m 3m 2m 2m 2m",
        )
        db.commit()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE source_chunk_fts
                USING fts5(chunk_id UNINDEXED, content, tokenize='unicode61')
                """
            )
        )
        conn.execute(
            text("INSERT INTO source_chunk_fts(chunk_id, content) VALUES (:chunk_id, :content)"),
            {"chunk_id": stale_chunk_id, "content": "primary street setback r30 single house"},
        )

    with Session(engine) as db:
        answer = RetrievalService(db).ask("What is the front setback for an R30 single house?")

    assert answer.status == "needs_human_review"
    assert "R30 primary street setback: 4m" in answer.answer
    assert answer.citations


def _add_chunk(
    db: Session,
    title: str,
    content: str,
    *,
    review_status: str = "accepted",
    blocking_review: bool = False,
    source_type: str = "local_planning_policy",
    approved_rule_quote: str | None = None,
) -> str:
    source = SourceDocument(
        title=title,
        authority="Example",
        source_type=source_type,
        canonical_url=f"https://example.test/{title.lower().replace(' ', '-')}",
        access_type="public",
    )
    version = SourceVersion(
        source_document=source,
        version_label="current",
        content_sha256=hash_text(content),
        raw_text=content,
        review_status=review_status,
        reviewed_by="fixture" if review_status == "accepted" else None,
        reviewed_at=utcnow() if review_status == "accepted" else None,
    )
    db.add_all([source, version])
    db.flush()
    db.add(
        SourceLicenceReview(
            source_document_id=source.id,
            source_version_id=version.id,
            allowed_use=True,
            allowed_storage=True,
            allowed_ai_processing=True,
            reviewed_at=utcnow(),
            review_status="approved",
        )
    )
    clause = Clause(
        source_version_id=version.id,
        clause_id="1.1",
        heading=title,
        text=content,
        normalized_text=" ".join(content.lower().split()),
        start_anchor="1.1",
        text_sha256=hash_text(content),
    )
    db.add(clause)
    db.flush()
    if review_status == "accepted":
        db.add(
            ClauseDisposition(
                clause_id=clause.id,
                disposition="rule_bearing" if approved_rule_quote else "informational",
                rationale="Fixture source review disposition.",
                reviewer="fixture",
            )
        )
        if approved_rule_quote:
            db.add(
                RuleRow(
                    rule_key="front_setback",
                    operator=">=",
                    value_json=to_json({"min_value": 4.0}),
                    unit="m",
                    condition_text="",
                    quote=approved_rule_quote,
                    clause_id=clause.id,
                    source_version_id=version.id,
                    lifecycle_status="approved",
                    approved_by="fixture",
                    approved_at=utcnow(),
                )
            )
    chunk = SourceChunk(
        source_version_id=version.id,
        clause_id=clause.id,
        heading=None,
        text=content,
        token_count=len(content.split()),
    )
    db.add(chunk)
    db.flush()
    db.add(
        SourceCitation(
            source_chunk_id=chunk.id,
            source_version_id=version.id,
            clause_id=clause.id,
            citation_json=to_json(
                Citation(
                    source_document_id=source.id,
                    source_title=source.title,
                    source_version_id=version.id,
                    version_label=version.version_label,
                    effective_date=version.effective_date,
                    retrieved_at=version.retrieved_at,
                    clause_id=clause.clause_id,
                    heading=clause.heading,
                    page_number=clause.page_number,
                    canonical_url=source.canonical_url,
                    quote=content,
                ).model_dump(mode="json")
            ),
        )
    )
    if blocking_review:
        db.add(
            ReviewQueueItem(
                queue="source_review",
                source_version_id=version.id,
                target_type="source_version",
                target_id=version.id,
                reason="Blocking source review remains open.",
            )
        )
    db.flush()
    return chunk.id

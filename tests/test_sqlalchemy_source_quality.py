from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from draftcheck.domain.sources.models import LicenceStatus, SourceReviewStatus, SourceVersion
from draftcheck.domain.sources.sqlalchemy_store import (
    _count_signal_requires_review,
    _parse_repair_profile,
    _source_quality_gates,
)


def test_parse_repair_profile_marks_low_signal_raw_pdf_ready_for_repair() -> None:
    profile = _parse_repair_profile(
        source=_source(source_type="structure_plan"),
        version=_version(),
        chunk_count=1,
        citation_count=1,
        parse_quality={
            "status": "low_signal_review",
            "page_count": 20,
            "pages_with_text": 1,
            "text_coverage_ratio": 0.05,
        },
        artifact_rows=[
            _artifact(
                id="raw-1",
                kind="raw_pdf",
                storage_path="raw-sources/aa/raw-fixture",
                size_bytes=1234,
            )
        ],
        low_signal=True,
    )

    assert profile["required"] is True
    assert profile["status"] == "repair_ready"
    assert profile["next_action"] == "run OCR or PDF text-layer repair from the stored raw PDF"
    assert profile["raw_artifact_count"] == 1
    assert profile["raw_artifact_kinds"] == ["raw_pdf"]
    assert profile["raw_artifacts"][0]["storage_path"] == "raw-sources/aa/raw-fixture"
    assert "parse_quality_low_signal_review" in profile["reason_codes"]
    assert "low_text_coverage" in profile["reason_codes"]
    assert "low_page_text_coverage" in profile["reason_codes"]


def test_parse_repair_profile_blocks_low_signal_source_without_raw_artifact() -> None:
    profile = _parse_repair_profile(
        source=_source(source_type="structure_plan"),
        version=_version(),
        chunk_count=1,
        citation_count=1,
        parse_quality={"status": "low_signal_review"},
        artifact_rows=[],
        low_signal=True,
    )

    assert profile["required"] is True
    assert profile["status"] == "raw_source_missing"
    assert profile["next_action"] == (
        "refetch with raw artifact persistence before OCR or parser repair"
    )
    assert profile["raw_artifact_count"] == 0


def test_source_quality_gates_surface_parse_repair_input_readiness() -> None:
    gates = {
        gate["gate"]: gate
        for gate in _source_quality_gates(
            {
                "pending_fetch_items": 0,
                "pending_review_versions": 2,
                "low_signal_versions": 2,
                "parse_repair_ready_versions": 1,
                "parse_repair_missing_raw_artifact_versions": 1,
                "approved_citable_versions": 0,
            }
        )
    }

    assert gates["parse_repair_inputs"] == {
        "gate": "parse_repair_inputs",
        "status": "blocked",
        "blocking_count": 1,
        "ready_count": 1,
    }


def test_count_signal_allows_complete_short_ocr_document_for_human_review() -> None:
    assert (
        _count_signal_requires_review(
            chunk_count=1,
            citation_count=1,
            parse_quality={
                "status": "text_layer_extracted",
                "text_char_count": 1136,
                "text_coverage_ratio": 1.0,
            },
        )
        is False
    )


def test_count_signal_keeps_short_or_unmeasured_single_chunk_in_parse_review() -> None:
    assert (
        _count_signal_requires_review(
            chunk_count=1,
            citation_count=1,
            parse_quality={
                "status": "text_layer_extracted",
                "text_char_count": 500,
                "text_coverage_ratio": 1.0,
            },
        )
        is True
    )
    assert (
        _count_signal_requires_review(
            chunk_count=1,
            citation_count=1,
            parse_quality=None,
        )
        is True
    )


def _source(*, source_type: str) -> SimpleNamespace:
    return SimpleNamespace(source_type=source_type)


def _version(*, metadata_only: bool = False) -> SourceVersion:
    return SourceVersion(
        id="version-1",
        source_id="source-1",
        version_label="fixture",
        sha256="a" * 64,
        storage_path="aa/" + ("a" * 64),
        licence_status=LicenceStatus.PENDING_REVIEW,
        review_status=SourceReviewStatus.PENDING_REVIEW,
        fetched_at=datetime(2026, 6, 8, tzinfo=UTC),
        metadata_only=metadata_only,
    )


def _artifact(
    *,
    id: str,
    kind: str,
    storage_path: str,
    size_bytes: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        kind=kind,
        storage_path=storage_path,
        sha256="b" * 64,
        media_type="application/pdf",
        size_bytes=size_bytes,
        parser_name="fixture",
        parser_version="v0",
    )

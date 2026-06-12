from __future__ import annotations

from draftcheck.domain.documents import DocumentParser


def test_document_parser_registry_selects_dxf_by_suffix_and_returns_artifacts() -> None:
    parser = DocumentParser()

    parsed = parser.parse_document(
        document_id="doc_registry",
        filename="site-plan.dxf",
        media_type="application/octet-stream",
        content=b"0\nSECTION\n2\nENTITIES\nDIMENSION 4.5\n0\nENDSEC\n",
    )

    assert parsed.parser_name == "draftcheck.dxf_text_parser"
    assert parsed.media_type == "application/octet-stream"
    assert parsed.parse_status == "parsed"
    assert parsed.artifacts
    artifact = parsed.artifacts[0]
    assert artifact.kind == "parser_output"
    assert artifact.metadata["parser_name"] == "draftcheck.dxf_text_parser"
    assert artifact.metadata["page_count"] == len(parsed.pages)
    assert artifact.metadata["fact_count"] == len(parsed.facts)
    assert artifact.metadata["persistence_status"] == "in_memory_descriptor_pending_artifact_rows"
    assert parsed.metadata["artifacts"][0] == artifact.to_dict()


def test_document_parser_legacy_parse_tuple_remains_compatible() -> None:
    parser = DocumentParser()

    media_type, parser_name, parse_status, pages, facts, metadata = parser.parse(
        document_id="doc_legacy",
        filename="site-plan.txt",
        media_type="text/plain",
        content=b"Lot area: 450 m2",
    )

    assert media_type == "text/plain"
    assert parser_name == "draftcheck.plain_text_parser"
    assert parse_status == "parsed"
    assert len(pages) == 1
    assert len(facts) == 1
    assert metadata["artifacts"][0]["kind"] == "parser_output"

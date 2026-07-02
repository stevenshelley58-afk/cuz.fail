from draftcheck.domain.sources import fetching
from draftcheck.domain.sources.fetching import SourceTextExtraction, extract_source_text_with_metadata


def test_pdf_extraction_falls_back_to_pymupdf_when_pypdf_raises(monkeypatch) -> None:
    class BrokenPdfReader:
        def __init__(self, _content) -> None:
            raise RuntimeError("malformed text operator")

    def fake_pymupdf(_content: bytes) -> SourceTextExtraction:
        return SourceTextExtraction(
            text="fallback text",
            metadata={
                "extraction": {"content_kind": "pdf", "method": "pymupdf_text_layer"},
                "parse_quality": {"status": "text_layer_extracted"},
            },
        )

    monkeypatch.setattr("pypdf.PdfReader", BrokenPdfReader)
    monkeypatch.setattr(fetching, "extract_pdf_text_with_pymupdf", fake_pymupdf)

    result = extract_source_text_with_metadata(
        b"%PDF-1.7",
        content_type="application/pdf",
        final_url="https://example.test/document.pdf",
    )

    assert result.text == "fallback text"
    assert result.metadata["extraction"]["method"] == "pymupdf_text_layer"
    assert result.metadata["extraction"]["fallback_from"] == "pypdf_text_layer"
    assert "malformed text operator" in result.metadata["extraction"]["fallback_reason"]

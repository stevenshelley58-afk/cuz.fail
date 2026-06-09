"""Document parsing domain helpers for the V3 rebuild."""

from draftcheck.domain.documents.parsing import (
    DocumentFact,
    DocumentNotFoundError,
    DocumentPage,
    DocumentParseError,
    DocumentParseResult,
    DocumentParser,
    DocumentRecord,
    DocumentReviewStatus,
    InMemoryDocumentLibrary,
    ParserCapability,
    decode_text_bytes,
    extract_docx_text,
    extract_pdf_pages,
    sample_parser_accuracy_report,
)

__all__ = [
    "DocumentFact",
    "DocumentNotFoundError",
    "DocumentPage",
    "DocumentParseError",
    "DocumentParseResult",
    "DocumentParser",
    "DocumentRecord",
    "DocumentReviewStatus",
    "InMemoryDocumentLibrary",
    "ParserCapability",
    "decode_text_bytes",
    "extract_docx_text",
    "extract_pdf_pages",
    "sample_parser_accuracy_report",
]

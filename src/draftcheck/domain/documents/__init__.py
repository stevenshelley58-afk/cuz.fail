"""Document parsing domain helpers for the V3 rebuild."""

from draftcheck.domain.documents.chunks import (
    DocumentChunk,
    DocumentChunkSearchHit,
    build_document_chunks,
    search_document_chunks,
    search_persisted_document_chunks,
    write_document_chunks,
)
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
    "DocumentChunk",
    "DocumentChunkSearchHit",
    "DocumentNotFoundError",
    "DocumentPage",
    "DocumentParseError",
    "DocumentParseResult",
    "DocumentParser",
    "DocumentRecord",
    "DocumentReviewStatus",
    "InMemoryDocumentLibrary",
    "ParserCapability",
    "build_document_chunks",
    "decode_text_bytes",
    "extract_docx_text",
    "extract_pdf_pages",
    "sample_parser_accuracy_report",
    "search_document_chunks",
    "search_persisted_document_chunks",
    "write_document_chunks",
]

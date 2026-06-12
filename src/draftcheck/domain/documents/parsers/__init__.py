"""Parser registry contracts for document extraction.

The registry is intentionally persistence-free.  Parser artifacts describe
what was extracted so DB artifact-row wiring can be added later without
changing parser selection or parser return shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class DocumentArtifact:
    kind: str
    label: str
    media_type: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "media_type": self.media_type,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ParsedDocument:
    media_type: str
    parser_name: str
    parser_version: str
    parse_status: str
    pages: tuple[Any, ...]
    facts: tuple[Any, ...]
    artifacts: tuple[DocumentArtifact, ...]
    metadata: dict[str, Any]


class DocumentContentParser(Protocol):
    name: str
    version: str

    def can_parse(self, media_type: str, filename: str) -> bool:
        """Return true when this parser should handle the normalized document."""

    def parse(
        self,
        *,
        document_id: str,
        filename: str,
        media_type: str,
        content: bytes,
    ) -> ParsedDocument:
        """Parse content without writing persistence artifacts."""


class DocumentParserRegistry:
    def __init__(self, parsers: tuple[DocumentContentParser, ...]) -> None:
        if not parsers:
            raise ValueError("at least one document parser is required")
        self.parsers = parsers

    def select(self, *, media_type: str, filename: str) -> DocumentContentParser:
        for parser in self.parsers:
            if parser.can_parse(media_type, filename):
                return parser
        return self.parsers[-1]


__all__ = [
    "DocumentArtifact",
    "DocumentContentParser",
    "DocumentParserRegistry",
    "ParsedDocument",
]

"""Value objects for the V3 source library."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Literal


class SourceError(Exception):
    """Base source-domain error."""


class SourceNotFoundError(SourceError):
    """Requested source or source version does not exist."""


class SourceNotCitableError(SourceError):
    """Source state cannot support citable regulatory retrieval."""


class LicenceStatus(str, Enum):
    OPEN = "open"
    VERIFIED_OPEN = "verified_open"
    PENDING_REVIEW = "pending_review"
    RESTRICTED = "restricted"
    METADATA_ONLY = "metadata_only"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"

    @property
    def can_store_full_text(self) -> bool:
        return self in {
            LicenceStatus.OPEN,
            LicenceStatus.VERIFIED_OPEN,
            LicenceStatus.PENDING_REVIEW,
        }

    @property
    def can_support_citation(self) -> bool:
        return self in {LicenceStatus.OPEN, LicenceStatus.VERIFIED_OPEN}


class SourceReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    STALE = "stale"


class ArtifactSubjectType(str, Enum):
    SOURCE_VERSION = "source_version"
    DOCUMENT = "document"
    DOCUMENT_PAGE = "document_page"
    EXPORT = "export"
    SKILL_VERSION = "skill_version"


class ArtifactKind(str, Enum):
    RAW_PDF = "raw_pdf"
    RAW_HTML = "raw_html"
    RAW_DOCX = "raw_docx"
    PARSED_TEXT = "parsed_text"
    OCR_TEXT = "ocr_text"
    TABLE_JSON = "table_json"
    PAGE_IMAGE = "page_image"
    EXTRACTION_OUTPUT = "extraction_output"
    CANONICAL_TEXT = "canonical_text"
    EXPORT_FILE = "export_file"
    SKILL_BUNDLE = "skill_bundle"
    METADATA_ONLY = "metadata_only"


class AnswerStatus(str, Enum):
    SUPPORTED_BY_APPROVED_SOURCES = "supported_by_approved_sources"
    UNSUPPORTED = "unsupported"


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def sha256_hex(content: bytes) -> str:
    return sha256(content).hexdigest()


def content_addressed_path(content_sha256: str) -> str:
    normalized = content_sha256.lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError("content sha256 must be a 64-character hex digest")
    return f"{normalized[:2]}/{normalized}"


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    dimension: int

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("embedding provider is required")
        if not self.model.strip():
            raise ValueError("embedding model is required")
        if self.dimension <= 0:
            raise ValueError("embedding dimension must be positive")


@dataclass(frozen=True)
class ContentAddressedArtifact:
    id: str
    subject_type: ArtifactSubjectType
    subject_id: str
    kind: ArtifactKind
    storage_path: str
    sha256: str
    media_type: str
    size_bytes: int
    parser_name: str | None = None
    parser_version: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_bytes(
        cls,
        *,
        subject_type: ArtifactSubjectType,
        subject_id: str,
        kind: ArtifactKind,
        content: bytes,
        media_type: str,
        parser_name: str | None = None,
        parser_version: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ContentAddressedArtifact:
        digest = sha256_hex(content)
        record_digest = sha256(
            f"{subject_type.value}:{subject_id}:{digest}".encode("utf-8")
        ).hexdigest()
        artifact_id = f"art_{record_digest[:16]}"
        return cls(
            id=artifact_id,
            subject_type=subject_type,
            subject_id=subject_id,
            kind=kind,
            storage_path=content_addressed_path(digest),
            sha256=digest,
            media_type=media_type,
            size_bytes=len(content),
            parser_name=parser_name,
            parser_version=parser_version,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    uri: str | None
    publisher: str | None
    licence_status: LicenceStatus
    created_at: datetime
    latest_version_id: str | None = None


@dataclass(frozen=True)
class SourceVersion:
    id: str
    source_id: str
    version_label: str
    sha256: str
    storage_path: str
    licence_status: LicenceStatus
    review_status: SourceReviewStatus
    fetched_at: datetime
    published_at: datetime | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    superseded_by_version_id: str | None = None
    artifact_ids: tuple[str, ...] = ()
    metadata_only: bool = False

    @property
    def can_support_citable_retrieval(self) -> bool:
        return (
            self.review_status is SourceReviewStatus.APPROVED
            and self.licence_status.can_support_citation
            and not self.metadata_only
            and self.superseded_by_version_id is None
        )


@dataclass(frozen=True)
class SourceCitation:
    id: str
    source_id: str
    source_version_id: str
    chunk_id: str
    source_title: str
    locator: str
    quote: str
    uri: str | None = None


@dataclass(frozen=True)
class SourceChunk:
    id: str
    source_id: str
    source_version_id: str
    ordinal: int
    text: str
    text_sha256: str
    citation_id: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class SourceReview:
    id: str
    org_id: str
    source_id: str
    source_version_id: str
    review_status: SourceReviewStatus
    licence_status: LicenceStatus
    actor_id: str
    reviewed_at: datetime
    notes: str | None = None


@dataclass(frozen=True)
class SourceImportResult:
    source: SourceDocument
    version: SourceVersion
    artifacts: tuple[ContentAddressedArtifact, ...]
    chunks: tuple[SourceChunk, ...]
    citations: tuple[SourceCitation, ...]
    duplicate: bool = False
    metadata_only: bool = False


@dataclass(frozen=True)
class SourceSearchHit:
    chunk: SourceChunk
    citation: SourceCitation
    version: SourceVersion
    score: float


@dataclass(frozen=True)
class SourceAnswer:
    status: AnswerStatus
    answer: str
    citations: tuple[SourceCitation, ...]
    source_version_ids: tuple[str, ...]
    assumptions: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    confidence: float = 0.0
    needs_verification: bool = True
    risk_level: Literal["unknown", "low", "medium", "high"] = "unknown"
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if self.status is AnswerStatus.SUPPORTED_BY_APPROVED_SOURCES and not self.citations:
            raise ValueError("supported regulatory answers require approved source citations")
        if self.status is AnswerStatus.UNSUPPORTED and self.confidence != 0.0:
            raise ValueError("unsupported answers must not report confidence")


@dataclass(frozen=True)
class SourceFreshness:
    source_id: str
    latest_version_id: str | None
    freshness_status: Literal["current", "no_versions", "refresh_requested"]
    fetched_at: datetime | None
    refresh_requested_at: datetime | None = None


@dataclass(frozen=True)
class SourceRefreshResult:
    source_id: str
    status: Literal["refresh_recorded"]
    freshness_status: Literal["refresh_requested"]
    requested_at: datetime

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import hash_text, normalize_text, to_json, word_limited_quote
from draftcheck_core.models import (
    Clause,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceFetchLog,
    SourceUpdateEvent,
    SourceVersion,
)
from draftcheck_scraper.lawful_fetcher import assert_lawful_source
from draftcheck_shared.schemas import SourceDocumentCreate


@dataclass(frozen=True)
class IngestionResult:
    source_document_id: str
    source_version_id: str
    clauses_created: int
    chunks_created: int
    duplicate: bool = False


@dataclass(frozen=True)
class HermesCorpusItemResult:
    row_number: int
    title: str
    status: str
    reason: str | None = None
    source_document_id: str | None = None
    source_version_id: str | None = None
    metadata_only: bool = False
    duplicate: bool = False


@dataclass(frozen=True)
class HermesCorpusImportResult:
    imported: int
    skipped: int
    metadata_only: int
    duplicates: int
    error_count: int
    errors: list[HermesCorpusItemResult]
    items: list[HermesCorpusItemResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceIngestionService:
    def __init__(self, db: Session):
        self.db = db

    def import_manifest_yaml(self, manifest_yaml: str) -> list[IngestionResult]:
        parsed = yaml.safe_load(manifest_yaml) or {}
        entries = parsed.get("sources", parsed if isinstance(parsed, list) else [])
        if not isinstance(entries, list):
            raise ValueError("Manifest must contain a sources list")
        return [self.ingest_source(SourceDocumentCreate(**entry)) for entry in entries]

    def import_entries(self, entries: list[SourceDocumentCreate]) -> list[IngestionResult]:
        return [self.ingest_source(entry) for entry in entries]

    def import_hermes_corpus(
        self,
        inventory_jsonl: str,
        corpus_root: str | Path | None = None,
    ) -> HermesCorpusImportResult:
        root = Path(corpus_root).expanduser().resolve() if corpus_root else None
        imported = 0
        skipped = 0
        metadata_only_count = 0
        duplicate_count = 0
        errors: list[HermesCorpusItemResult] = []
        items: list[HermesCorpusItemResult] = []

        for row_number, raw_line in enumerate(inventory_jsonl.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                item = HermesCorpusItemResult(
                    row_number=row_number,
                    title="invalid-json",
                    status="error",
                    reason=f"Invalid JSONL row: {exc.msg}",
                )
                errors.append(item)
                items.append(item)
                continue
            if not isinstance(row, dict):
                item = HermesCorpusItemResult(
                    row_number=row_number,
                    title="invalid-json",
                    status="error",
                    reason="JSONL row must be an object",
                )
                errors.append(item)
                items.append(item)
                continue

            title = str(row.get("title") or row.get("source_id") or f"row {row_number}")
            skip_reason = self._hermes_skip_reason(row)
            if skip_reason:
                skipped += 1
                items.append(
                    HermesCorpusItemResult(
                        row_number=row_number,
                        title=title,
                        status="skipped",
                        reason=skip_reason,
                    )
                )
                continue

            try:
                source_in, metadata_only = self._source_from_hermes_row(row, root)
                result = self.ingest_source(source_in)
            except Exception as exc:
                item = HermesCorpusItemResult(
                    row_number=row_number,
                    title=title,
                    status="error",
                    reason=str(exc),
                )
                errors.append(item)
                items.append(item)
                continue

            imported += 1
            if metadata_only:
                metadata_only_count += 1
            if result.duplicate:
                duplicate_count += 1
            items.append(
                HermesCorpusItemResult(
                    row_number=row_number,
                    title=source_in.title,
                    status="duplicate" if result.duplicate else "imported",
                    source_document_id=result.source_document_id,
                    source_version_id=result.source_version_id,
                    metadata_only=metadata_only,
                    duplicate=result.duplicate,
                )
            )

        return HermesCorpusImportResult(
            imported=imported,
            skipped=skipped,
            metadata_only=metadata_only_count,
            duplicates=duplicate_count,
            error_count=len(errors),
            errors=errors,
            items=items,
        )

    def ingest_source(self, source_in: SourceDocumentCreate) -> IngestionResult:
        self._assert_allowed(source_in)
        content = normalize_text(source_in.content or "")
        metadata_only = not bool(content)
        if not content:
            if not source_in.canonical_url:
                raise ValueError("Source content or canonical_url is required")
            if not _is_standards_australia(source_in):
                self._log_fetch(source_in.canonical_url, "pending", source_in)
            content = _metadata_only_text(source_in)

        source_doc = self._upsert_source_document(source_in)
        content_hash = hash_text(content)
        existing = self.db.scalar(
            select(SourceVersion).where(
                SourceVersion.source_document_id == source_doc.id,
                SourceVersion.content_sha256 == content_hash,
            )
        )
        if existing:
            return IngestionResult(source_doc.id, existing.id, 0, 0, duplicate=True)

        for old_version in self.db.scalars(
            select(SourceVersion).where(
                SourceVersion.source_document_id == source_doc.id,
                SourceVersion.is_superseded.is_(False),
            )
        ):
            old_version.is_superseded = True

        version = SourceVersion(
            source_document_id=source_doc.id,
            version_label=source_in.version_label,
            effective_date=source_in.effective_date,
            published_date=source_in.published_date,
            content_sha256=content_hash,
            raw_object_key=source_in.raw_object_key,
            parsed_object_key=source_in.parsed_object_key,
            raw_text=content,
            parse_status="metadata_only" if metadata_only else source_in.parse_status,
        )
        if source_in.retrieved_at:
            version.retrieved_at = source_in.retrieved_at
        self.db.add(version)
        self.db.flush()

        if metadata_only:
            self.db.add(
                SourceUpdateEvent(
                    source_document_id=source_doc.id,
                    event_type="metadata_registered",
                    notes="Registered metadata-only source; no citable source chunks created.",
                )
            )
            record_audit(
                self.db,
                action="source.metadata_registered",
                target_type="source_version",
                target_id=version.id,
                metadata={
                    "source_document_id": source_doc.id,
                    "content_sha256": content_hash,
                    "metadata_only": True,
                },
            )
            self.db.flush()
            return IngestionResult(source_doc.id, version.id, 0, 0)

        clauses = self._extract_clauses(content, source_in.canonical_url)
        chunks_created = 0
        for clause_data in clauses:
            clause = Clause(
                source_version_id=version.id,
                clause_id=clause_data["clause_id"],
                heading=clause_data.get("heading"),
                page_number=clause_data.get("page_number"),
                text=clause_data["text"],
                normalized_text=normalize_text(clause_data["text"]),
                start_anchor=clause_data["anchor"],
                text_sha256=hash_text(clause_data["text"]),
            )
            self.db.add(clause)
            self.db.flush()
            for index, chunk_text in enumerate(_chunk_text(clause.text)):
                chunk = SourceChunk(
                    source_version_id=version.id,
                    clause_id=clause.id,
                    heading=clause.heading,
                    page_number=clause.page_number,
                    text=chunk_text,
                    token_count=max(1, int(len(chunk_text.split()) * 1.25)),
                )
                self.db.add(chunk)
                self.db.flush()
                citation = {
                    "source_document_id": source_doc.id,
                    "source_title": source_doc.title,
                    "source_version_id": version.id,
                    "version_label": version.version_label,
                    "effective_date": version.effective_date,
                    "retrieved_at": version.retrieved_at.isoformat(),
                    "clause_id": clause.clause_id,
                    "heading": clause.heading,
                    "page_number": clause.page_number,
                    "canonical_url": source_doc.canonical_url,
                    "quote": word_limited_quote(chunk.text, 80),
                    "chunk_index": index,
                }
                self.db.add(
                    SourceCitation(
                        source_chunk_id=chunk.id,
                        source_version_id=version.id,
                        clause_id=clause.id,
                        citation_json=to_json(citation),
                    )
                )
                chunks_created += 1

        self.db.add(
            SourceUpdateEvent(
                source_document_id=source_doc.id,
                event_type="version_ingested",
                notes=f"Ingested {len(clauses)} clauses and {chunks_created} chunks",
            )
        )
        record_audit(
            self.db,
            action="source.version.ingested",
            target_type="source_version",
            target_id=version.id,
            metadata={
                "source_document_id": source_doc.id,
                "content_sha256": content_hash,
                "clauses_created": len(clauses),
                "chunks_created": chunks_created,
            },
        )
        self.db.flush()
        return IngestionResult(source_doc.id, version.id, len(clauses), chunks_created)

    def _assert_allowed(self, source_in: SourceDocumentCreate) -> None:
        if _is_standards_australia(source_in) and not source_in.content:
            return
        if not source_in.scrape_allowed:
            raise ValueError("Source is marked scrape_allowed=false")
        if source_in.access_type not in {"public", "unknown"}:
            raise ValueError("Restricted sources cannot be auto-ingested")
        if _is_standards_australia(source_in) and source_in.content:
            raise ValueError("Do not ingest paid/proprietary Australian Standards full text")
        if source_in.canonical_url and not source_in.content:
            assert_lawful_source(source_in.canonical_url, source_in.licence_notes, source_in.access_type)

    def _hermes_skip_reason(self, row: dict[str, Any]) -> str | None:
        if not _as_bool(row.get("robots_allowed"), default=True):
            return "robots.txt disallowed automated access"
        robots_status = str(row.get("robots_status") or "").lower().strip()
        if robots_status in {"denied", "disallowed", "blocked", "false", "no"}:
            return f"robots_status={robots_status}"
        access_type = str(row.get("access_type") or "unknown").lower().strip()
        is_standards = _is_standards_australia_row(row)
        if not is_standards and access_type not in {"public", "open"}:
            return f"restricted access_type={access_type}"
        parse_status = str(row.get("parse_status") or "ok").lower().strip()
        if parse_status in {"blocked", "paywalled", "login_required", "captcha", "robots_disallowed"}:
            return f"parse_status={parse_status}"
        if not is_standards and parse_status not in {"ok", "partial", "metadata_only"}:
            return f"parse_status={parse_status}"
        if not is_standards and _has_restricted_access_terms(row):
            return "licence or access notes indicate restricted reuse"
        if not is_standards:
            canonical_url = _hermes_canonical_url(row)
            if not canonical_url:
                return "missing canonical_url/retrieved_url"
            try:
                assert_lawful_source(
                    canonical_url,
                    _hermes_licence_notes(row, metadata_only=False),
                    "public" if access_type == "open" else access_type,
                )
            except ValueError as exc:
                return str(exc)
        return None

    def _source_from_hermes_row(
        self,
        row: dict[str, Any],
        corpus_root: Path | None,
    ) -> tuple[SourceDocumentCreate, bool]:
        title = _clean_str(row.get("title") or row.get("source_id"))
        if not title:
            raise ValueError("Hermes row is missing title/source_id")

        metadata_only = _is_standards_australia_row(row)
        access_type = (_clean_str(row.get("access_type")) or "unknown").lower()
        stored_access_type = "public" if access_type == "open" else access_type
        content = None if metadata_only else self._read_hermes_content(row, corpus_root)
        if not metadata_only and not content:
            raise ValueError("Hermes row has no parsed text content to ingest")

        authority = _clean_str(row.get("authority")) or "Unknown authority"
        source_in = SourceDocumentCreate(
            title=title,
            jurisdiction=_clean_str(row.get("jurisdiction")) or "WA",
            authority=authority,
            local_government=_clean_str(row.get("local_government")),
            source_type=_clean_str(row.get("source_type")) or "source_document",
            canonical_url=_hermes_canonical_url(row),
            licence_notes=_hermes_licence_notes(row, metadata_only),
            access_type=stored_access_type,
            scrape_allowed=_as_bool(row.get("robots_allowed"), default=True)
            and access_type in {"public", "unknown", "open"},
            content=content,
            version_label=_hermes_version_label(row),
            effective_date=_clean_str(row.get("effective_date")),
            published_date=_clean_str(row.get("published_date")),
            retrieved_at=row.get("retrieved_at"),
            parse_status="metadata_only" if metadata_only else str(row.get("parse_status") or "ok").lower(),
            raw_object_key=_clean_str(row.get("raw_path")),
            parsed_object_key=None if metadata_only else _clean_str(row.get("parsed_path")),
        )
        return source_in, metadata_only

    def _read_hermes_content(self, row: dict[str, Any], corpus_root: Path | None) -> str | None:
        parsed_path = _resolve_hermes_path(row.get("parsed_path"), corpus_root)
        if parsed_path and parsed_path.is_file():
            content = parsed_path.read_text(encoding="utf-8", errors="replace")
            _validate_hermes_sha256(row, parsed_path, content, corpus_root)
            return content

        raw_path = _resolve_hermes_path(row.get("raw_path"), corpus_root)
        content_type = str(row.get("content_type") or "").lower()
        if raw_path and raw_path.is_file() and _is_text_like_path(raw_path, content_type):
            content = raw_path.read_text(encoding="utf-8", errors="replace")
            _validate_hermes_sha256(row, raw_path, content, corpus_root)
            return content
        return None

    def _upsert_source_document(self, source_in: SourceDocumentCreate) -> SourceDocument:
        stmt = select(SourceDocument).where(SourceDocument.title == source_in.title)
        if source_in.canonical_url:
            stmt = select(SourceDocument).where(SourceDocument.canonical_url == source_in.canonical_url)
        source_doc = self.db.scalar(stmt)
        if source_doc:
            source_doc.jurisdiction = source_in.jurisdiction
            source_doc.authority = source_in.authority
            source_doc.local_government = source_in.local_government
            source_doc.source_type = source_in.source_type
            source_doc.licence_notes = source_in.licence_notes
            source_doc.access_type = source_in.access_type
            source_doc.scrape_allowed = source_in.scrape_allowed
            return source_doc

        source_doc = SourceDocument(
            title=source_in.title,
            jurisdiction=source_in.jurisdiction,
            authority=source_in.authority,
            local_government=source_in.local_government,
            source_type=source_in.source_type,
            canonical_url=source_in.canonical_url,
            licence_notes=source_in.licence_notes,
            access_type=source_in.access_type,
            scrape_allowed=source_in.scrape_allowed,
        )
        self.db.add(source_doc)
        self.db.flush()
        return source_doc

    def _log_fetch(self, url: str, status: str, source_in: SourceDocumentCreate) -> None:
        self.db.add(
            SourceFetchLog(
                url=url,
                status=status,
                retrieved_at=datetime.utcnow() if status == "success" else None,
                metadata_json=to_json(
                    {
                        "title": source_in.title,
                        "authority": source_in.authority,
                        "note": "Registered for lawful fetch; no bypass attempted.",
                    }
                ),
            )
        )

    def _extract_clauses(self, content: str, canonical_url: str | None) -> list[dict[str, Any]]:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        clauses: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        heading_pattern = re.compile(
            r"^(?:clause\s+|cl\.?\s*)?([A-Z]?\d+(?:\.\d+){0,5}(?:\([a-z0-9]+\))?)\s*[-:.)]?\s*(.*)$",
            re.IGNORECASE,
        )
        for line in lines:
            match = heading_pattern.match(line)
            if match and len(line) < 180:
                if current:
                    clauses.append(current)
                clause_id = match.group(1)
                heading = match.group(2).strip() or None
                current = {
                    "clause_id": clause_id,
                    "heading": heading,
                    "text": line,
                    "anchor": _anchor(canonical_url, clause_id),
                }
            elif current:
                current["text"] = f"{current['text']}\n{line}"
            else:
                current = {
                    "clause_id": "intro",
                    "heading": "Introductory material",
                    "text": line,
                    "anchor": _anchor(canonical_url, "intro"),
                }
        if current:
            clauses.append(current)
        return clauses or [
            {
                "clause_id": "source-text",
                "heading": "Source text",
                "text": content,
                "anchor": _anchor(canonical_url, "source-text"),
            }
        ]


def _chunk_text(text: str, max_chars: int = 1400) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _anchor(url: str | None, clause_id: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", clause_id.lower()).strip("-")
    return f"{url}#{safe}" if url else f"source-text#{safe}"


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1", "allowed"}:
            return True
        if normalized in {"false", "no", "n", "0", "disallowed", "blocked"}:
            return False
    return default


def _is_standards_australia(source_in: SourceDocumentCreate) -> bool:
    haystack = " ".join(
        part
        for part in [
            source_in.title,
            source_in.authority,
            source_in.source_type,
            source_in.canonical_url or "",
        ]
        if part
    ).lower()
    return "standards australia" in haystack or "standards.org.au" in haystack


def _is_standards_australia_row(row: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(row.get(key) or "")
        for key in ("title", "authority", "source_type", "canonical_url", "retrieved_url")
    ).lower()
    return "standards australia" in haystack or "standards.org.au" in haystack


def _hermes_canonical_url(row: dict[str, Any]) -> str | None:
    return _clean_str(row.get("canonical_url") or row.get("retrieved_url"))


def _has_restricted_access_terms(row: dict[str, Any]) -> bool:
    terms = (
        "paywall",
        "login required",
        "captcha",
        "proprietary",
        "no reuse",
        "no redistribution",
        "licence required",
        "license required",
        "subscription",
        "paid access",
    )
    haystack = " ".join(
        str(row.get(key) or "")
        for key in ("licence_notes", "notes", "access_notes", "rights", "copyright_notes")
    ).lower()
    return any(term in haystack for term in terms)


def _metadata_only_text(source_in: SourceDocumentCreate) -> str:
    notes = normalize_text(source_in.licence_notes)
    if _is_standards_australia(source_in):
        metadata_note = "Metadata-only source record. Paid or proprietary Australian Standards full text is not stored."
    else:
        metadata_note = "Metadata-only source record. Full source content has not been fetched or stored."
    lines = [
        source_in.title,
        metadata_note,
        f"Authority: {source_in.authority}",
        f"Access type: {source_in.access_type}",
    ]
    if source_in.canonical_url:
        lines.append(f"Canonical URL: {source_in.canonical_url}")
    if notes:
        lines.append(f"Access notes: {notes}")
    return "\n".join(lines)


def _hermes_licence_notes(row: dict[str, Any], metadata_only: bool) -> str:
    parts = [
        _clean_str(row.get("licence_notes")),
        _clean_str(row.get("notes")),
        f"Hermes source_id={row.get('source_id')}" if row.get("source_id") else None,
        f"Hermes retrieved_at={row.get('retrieved_at')}" if row.get("retrieved_at") else None,
        f"Hermes retrieved_url={row.get('retrieved_url')}" if row.get("retrieved_url") else None,
        f"Hermes raw_path={row.get('raw_path')}" if row.get("raw_path") else None,
        f"Hermes parsed_path={row.get('parsed_path')}" if row.get("parsed_path") else None,
        f"Hermes sha256={row.get('sha256')}" if row.get("sha256") else None,
    ]
    if metadata_only:
        parts.append("Metadata only; Australian Standards full text was not read or stored.")
    return " | ".join(part for part in parts if part)


def _hermes_version_label(row: dict[str, Any]) -> str | None:
    explicit = _clean_str(row.get("version_label"))
    if explicit:
        return explicit
    last_updated = _clean_str(row.get("last_updated_text"))
    if last_updated:
        return last_updated
    digest = _clean_str(row.get("sha256"))
    if digest:
        return f"hermes:{digest[:12]}"
    return _clean_str(row.get("retrieved_at"))


def _resolve_hermes_path(value: Any, corpus_root: Path | None) -> Path | None:
    path_text = _clean_str(value)
    if not path_text:
        return None
    if corpus_root is None:
        raise ValueError("corpus_root is required before reading Hermes corpus files")
    root = corpus_root.expanduser().resolve()
    path = Path(path_text)
    if not path.is_absolute():
        path = root / path
    resolved = path.expanduser().resolve()
    if not _is_relative_to(resolved, root):
        raise ValueError(f"Hermes corpus path escapes corpus_root: {path_text}")
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_hermes_sha256(
    row: dict[str, Any],
    parsed_or_raw_path: Path,
    content: str,
    corpus_root: Path | None,
) -> None:
    expected = _clean_str(row.get("sha256"))
    if not expected:
        return
    normalized_expected = expected.lower()
    text_digest = sha256(content.encode("utf-8")).hexdigest()
    if text_digest == normalized_expected:
        return

    raw_path = _resolve_hermes_path(row.get("raw_path"), corpus_root)
    if raw_path and raw_path.is_file():
        raw_digest = sha256(raw_path.read_bytes()).hexdigest()
        if raw_digest == normalized_expected:
            return
    raise ValueError(
        f"Hermes sha256 mismatch for {parsed_or_raw_path.name}; parsed/raw content requires manual review"
    )


def _is_text_like_path(path: Path, content_type: str) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".html", ".htm", ".csv", ".json", ".jsonl", ".xml"}:
        return True
    return content_type.startswith("text/") or "json" in content_type or "html" in content_type

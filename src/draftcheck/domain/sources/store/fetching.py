"""Lawful-fetch, parse-repair, discovery, and fetch-record operations for the source library."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from draftcheck.db.models import (
    Artifact as DbArtifact,
    Source as DbSource,
    SourceChunk as DbSourceChunk,
    SourceCitation as DbSourceCitation,
    SourceFetchLog as DbSourceFetchLog,
    SourceVersion as DbSourceVersion,
)
from draftcheck.domain.sources.fetching import (
    CandidateSourceLink,
    extract_pdf_text_with_ocr,
    extract_pdf_text_with_pymupdf,
    fetch_public_source,
    sanitize_source_text,
)
from draftcheck.domain.sources.models import (
    ArtifactKind,
    ArtifactSubjectType,
    LicenceStatus,
    SourceNotFoundError,
    SourceReviewStatus,
    SourceVersion,
    content_addressed_path,
)
from draftcheck.domain.sources.store._helpers import (
    _authority_for_discovered_link,
    _candidate_links_from_metadata,
    _candidate_links_from_text,
    _count_signal_requires_review,
    _declared_size_mb,
    _is_public_http_url,
    _optional_int,
    _optional_str,
    _parse_quality_requires_review,
    _parse_quality_text_char_count,
    _parse_repair_profile,
    _preferred_raw_repair_artifact,
    _quality_readiness,
    _raw_artifact_kind,
    _title_from_url,
    _utc_now,
    _version_parse_quality,
)

if TYPE_CHECKING:
    from draftcheck.domain.sources.store._base import SourceStoreBase
else:  # pragma: no cover - typing-only base; mixins compose at runtime
    SourceStoreBase = object


class SourceFetchOps(SourceStoreBase):
    """Lawful-fetch, parse-repair, and discovery methods for ``SqlAlchemySourceLibrary``."""

    def fetch_pending_sources(
        self,
        *,
        local_government: str | None = None,
        source_type: str | None = None,
        title_contains: str | None = None,
        readiness: str | None = None,
        max_declared_size_mb: float | None = None,
        limit: int = 5,
        org_id: UUID,
        requested_by_user_id: UUID,
        force: bool = False,
    ) -> dict[str, object]:
        candidates = self._pending_fetch_candidates(
            local_government=local_government,
            source_type=source_type,
            title_contains=title_contains,
            readiness=readiness,
            max_declared_size_mb=max_declared_size_mb,
            limit=limit,
            force=force,
        )
        fetched = 0
        failed = 0
        skipped = 0
        items: list[dict[str, object]] = []
        for candidate in candidates:
            if not candidate["canonical_url"]:
                skipped += 1
                continue
            try:
                public_source = fetch_public_source(
                    str(candidate["canonical_url"]),
                    licence_notes=str(candidate.get("licence_notes") or ""),
                )
                candidate_metadata = candidate.get("metadata")
                source_metadata = (
                    candidate_metadata
                    if isinstance(candidate_metadata, Mapping)
                    else {}
                )
                result = self.import_source(
                    title=str(candidate["title"]),
                    content=public_source.text,
                    uri=str(candidate["canonical_url"]),
                    publisher=str(candidate["authority"]),
                    licence_status=LicenceStatus.PENDING_REVIEW,
                    review_status=SourceReviewStatus.PENDING_REVIEW,
                    media_type="text/plain",
                    metadata_only=False,
                    jurisdiction=str(candidate["jurisdiction"]),
                    authority=str(candidate["authority"]),
                    local_government=_optional_str(candidate.get("local_government")),
                    source_type=str(candidate["source_type"]),
                    access_type=str(candidate["access_type"]),
                    licence_notes=str(candidate.get("licence_notes") or ""),
                    version_label=f"fetched:{public_source.sha256[:12]}",
                    source_metadata=source_metadata,
                    version_metadata=public_source.metadata,
                )
                raw_artifact = self.record_raw_fetch_artifact(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    content=public_source.content,
                    content_type=public_source.content_type,
                    final_url=public_source.final_url,
                    metadata=public_source.metadata,
                )
                self.record_fetch_log(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="public_source_fetch",
                    status="success",
                    metadata=public_source.metadata,
                    completed=True,
                )
                fetched += 1
                items.append(
                    {
                        "source_id": result.source.id,
                        "source_version_id": result.version.id,
                        "title": result.source.title,
                        "status": "success",
                        "duplicate": result.duplicate,
                        "chunk_count": len(result.chunks),
                        "citation_count": len(result.citations),
                        "parse_quality": public_source.metadata.get("parse_quality"),
                        "raw_artifact_id": raw_artifact["id"],
                        "review_status": result.version.review_status.value,
                    }
                )
            except (httpx.HTTPError, ValueError) as exc:
                self.record_fetch_log(
                    source_id=str(candidate["source_id"]),
                    source_version_id=_optional_str(candidate.get("source_version_id")),
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="public_source_fetch",
                    status="failed",
                    metadata={"canonical_url": candidate["canonical_url"]},
                    error=str(exc),
                    completed=True,
                )
                failed += 1
                items.append(
                    {
                        "source_id": str(candidate["source_id"]),
                        "title": str(candidate["title"]),
                        "status": "failed",
                        "error": str(exc),
                    }
                )
        return {
            "fetched": fetched,
            "failed": failed,
            "skipped": skipped,
            "items": items,
        }

    def repair_parse_quality_sources(
        self,
        *,
        local_government: str | None = None,
        source_type: str | None = None,
        title_contains: str | None = None,
        limit: int = 5,
        org_id: UUID,
        requested_by_user_id: UUID,
        force: bool = False,
        ocr: bool = False,
        max_ocr_pages: int = 30,
        ocr_dpi: int = 200,
    ) -> dict[str, object]:
        candidates = self._parse_repair_candidates(
            local_government=local_government,
            source_type=source_type,
            title_contains=title_contains,
            limit=limit,
        )
        repaired = 0
        failed = 0
        skipped = 0
        items: list[dict[str, object]] = []
        storage_root = Path(os.getenv("OBJECT_STORAGE_ROOT", ".storage")).expanduser()
        for candidate in candidates:
            source_id = str(candidate["source_id"])
            source_version_id = str(candidate["source_version_id"])
            title = str(candidate["title"])
            raw_kind = str(candidate["raw_kind"])
            if raw_kind != ArtifactKind.RAW_PDF.value:
                skipped += 1
                items.append(
                    {
                        "source_id": source_id,
                        "source_version_id": source_version_id,
                        "title": title,
                        "status": "skipped",
                        "reason": f"unsupported raw artifact kind: {raw_kind}",
                    }
                )
                continue
            raw_path = storage_root / str(candidate["raw_storage_path"])
            if not raw_path.is_file():
                failed += 1
                error = f"raw artifact file is missing: {candidate['raw_storage_path']}"
                self.record_fetch_log(
                    source_id=source_id,
                    source_version_id=source_version_id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="parse_repair",
                    status="failed",
                    metadata={"raw_artifact_id": candidate["raw_artifact_id"]},
                    error=error,
                    completed=True,
                )
                items.append(
                    {
                        "source_id": source_id,
                        "source_version_id": source_version_id,
                        "title": title,
                        "status": "failed",
                        "error": error,
                    }
                )
                continue
            try:
                raw_content = raw_path.read_bytes()
                extraction = (
                    extract_pdf_text_with_ocr(
                        raw_content,
                        max_pages=max_ocr_pages,
                        dpi=ocr_dpi,
                    )
                    if ocr
                    else extract_pdf_text_with_pymupdf(raw_content)
                )
                repaired_text = sanitize_source_text(extraction.text)
                if not repaired_text.strip():
                    raise ValueError("repair parser produced no parseable text")
                previous_char_count = _optional_int(candidate.get("current_text_char_count")) or 0
                if len(repaired_text) <= previous_char_count and not force:
                    skipped += 1
                    self.record_fetch_log(
                        source_id=source_id,
                        source_version_id=source_version_id,
                        org_id=org_id,
                        requested_by_user_id=requested_by_user_id,
                        fetch_kind="parse_repair",
                        status="skipped_no_improvement",
                        metadata={
                            "raw_artifact_id": candidate["raw_artifact_id"],
                            "repair_mode": "ocr" if ocr else "text_layer",
                            "previous_text_char_count": previous_char_count,
                            "repaired_text_char_count": len(repaired_text),
                            **extraction.metadata,
                        },
                        completed=True,
                    )
                    items.append(
                        {
                            "source_id": source_id,
                            "source_version_id": source_version_id,
                            "title": title,
                            "status": "skipped",
                            "reason": "repair text was not longer than the current extraction",
                            "previous_text_char_count": previous_char_count,
                            "repaired_text_char_count": len(repaired_text),
                            "parse_quality": extraction.metadata.get("parse_quality"),
                        }
                    )
                    continue
                repair_metadata = {
                    **extraction.metadata,
                    "repair": {
                        "method": (
                            "pymupdf_render_tesseract_ocr"
                            if ocr
                            else "pymupdf_text_layer"
                        ),
                        "previous_source_version_id": source_version_id,
                        "raw_artifact_id": candidate["raw_artifact_id"],
                        "previous_text_char_count": previous_char_count,
                        "repaired_text_char_count": len(repaired_text),
                        "review_required": True,
                        "note": "Parser repair creates a new pending-review version; it does not approve the source.",
                    },
                }
                result = self.import_source(
                    source_id=source_id,
                    title=title,
                    content=repaired_text,
                    uri=_optional_str(candidate.get("canonical_url")),
                    publisher=str(candidate["authority"]),
                    licence_status=LicenceStatus.PENDING_REVIEW,
                    review_status=SourceReviewStatus.PENDING_REVIEW,
                    media_type="text/plain",
                    metadata_only=False,
                    jurisdiction=str(candidate["jurisdiction"]),
                    authority=str(candidate["authority"]),
                    local_government=_optional_str(candidate.get("local_government")),
                    source_type=str(candidate["source_type"]),
                    access_type=str(candidate["access_type"]),
                    licence_notes=str(candidate.get("licence_notes") or ""),
                    version_label=(
                        f"{'ocr' if ocr else 'repaired'}:"
                        f"{sha256(repaired_text.encode('utf-8')).hexdigest()[:12]}"
                    ),
                    source_metadata=cast(Mapping[str, object], candidate["source_metadata"]),
                    version_metadata=repair_metadata,
                )
                raw_artifact = self.record_raw_fetch_artifact(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    content=raw_content,
                    content_type=str(candidate.get("raw_media_type") or "application/pdf"),
                    final_url=str(candidate.get("canonical_url") or ""),
                    metadata={
                        "copied_from_source_version_id": source_version_id,
                        "copied_from_artifact_id": str(candidate["raw_artifact_id"]),
                    },
                )
                self.record_fetch_log(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="parse_repair",
                    status="success",
                    metadata={
                        "previous_source_version_id": source_version_id,
                        "raw_artifact_id": raw_artifact["id"],
                        "previous_raw_artifact_id": candidate["raw_artifact_id"],
                        "repair_mode": "ocr" if ocr else "text_layer",
                        "previous_text_char_count": previous_char_count,
                        "repaired_text_char_count": len(repaired_text),
                        "duplicate": result.duplicate,
                        **extraction.metadata,
                    },
                    completed=True,
                )
                repaired += 1
                items.append(
                    {
                        "source_id": result.source.id,
                        "source_version_id": result.version.id,
                        "previous_source_version_id": source_version_id,
                        "title": result.source.title,
                        "status": "success",
                        "duplicate": result.duplicate,
                        "chunk_count": len(result.chunks),
                        "citation_count": len(result.citations),
                        "previous_text_char_count": previous_char_count,
                        "repaired_text_char_count": len(repaired_text),
                        "parse_quality": extraction.metadata.get("parse_quality"),
                        "raw_artifact_id": raw_artifact["id"],
                        "review_status": result.version.review_status.value,
                    }
                )
            except (OSError, ValueError) as exc:
                failed += 1
                self.record_fetch_log(
                    source_id=source_id,
                    source_version_id=source_version_id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="parse_repair",
                    status="failed",
                    metadata={"raw_artifact_id": candidate["raw_artifact_id"]},
                    error=str(exc),
                    completed=True,
                )
                items.append(
                    {
                        "source_id": source_id,
                        "source_version_id": source_version_id,
                        "title": title,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
        return {
            "repaired": repaired,
            "failed": failed,
            "skipped": skipped,
            "items": items,
        }

    def discover_child_sources(
        self,
        *,
        local_government: str | None = None,
        limit: int = 50,
        org_id: UUID,
        requested_by_user_id: UUID,
    ) -> dict[str, object]:
        """Register discovered child source links as pending-review fetch targets."""

        parents = self._child_discovery_candidates(local_government=local_government)
        links_seen = 0
        discovered = 0
        duplicates = 0
        skipped = 0
        items: list[dict[str, object]] = []
        for parent in parents:
            if discovered >= limit:
                break
            candidate_links = cast(tuple[CandidateSourceLink, ...], parent["candidate_links"])
            for link in candidate_links:
                links_seen += 1
                if discovered >= limit:
                    break
                if not isinstance(link, CandidateSourceLink) or not _is_public_http_url(link.url):
                    skipped += 1
                    continue
                if link.url == parent.get("canonical_url"):
                    skipped += 1
                    continue
                authority = _authority_for_discovered_link(
                    link.url,
                    fallback=str(parent["authority"]),
                )
                if self._already_has_fetched_source(link.url):
                    skipped += 1
                    continue
                source_metadata = {
                    "discovery_source": "source_child_link",
                    "discovered_from_source_id": str(parent["source_id"]),
                    "discovered_from_source_version_id": str(parent["source_version_id"]),
                    "discovered_from_url": parent.get("canonical_url"),
                    "discovery_label": link.label,
                    "licence_notes": "Discovered from official public source page; fetch, licence, currency, and source-version review required before citation.",
                    "pending_review_reason": "Discovered child source requires lawful fetch and human approval.",
                }
                result = self.import_source(
                    title=link.label or _title_from_url(link.url),
                    content="",
                    uri=link.url,
                    publisher=authority,
                    licence_status=LicenceStatus.PENDING_REVIEW,
                    review_status=SourceReviewStatus.PENDING_REVIEW,
                    metadata_only=True,
                    jurisdiction=str(parent["jurisdiction"]),
                    authority=authority,
                    local_government=_optional_str(parent.get("local_government")),
                    source_type=link.source_type,
                    access_type=str(parent["access_type"]),
                    licence_notes=str(source_metadata["licence_notes"]),
                    version_label="discovered-anchor",
                    source_metadata=source_metadata,
                    version_metadata=source_metadata,
                )
                if result.duplicate:
                    duplicates += 1
                    status = "duplicate"
                else:
                    discovered += 1
                    status = "pending_fetch"
                self.record_fetch_log(
                    source_id=result.source.id,
                    source_version_id=result.version.id,
                    org_id=org_id,
                    requested_by_user_id=requested_by_user_id,
                    fetch_kind="source_link_discovery",
                    status=status,
                    metadata={
                        "url": link.url,
                        "label": link.label,
                        "source_type": link.source_type,
                        "discovered_from_source_id": str(parent["source_id"]),
                    },
                    completed=status == "duplicate",
                )
                items.append(
                    {
                        "source_id": result.source.id,
                        "source_version_id": result.version.id,
                        "title": result.source.title,
                        "canonical_url": link.url,
                        "source_type": link.source_type,
                        "status": status,
                    }
                )
        return {
            "discovered": discovered,
            "duplicates": duplicates,
            "skipped": skipped,
            "links_seen": links_seen,
            "items": items,
        }

    def record_fetch_log(
        self,
        *,
        source_id: str,
        source_version_id: str | None,
        org_id: UUID,
        requested_by_user_id: UUID,
        fetch_kind: str,
        status: str,
        metadata: Mapping[str, object] | None = None,
        error: str | None = None,
        completed: bool = False,
    ) -> None:
        with self._session_factory() as session:
            with session.begin():
                source = self._get_source_by_id(session, source_id)
                version = (
                    self._get_version_by_id(session, source_version_id)
                    if source_version_id
                    else self._latest_version(session, source)
                )
                session.add(
                    DbSourceFetchLog(
                        id=uuid4(),
                        org_id=org_id,
                        source_id=source.id,
                        source_version_id=version.id if version else None,
                        requested_by_user_id=requested_by_user_id,
                        fetch_kind=fetch_kind,
                        status=status,
                        completed_at=_utc_now() if completed else None,
                        error=error,
                        metadata_json=dict(metadata or {}),
                    )
                )

    def record_raw_fetch_artifact(
        self,
        *,
        source_id: str,
        source_version_id: str,
        content: bytes,
        content_type: str,
        final_url: str,
        metadata: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        digest = sha256(content).hexdigest()
        relative_path = f"raw-sources/{content_addressed_path(digest)}"
        storage_root = Path(os.getenv("OBJECT_STORAGE_ROOT", ".storage")).expanduser()
        artifact_path = storage_root / relative_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        if not artifact_path.exists():
            artifact_path.write_bytes(content)
        kind = _raw_artifact_kind(content_type=content_type, final_url=final_url)
        with self._session_factory() as session:
            with session.begin():
                source = self._get_source_by_id(session, source_id)
                version = self._get_version_by_id(session, source_version_id)
                if version.source_id != source.id:
                    raise SourceNotFoundError(f"source version does not belong to source: {source_version_id}")
                existing = session.scalar(
                    select(DbArtifact).where(
                        DbArtifact.subject_id == version.id,
                        DbArtifact.kind == kind.value,
                        DbArtifact.sha256 == digest,
                    )
                )
                if existing is None:
                    existing = DbArtifact(
                        id=uuid4(),
                        org_id=source.org_id,
                        subject_type=ArtifactSubjectType.SOURCE_VERSION.value,
                        subject_id=version.id,
                        kind=kind.value,
                        storage_path=relative_path,
                        sha256=digest,
                        media_type=content_type,
                        size_bytes=len(content),
                        parser_name="draftcheck.sources.public_fetch.raw",
                        parser_version="v0",
                        metadata_json={
                            "source_id": str(source.id),
                            "final_url": final_url,
                            "raw_sha256": digest,
                            **dict(metadata or {}),
                        },
                    )
                    session.add(existing)
                    session.flush()
                manifest = dict(version.storage_manifest_json or {})
                artifact_ids = manifest.get("artifact_ids", [])
                normalized_ids = [str(value) for value in artifact_ids] if isinstance(artifact_ids, list) else []
                if str(existing.id) not in normalized_ids:
                    normalized_ids.append(str(existing.id))
                    manifest["artifact_ids"] = normalized_ids
                    version.storage_manifest_json = manifest
                return {
                    "id": str(existing.id),
                    "kind": existing.kind,
                    "storage_path": existing.storage_path,
                    "sha256": existing.sha256,
                    "size_bytes": existing.size_bytes or 0,
                }

    def _parse_repair_candidates(
        self,
        *,
        local_government: str | None,
        source_type: str | None,
        title_contains: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        with self._session_factory() as session:
            statement = select(DbSource).order_by(DbSource.authority, DbSource.title)
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            if source_type:
                statement = statement.where(DbSource.source_type == source_type)
            normalized_title_filter = title_contains.strip().casefold() if title_contains else None
            candidates: list[dict[str, object]] = []
            for source in session.scalars(statement).all():
                if len(candidates) >= limit:
                    break
                if normalized_title_filter and normalized_title_filter not in source.title.casefold():
                    continue
                version = self._latest_version(session, source)
                fetch_log = self._latest_fetch_log(session, source)
                if version is None:
                    continue
                domain_version = self._source_version(version)
                chunk_count = int(
                    session.scalar(
                        select(func.count()).select_from(DbSourceChunk).where(
                            DbSourceChunk.source_version_id == version.id,
                        )
                    )
                    or 0
                )
                citation_count = int(
                    session.scalar(
                        select(func.count()).select_from(DbSourceCitation).where(
                            DbSourceCitation.source_version_id == version.id,
                        )
                    )
                    or 0
                )
                parse_quality = _version_parse_quality(version=version, fetch_log=fetch_log)
                metadata_low_signal = _parse_quality_requires_review(parse_quality)
                low_signal = (
                    not domain_version.metadata_only
                    and source.source_type != "scheme_map"
                    and (
                        metadata_low_signal
                        or _count_signal_requires_review(
                            chunk_count=chunk_count,
                            citation_count=citation_count,
                            parse_quality=parse_quality,
                        )
                    )
                )
                artifact_rows = session.scalars(
                    select(DbArtifact).where(DbArtifact.subject_id == version.id)
                ).all()
                repair_profile = _parse_repair_profile(
                    source=source,
                    version=domain_version,
                    chunk_count=chunk_count,
                    citation_count=citation_count,
                    parse_quality=parse_quality,
                    artifact_rows=artifact_rows,
                    low_signal=low_signal,
                )
                if repair_profile["status"] != "repair_ready":
                    continue
                raw_artifact = _preferred_raw_repair_artifact(artifact_rows)
                if raw_artifact is None:
                    continue
                current_text_char_count = _parse_quality_text_char_count(parse_quality)
                if current_text_char_count is None:
                    current_text_char_count = int(
                        session.scalar(
                            select(func.coalesce(func.sum(func.length(DbSourceChunk.text)), 0)).where(
                                DbSourceChunk.source_version_id == version.id,
                            )
                        )
                        or 0
                    )
                candidates.append(
                    {
                        "source_id": str(source.id),
                        "source_version_id": str(version.id),
                        "title": source.title,
                        "authority": source.authority,
                        "jurisdiction": source.jurisdiction,
                        "local_government": source.local_government,
                        "source_type": source.source_type,
                        "canonical_url": source.canonical_url,
                        "access_type": source.access_type,
                        "licence_notes": source.metadata_json.get("licence_notes"),
                        "source_metadata": dict(source.metadata_json or {}),
                        "current_text_char_count": current_text_char_count,
                        "raw_artifact_id": str(raw_artifact.id),
                        "raw_kind": raw_artifact.kind,
                        "raw_storage_path": raw_artifact.storage_path,
                        "raw_media_type": raw_artifact.media_type,
                    }
                )
            return candidates

    def _pending_fetch_candidates(
        self,
        *,
        local_government: str | None,
        source_type: str | None,
        title_contains: str | None,
        readiness: str | None,
        max_declared_size_mb: float | None,
        limit: int,
        force: bool,
    ) -> list[dict[str, object]]:
        with self._session_factory() as session:
            statement = select(DbSource).where(DbSource.canonical_url.is_not(None)).order_by(
                DbSource.authority,
                DbSource.title,
            )
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            if source_type:
                statement = statement.where(DbSource.source_type == source_type)
            normalized_title_filter = title_contains.strip().casefold() if title_contains else None
            candidates: list[dict[str, object]] = []
            for source in session.scalars(statement).all():
                if normalized_title_filter and normalized_title_filter not in source.title.casefold():
                    continue
                declared_size_mb = _declared_size_mb(source.title)
                if (
                    max_declared_size_mb is not None
                    and declared_size_mb is not None
                    and declared_size_mb > max_declared_size_mb
                ):
                    continue
                latest = self._latest_version(session, source)
                latest_fetch = self._latest_fetch_log(session, source)
                latest_domain = self._source_version(latest) if latest else None
                if readiness:
                    if latest is None or latest_domain is None:
                        continue
                    current_readiness = self._source_version_readiness_for_row(
                        session,
                        source=source,
                        version=latest,
                        fetch_log=latest_fetch,
                        domain_version=latest_domain,
                    )
                    if current_readiness != readiness:
                        continue
                if not force:
                    already_fetched = latest_domain is not None and not latest_domain.metadata_only
                    latest_succeeded = latest_fetch is not None and latest_fetch.status == "success"
                    if already_fetched or latest_succeeded:
                        continue
                candidates.append(
                    {
                        "source_id": str(source.id),
                        "source_version_id": str(latest.id) if latest else None,
                        "title": source.title,
                        "jurisdiction": source.jurisdiction,
                        "authority": source.authority,
                        "local_government": source.local_government,
                        "source_type": source.source_type,
                        "canonical_url": source.canonical_url,
                        "access_type": source.access_type,
                        "licence_notes": (source.metadata_json or {}).get("licence_notes"),
                        "metadata": dict(source.metadata_json or {}),
                    }
                )
                if len(candidates) >= limit:
                    break
            return candidates

    def _source_version_readiness_for_row(
        self,
        session: Session,
        *,
        source: DbSource,
        version: DbSourceVersion,
        fetch_log: DbSourceFetchLog | None,
        domain_version: SourceVersion,
    ) -> str:
        chunk_count = int(
            session.scalar(
                select(func.count()).select_from(DbSourceChunk).where(
                    DbSourceChunk.source_version_id == version.id,
                )
            )
            or 0
        )
        citation_count = int(
            session.scalar(
                select(func.count()).select_from(DbSourceCitation).where(
                    DbSourceCitation.source_version_id == version.id,
                )
            )
            or 0
        )
        parse_quality = _version_parse_quality(version=version, fetch_log=fetch_log)
        low_signal = (
            not domain_version.metadata_only
            and source.source_type != "scheme_map"
            and (
                _parse_quality_requires_review(parse_quality)
                or _count_signal_requires_review(
                    chunk_count=chunk_count,
                    citation_count=citation_count,
                    parse_quality=parse_quality,
                )
            )
        )
        return _quality_readiness(
            version=domain_version,
            chunk_count=chunk_count,
            citation_count=citation_count,
            low_signal=low_signal,
        )

    def _child_discovery_candidates(
        self,
        *,
        local_government: str | None,
    ) -> list[dict[str, object]]:
        with self._session_factory() as session:
            statement = select(DbSource).where(DbSource.canonical_url.is_not(None)).order_by(
                DbSource.authority,
                DbSource.title,
            )
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            parents: list[dict[str, object]] = []
            for source in session.scalars(statement).all():
                latest = self._latest_version(session, source)
                if latest is None:
                    continue
                latest_domain = self._source_version(latest)
                if latest_domain.metadata_only:
                    continue
                candidate_links = _candidate_links_from_metadata(latest.metadata_json)
                if not candidate_links:
                    chunks = session.scalars(
                        select(DbSourceChunk)
                        .where(DbSourceChunk.source_version_id == latest.id)
                        .order_by(DbSourceChunk.chunk_index)
                    ).all()
                    candidate_links = _candidate_links_from_text(
                        "\n".join(chunk.text for chunk in chunks)
                    )
                if not candidate_links:
                    continue
                parents.append(
                    {
                        "source_id": source.id,
                        "source_version_id": latest.id,
                        "title": source.title,
                        "jurisdiction": source.jurisdiction,
                        "authority": source.authority,
                        "local_government": source.local_government,
                        "source_type": source.source_type,
                        "canonical_url": source.canonical_url,
                        "access_type": source.access_type,
                        "candidate_links": candidate_links,
                    }
                )
            return parents

    def _already_has_fetched_source(self, canonical_url: str) -> bool:
        with self._session_factory() as session:
            source = session.scalar(
                select(DbSource).where(DbSource.canonical_url == canonical_url).limit(1)
            )
            if source is None:
                return False
            latest = self._latest_version(session, source)
            if latest is None:
                return False
            return not self._source_version(latest).metadata_only

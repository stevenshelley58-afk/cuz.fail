"""Module-level helper functions shared by the source-store mixins."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from hashlib import sha256
import json
import re
from typing import Any
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid5

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
    infer_source_type,
)
from draftcheck.domain.sources.library import _safe_quote
from draftcheck.domain.sources.models import (
    ArtifactKind,
    LicenceStatus,
    SourceReviewStatus,
    SourceVersion,
)


# ---- artifact payload, id, and status coercion helpers ----
def _artifact_payload(
    *,
    title: str,
    content: str,
    uri: str | None,
    publisher: str | None,
    licence_status: LicenceStatus,
    metadata_only: bool,
) -> bytes:
    if content and not metadata_only:
        return content.encode("utf-8")
    return json.dumps(
        {
            "title": title,
            "uri": uri,
            "publisher": publisher,
            "licence_status": licence_status.value,
            "metadata_only": True,
        },
        sort_keys=True,
    ).encode("utf-8")


def _source_uuid(source_id: str | None, *, title: str, canonical_url: str | None) -> UUID:
    if source_id:
        try:
            return UUID(source_id)
        except ValueError:
            return uuid5(NAMESPACE_URL, f"draftcheck.source:{source_id}")
    return uuid5(NAMESPACE_URL, f"draftcheck.source:{title}|{canonical_url or ''}")


def _uuid_from_string(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a UUID for durable source review") from exc


def _licence_status(value: str) -> LicenceStatus:
    try:
        return LicenceStatus(value)
    except ValueError:
        return LicenceStatus.UNKNOWN


def _review_status(value: str) -> SourceReviewStatus:
    try:
        return SourceReviewStatus(value)
    except ValueError:
        return SourceReviewStatus.PENDING_REVIEW


# ---- link discovery helpers ----
_URL_IN_TEXT_RE = re.compile(r"https?://[^\s<>)\"']+")


def _candidate_links_from_metadata(metadata: Mapping[str, object]) -> tuple[CandidateSourceLink, ...]:
    raw_links = metadata.get("candidate_links")
    if not isinstance(raw_links, list):
        return ()
    links: list[CandidateSourceLink] = []
    seen: set[str] = set()
    for raw_link in raw_links:
        if not isinstance(raw_link, Mapping):
            continue
        url = _optional_str(raw_link.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        label = _optional_str(raw_link.get("label")) or _title_from_url(url)
        source_type = _optional_str(raw_link.get("source_type")) or infer_source_type(url, label)
        links.append(CandidateSourceLink(url=url, label=label, source_type=source_type))
    return tuple(links)


def _candidate_links_from_text(text: str) -> tuple[CandidateSourceLink, ...]:
    links: list[CandidateSourceLink] = []
    seen: set[str] = set()
    in_candidate_block = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if in_candidate_block:
                in_candidate_block = False
            continue
        if line.lower().startswith("candidate public source links"):
            in_candidate_block = True
            continue
        if not in_candidate_block and "http" not in line.lower():
            continue
        match = _URL_IN_TEXT_RE.search(line)
        if match is None:
            continue
        url = match.group(0).rstrip(".,;]")
        if url in seen or not _is_public_http_url(url):
            continue
        label = line[: match.start()].strip().rstrip(":").strip() or _title_from_url(url)
        if not _looks_like_discovered_source(url, label):
            continue
        seen.add(url)
        links.append(
            CandidateSourceLink(
                url=url,
                label=label,
                source_type=infer_source_type(url, label),
            )
        )
    return tuple(links)


def _looks_like_discovered_source(url: str, label: str) -> bool:
    haystack = f"{url} {label}".lower().replace("_", "-")
    if any(
        term in haystack
        for term in (
            "local-planning",
            "planning-scheme",
            "scheme-text",
            "schemetext",
            "structure-plan",
            "local-development-plan",
            "local development plan",
            "planning-strategy",
            "local planning strategy",
            "local-planning-polic",
            "local planning polic",
            "planning advice",
            "planning-advice",
            "r-code",
            "rcode",
            "residential-design-code",
        )
    ):
        return True
    if _has_lpp_token(haystack):
        return True
    if _has_tps_token(haystack) and ("map" in haystack or "scheme" in haystack):
        return True
    return bool(
        (haystack.endswith((".pdf", ".doc", ".docx")) or ".pdf" in haystack)
        and any(term in haystack for term in ("planning", "scheme", "map", "r-code", "rcode"))
    )


def _has_tps_token(haystack: str) -> bool:
    normalized = (
        haystack.replace("/", "-")
        .replace(".", "-")
        .replace("(", "-")
        .replace(")", "-")
        .replace("%20", "-")
    )
    return any(
        token == "tps" or (token.startswith("tps") and token[3:].isdigit())
        for token in normalized.split("-")
    )


def _has_lpp_token(haystack: str) -> bool:
    normalized = (
        haystack.replace("/", "-")
        .replace(".", "-")
        .replace("(", "-")
        .replace(")", "-")
        .replace("%20", "-")
    )
    return any(
        token == "lpp" or (token.startswith("lpp") and token[3:].isdigit())
        for token in normalized.split("-")
    )


def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return False
    lowered = url.lower()
    return not any(
        restricted in lowered
        for restricted in ("login", "signin", "password", "private", "cart", "checkout", "captcha")
    )


def _authority_for_discovered_link(url: str, *, fallback: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("cockburn.wa.gov.au"):
        return "City of Cockburn"
    if host.endswith("wa.gov.au") or host.endswith("planning.wa.gov.au"):
        return "Department of Planning, Lands and Heritage"
    return fallback


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path_title = parsed.path.rstrip("/").split("/")[-1]
    if not path_title:
        return url
    for suffix in (".aspx", ".html", ".htm", ".pdf", ".docx", ".doc"):
        if path_title.lower().endswith(suffix):
            path_title = path_title[: -len(suffix)]
            break
    return path_title.replace("-", " ").replace("_", " ").replace("%20", " ").strip() or url


# ---- manifest parsing helpers ----
def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_manifest_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    normalized = str(value).strip()
    if not normalized:
        return None
    if len(normalized) == 10:
        parsed_date = date.fromisoformat(normalized)
        return datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=UTC)
    parsed_datetime = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    return parsed_datetime if parsed_datetime.tzinfo else parsed_datetime.replace(tzinfo=UTC)


def _manifest_fetch_status(entry: Mapping[str, Any], metadata_only: bool) -> str:
    if not bool(entry.get("scrape_allowed", False)):
        return "blocked"
    if metadata_only:
        return "pending_fetch"
    return "pending_review"


# ---- ingestion-status and parse-quality helpers ----
def _pending_action(
    version: DbSourceVersion | None,
    fetch_log: DbSourceFetchLog | None,
) -> str:
    if version is None:
        return "record_source_version"
    review_status = _review_status(version.review_status)
    if fetch_log is not None and fetch_log.status == "pending_fetch":
        return "lawful_fetch"
    if review_status is SourceReviewStatus.PENDING_REVIEW:
        return "source_review"
    if review_status is SourceReviewStatus.APPROVED:
        return "ready_for_rule_extraction"
    return "review_follow_up"


def _increment_nested_count(counts: dict[str, Any], key: str, value: str) -> None:
    nested = counts.get(key)
    if not isinstance(nested, dict):
        nested = {}
        counts[key] = nested
    nested[value] = int(nested.get(value, 0)) + 1


def _quality_item_without_version(
    *,
    source: DbSource,
    fetch_log: DbSourceFetchLog | None,
) -> dict[str, object]:
    return {
        "source_id": str(source.id),
        "source_version_id": None,
        "title": source.title,
        "authority": source.authority,
        "local_government": source.local_government,
        "source_type": source.source_type,
        "canonical_url": source.canonical_url,
        "licence_status": None,
        "review_status": None,
        "metadata_only": False,
        "chunk_count": 0,
        "citation_count": 0,
        "readiness": "missing_source_version",
        "issue_codes": ["missing_source_version"],
        "recommended_action": "repair_source_version",
        "priority": "critical",
        "can_support_search": False,
        "latest_fetch": (
            {
                "status": fetch_log.status,
                "fetch_kind": fetch_log.fetch_kind,
                "requested_at": fetch_log.requested_at.isoformat(),
            }
            if fetch_log is not None
            else None
        ),
    }


def _quality_readiness(
    *,
    version: SourceVersion,
    chunk_count: int,
    citation_count: int,
    low_signal: bool,
) -> str:
    if version.can_support_citable_retrieval and chunk_count > 0 and citation_count > 0:
        return "citable_search_ready"
    if version.metadata_only:
        return "pending_lawful_fetch"
    if chunk_count == 0 or citation_count == 0:
        return "parse_or_citation_repair_required"
    if low_signal:
        return "parse_quality_review_required"
    if version.review_status is SourceReviewStatus.PENDING_REVIEW:
        return "source_review_ready"
    if version.review_status is SourceReviewStatus.REJECTED:
        return "source_rejected"
    if version.review_status is SourceReviewStatus.STALE:
        return "source_refresh_required"
    if not version.licence_status.can_support_citation:
        return "licence_review_required"
    return "review_follow_up"


def _parse_quality_metadata(metadata: Mapping[str, object]) -> dict[str, object] | None:
    value = metadata.get("parse_quality")
    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _version_parse_quality(
    *,
    version: DbSourceVersion,
    fetch_log: DbSourceFetchLog | None,
) -> dict[str, object] | None:
    version_quality = _parse_quality_metadata(version.metadata_json)
    if version_quality is not None:
        return version_quality
    if fetch_log is None or fetch_log.source_version_id != version.id:
        return None
    return _parse_quality_metadata(fetch_log.metadata_json)


def _parse_quality_requires_review(parse_quality: Mapping[str, object] | None) -> bool:
    if parse_quality is None:
        return False
    return str(parse_quality.get("status") or "") in {
        "low_signal_review",
        "no_parseable_text",
        "partial_ocr_review",
    }


def _count_signal_requires_review(
    *,
    chunk_count: int,
    citation_count: int,
    parse_quality: Mapping[str, object] | None,
) -> bool:
    if chunk_count == 0 or citation_count == 0:
        return True
    if chunk_count > 1 and citation_count > 1:
        return False
    if parse_quality is None:
        return True
    if str(parse_quality.get("status") or "") != "text_layer_extracted":
        return True
    text_char_count = _parse_quality_text_char_count(parse_quality) or 0
    text_coverage_ratio = _optional_float(parse_quality.get("text_coverage_ratio")) or 0.0
    return text_char_count < 1000 or text_coverage_ratio < 0.5


# ---- parse-repair helpers ----
_RAW_SOURCE_ARTIFACT_KINDS = {
    ArtifactKind.RAW_PDF.value,
    ArtifactKind.RAW_HTML.value,
    ArtifactKind.RAW_DOCX.value,
}
_REPAIRED_TEXT_ARTIFACT_KINDS = {
    ArtifactKind.OCR_TEXT.value,
    ArtifactKind.PARSED_TEXT.value,
}


def _parse_repair_profile(
    *,
    source: DbSource,
    version: SourceVersion,
    chunk_count: int,
    citation_count: int,
    parse_quality: Mapping[str, object] | None,
    artifact_rows: Sequence[DbArtifact],
    low_signal: bool,
) -> dict[str, object]:
    raw_artifacts = [
        artifact for artifact in artifact_rows if artifact.kind in _RAW_SOURCE_ARTIFACT_KINDS
    ]
    repair_artifacts = [
        artifact
        for artifact in artifact_rows
        if artifact.kind in _REPAIRED_TEXT_ARTIFACT_KINDS
    ]
    reason_codes = _parse_repair_reason_codes(
        chunk_count=chunk_count,
        citation_count=citation_count,
        parse_quality=parse_quality,
        low_signal=low_signal,
    )
    if version.metadata_only:
        status_value = "pending_lawful_fetch"
        next_action = "lawfully fetch the public source before parse repair"
    elif source.source_type == "scheme_map":
        status_value = "not_required"
        next_action = "review map evidence separately; text extraction is not authoritative for measurements"
    elif not low_signal:
        status_value = "not_required"
        next_action = "automated source review"
    elif repair_artifacts:
        status_value = "repaired_text_available"
        next_action = "review repaired text, then rechunk and re-cite before source approval"
    elif raw_artifacts:
        status_value = "repair_ready"
        next_action = _parse_repair_next_action(raw_artifacts)
    else:
        status_value = "raw_source_missing"
        next_action = "refetch with raw artifact persistence before OCR or parser repair"
    return {
        "required": status_value
        in {"repair_ready", "raw_source_missing", "repaired_text_available"},
        "status": status_value,
        "next_action": next_action,
        "reason_codes": reason_codes,
        "raw_artifact_count": len(raw_artifacts),
        "raw_artifact_kinds": sorted({artifact.kind for artifact in raw_artifacts}),
        "raw_artifacts": [_artifact_repair_reference(artifact) for artifact in raw_artifacts],
        "repair_artifact_count": len(repair_artifacts),
        "repair_artifact_kinds": sorted({artifact.kind for artifact in repair_artifacts}),
        "repair_artifacts": [
            _artifact_repair_reference(artifact) for artifact in repair_artifacts
        ],
    }


def _parse_repair_next_action(raw_artifacts: Sequence[DbArtifact]) -> str:
    kinds = {artifact.kind for artifact in raw_artifacts}
    if ArtifactKind.RAW_PDF.value in kinds:
        return "run OCR or PDF text-layer repair from the stored raw PDF"
    if ArtifactKind.RAW_DOCX.value in kinds:
        return "rerun DOCX parser from the stored raw document"
    if ArtifactKind.RAW_HTML.value in kinds:
        return "rerun HTML parser from the stored raw page"
    return "rerun parser from the stored raw source artifact"


def _parse_repair_reason_codes(
    *,
    chunk_count: int,
    citation_count: int,
    parse_quality: Mapping[str, object] | None,
    low_signal: bool,
) -> list[str]:
    reason_codes: list[str] = []
    if chunk_count == 0:
        reason_codes.append("no_chunks")
    elif chunk_count <= 1:
        reason_codes.append("single_chunk")
    if citation_count == 0:
        reason_codes.append("no_citations")
    elif citation_count <= 1:
        reason_codes.append("single_citation")
    if parse_quality is not None:
        status_value = str(parse_quality.get("status") or "").strip()
        if status_value:
            reason_codes.append(f"parse_quality_{status_value}")
        text_coverage_ratio = _optional_float(parse_quality.get("text_coverage_ratio"))
        if text_coverage_ratio is not None and text_coverage_ratio < 0.2:
            reason_codes.append("low_text_coverage")
        page_count = _optional_int(parse_quality.get("page_count"))
        pages_with_text = _optional_int(parse_quality.get("pages_with_text"))
        if page_count and pages_with_text is not None and pages_with_text / page_count < 0.2:
            reason_codes.append("low_page_text_coverage")
    if low_signal and not reason_codes:
        reason_codes.append("low_signal_parse_review")
    return list(dict.fromkeys(reason_codes))


def _artifact_repair_reference(artifact: DbArtifact) -> dict[str, object]:
    return {
        "id": str(artifact.id),
        "kind": artifact.kind,
        "storage_path": artifact.storage_path,
        "sha256": artifact.sha256,
        "media_type": artifact.media_type,
        "size_bytes": artifact.size_bytes or 0,
        "parser_name": artifact.parser_name,
        "parser_version": artifact.parser_version,
    }


def _preferred_raw_repair_artifact(artifact_rows: Sequence[DbArtifact]) -> DbArtifact | None:
    priority = {
        ArtifactKind.RAW_PDF.value: 0,
        ArtifactKind.RAW_DOCX.value: 1,
        ArtifactKind.RAW_HTML.value: 2,
    }
    raw_artifacts = [
        artifact for artifact in artifact_rows if artifact.kind in _RAW_SOURCE_ARTIFACT_KINDS
    ]
    if not raw_artifacts:
        return None
    return sorted(
        raw_artifacts,
        key=lambda artifact: (
            priority.get(artifact.kind, 9),
            -(artifact.size_bytes or 0),
            artifact.created_at,
        ),
    )[0]


def _parse_quality_text_char_count(
    parse_quality: Mapping[str, object] | None,
) -> int | None:
    if parse_quality is None:
        return None
    return _optional_int(parse_quality.get("text_char_count"))


# ---- numeric coercion and sampling helpers ----
def _optional_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sample_ordinals(total: int, limit: int) -> list[int]:
    if total <= 0:
        return []
    if limit <= 0 or total <= limit:
        return list(range(1, total + 1))
    if limit == 1:
        return [1]
    ordinals = {1, total}
    if limit > 2:
        step = (total - 1) / (limit - 1)
        ordinals.update(1 + round(step * index) for index in range(limit))
    return sorted(ordinal for ordinal in ordinals if 1 <= ordinal <= total)[:limit]


# ---- review-packet helpers ----
def _review_packet_source(source: DbSource) -> dict[str, object]:
    return {
        "id": str(source.id),
        "title": source.title,
        "authority": source.authority,
        "jurisdiction": source.jurisdiction,
        "local_government": source.local_government,
        "source_type": source.source_type,
        "canonical_url": source.canonical_url,
        "access_type": source.access_type,
        "status": source.status,
        "metadata": source.metadata_json,
    }


def _review_packet_version(version: SourceVersion) -> dict[str, object]:
    return {
        "id": version.id,
        "source_id": version.source_id,
        "version_label": version.version_label,
        "sha256": version.sha256,
        "storage_path": version.storage_path,
        "licence_status": version.licence_status.value,
        "review_status": version.review_status.value,
        "fetched_at": version.fetched_at.isoformat(),
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "effective_from": version.effective_from.isoformat() if version.effective_from else None,
        "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        "superseded_by_version_id": version.superseded_by_version_id,
        "artifact_ids": list(version.artifact_ids),
        "metadata_only": version.metadata_only,
        "can_support_citable_retrieval": version.can_support_citable_retrieval,
    }


def _review_packet_fetch_log(fetch_log: DbSourceFetchLog | None) -> dict[str, object] | None:
    if fetch_log is None:
        return None
    return {
        "id": str(fetch_log.id),
        "source_version_id": str(fetch_log.source_version_id) if fetch_log.source_version_id else None,
        "fetch_kind": fetch_log.fetch_kind,
        "status": fetch_log.status,
        "requested_at": fetch_log.requested_at.isoformat(),
        "completed_at": fetch_log.completed_at.isoformat() if fetch_log.completed_at else None,
        "error": fetch_log.error,
        "metadata": fetch_log.metadata_json,
    }


def _review_packet_artifact(artifact: DbArtifact) -> dict[str, object]:
    return {
        "id": str(artifact.id),
        "subject_type": artifact.subject_type,
        "subject_id": str(artifact.subject_id) if artifact.subject_id else None,
        "kind": artifact.kind,
        "storage_path": artifact.storage_path,
        "sha256": artifact.sha256,
        "media_type": artifact.media_type,
        "size_bytes": artifact.size_bytes,
        "parser_name": artifact.parser_name,
        "parser_version": artifact.parser_version,
        "metadata": artifact.metadata_json,
    }


def _review_packet_chunk_sample(
    *,
    chunk: DbSourceChunk,
    citation: DbSourceCitation | None,
    source: DbSource,
    version: DbSourceVersion,
    sample_chars: int,
) -> dict[str, object]:
    text = _truncate_review_text(chunk.text, sample_chars)
    return {
        "id": str(chunk.id),
        "source_id": str(source.id),
        "source_version_id": str(version.id),
        "ordinal": chunk.chunk_index,
        "heading": chunk.heading,
        "section_ref": chunk.section_ref,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "token_count": chunk.token_count,
        "text": text,
        "text_truncated": len(chunk.text) > len(text),
        "text_sha256": sha256(chunk.text.encode("utf-8")).hexdigest(),
        "citation": (
            _review_packet_citation(citation, chunk=chunk, source=source)
            if citation is not None
            else None
        ),
    }


def _review_packet_citation(
    citation: DbSourceCitation,
    *,
    chunk: DbSourceChunk,
    source: DbSource,
) -> dict[str, object]:
    return {
        "id": str(citation.id),
        "chunk_id": str(chunk.id),
        "locator": citation.section_ref or f"chunk {chunk.chunk_index}",
        "page_number": citation.page_number,
        "quote": citation.quote or _safe_quote(chunk.text),
        "uri": source.canonical_url,
        "citation_json": citation.citation_json,
    }


def _truncate_review_text(text: str, max_chars: int) -> str:
    normalized_limit = max(max_chars, 0)
    if len(text) <= normalized_limit:
        return text
    return text[:normalized_limit].rstrip()


def _packet_recommended_action(readiness: str) -> str:
    if readiness == "pending_lawful_fetch":
        return "lawful_fetch"
    if readiness in {"parse_or_citation_repair_required", "parse_quality_review_required"}:
        return "repair_parse_or_citations"
    if readiness == "source_review_ready":
        return "source_review"
    if readiness == "source_rejected":
        return "replace_or_refresh_source"
    if readiness == "source_refresh_required":
        return "refresh_source"
    if readiness == "licence_review_required":
        return "licence_review"
    if readiness == "citable_search_ready":
        return "rule_extraction_review"
    return "review_follow_up"


# ---- quality-gate and sort helpers ----
def _source_quality_gates(counts: Mapping[str, object]) -> list[dict[str, object]]:
    pending_fetch = _int_count(counts, "pending_fetch_items")
    pending_review = _int_count(counts, "pending_review_versions")
    low_signal = _int_count(counts, "low_signal_versions")
    parse_repair_ready = _int_count(counts, "parse_repair_ready_versions")
    parse_repair_missing_raw = _int_count(
        counts,
        "parse_repair_missing_raw_artifact_versions",
    )
    approved_citable = _int_count(counts, "approved_citable_versions")
    return [
        {
            "gate": "lawful_fetch_complete",
            "status": "blocked" if pending_fetch else "passed",
            "blocking_count": pending_fetch,
        },
        {
            "gate": "source_review_complete",
            "status": "blocked" if pending_review else "passed",
            "blocking_count": pending_review,
        },
        {
            "gate": "parse_quality_review",
            "status": "needs_review" if low_signal else "passed",
            "blocking_count": low_signal,
        },
        {
            "gate": "parse_repair_inputs",
            "status": (
                "blocked"
                if parse_repair_missing_raw
                else "ready"
                if parse_repair_ready
                else "not_required"
            ),
            "blocking_count": parse_repair_missing_raw,
            "ready_count": parse_repair_ready,
        },
        {
            "gate": "citable_search_ready",
            "status": "blocked" if approved_citable == 0 else "passed",
            "blocking_count": 0 if approved_citable else 1,
        },
        {
            "gate": "deterministic_rules_promoted",
            "status": "blocked",
            "blocking_count": 1,
        },
    ]


def _int_count(counts: Mapping[str, object], key: str) -> int:
    value = counts.get(key)
    return value if isinstance(value, int) else 0


def _quality_sort_key(item: Mapping[str, object]) -> tuple[int, str, str]:
    readiness_rank = {
        "pending_lawful_fetch": 0,
        "parse_or_citation_repair_required": 1,
        "parse_quality_review_required": 2,
        "source_review_ready": 3,
        "licence_review_required": 4,
        "source_refresh_required": 5,
        "source_rejected": 6,
        "citable_search_ready": 7,
    }
    readiness = str(item.get("readiness") or "")
    source_type = str(item.get("source_type") or "")
    title = str(item.get("title") or "")
    return (readiness_rank.get(readiness, 9), source_type, title)


# ---- review worklist and misc helpers ----
def _review_issue_codes(
    *,
    source: DbSource,
    version: SourceVersion,
    chunk_count: int,
    citation_count: int,
) -> list[str]:
    issues: list[str] = []
    if version.metadata_only:
        issues.append("metadata_only_pending_fetch")
    if version.review_status is SourceReviewStatus.PENDING_REVIEW:
        issues.append("source_version_pending_review")
    if version.licence_status is LicenceStatus.PENDING_REVIEW:
        issues.append("licence_pending_review")
    if not version.metadata_only and chunk_count == 0:
        issues.append("no_chunks")
    if not version.metadata_only and citation_count == 0:
        issues.append("no_citations")
    if source.source_type == "scheme_map":
        issues.append("scheme_map_text_only_no_measurement")
    declared_size_mb = _declared_size_mb(source.title)
    if declared_size_mb is not None and declared_size_mb >= 25:
        issues.append("large_document_controlled_fetch_or_review")
    if version.review_status is SourceReviewStatus.REJECTED:
        issues.append("source_version_rejected")
    return issues


def _raw_artifact_kind(*, content_type: str, final_url: str) -> ArtifactKind:
    haystack = f"{content_type} {final_url}".lower()
    if "pdf" in haystack:
        return ArtifactKind.RAW_PDF
    if "wordprocessingml" in haystack or "msword" in haystack or haystack.endswith(".docx"):
        return ArtifactKind.RAW_DOCX
    if "html" in haystack or haystack.endswith((".html", ".htm", "/")):
        return ArtifactKind.RAW_HTML
    return ArtifactKind.CANONICAL_TEXT


def _review_recommended_action(
    *,
    metadata_only: bool,
    review_status: SourceReviewStatus,
    chunk_count: int,
    citation_count: int,
) -> str:
    if metadata_only:
        return "lawful_fetch"
    if chunk_count == 0 or citation_count == 0:
        return "repair_parse_or_citations"
    if review_status is SourceReviewStatus.PENDING_REVIEW:
        return "source_review"
    if review_status is SourceReviewStatus.REJECTED:
        return "replace_or_refresh_source"
    if review_status is SourceReviewStatus.STALE:
        return "refresh_source"
    return "review_follow_up"


def _review_priority(*, source_type: str, metadata_only: bool, chunk_count: int) -> str:
    if not metadata_only and source_type in {"local_planning_scheme", "local_planning_strategy"}:
        return "critical"
    if not metadata_only and source_type in {
        "local_development_plan",
        "local_planning_policy",
        "planning_guidance",
    }:
        return "high"
    if source_type == "scheme_map":
        return "high" if not metadata_only else "medium"
    if not metadata_only and source_type == "structure_plan":
        return "medium"
    if metadata_only and source_type == "structure_plan":
        return "controlled_fetch"
    if chunk_count == 0:
        return "medium"
    return "normal"


def _review_sort_key(item: Mapping[str, object]) -> tuple[int, str, str]:
    priority_rank = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "normal": 3,
        "controlled_fetch": 4,
    }
    priority = str(item.get("priority") or "normal")
    source_type = str(item.get("source_type") or "")
    title = str(item.get("title") or "")
    return (priority_rank.get(priority, 9), source_type, title)


def _declared_size_mb(title: str) -> float | None:
    match = re.search(r"\((?:PDF,\s*)?([0-9]+(?:\.[0-9]+)?)\s*MB\)", title, flags=re.IGNORECASE)
    if match is None:
        return None
    return float(match.group(1))


def _utc_now() -> datetime:
    return datetime.now(UTC)

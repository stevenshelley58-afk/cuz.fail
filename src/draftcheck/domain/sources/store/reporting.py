"""Reporting operations: ingestion status, review worklist, quality report, review packet."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from draftcheck.db.models import (
    Artifact as DbArtifact,
    Source as DbSource,
    SourceChunk as DbSourceChunk,
    SourceCitation as DbSourceCitation,
)
from draftcheck.domain.sources.models import (
    SourceNotFoundError,
    SourceReviewStatus,
)
from draftcheck.domain.sources.store._helpers import (
    _count_signal_requires_review,
    _declared_size_mb,
    _increment_nested_count,
    _packet_recommended_action,
    _parse_quality_requires_review,
    _parse_repair_profile,
    _pending_action,
    _quality_item_without_version,
    _quality_readiness,
    _quality_sort_key,
    _review_issue_codes,
    _review_packet_artifact,
    _review_packet_chunk_sample,
    _review_packet_fetch_log,
    _review_packet_source,
    _review_packet_version,
    _review_priority,
    _review_recommended_action,
    _review_sort_key,
    _sample_ordinals,
    _source_quality_gates,
    _version_parse_quality,
)

if TYPE_CHECKING:
    from draftcheck.domain.sources.store._base import SourceStoreBase
else:  # pragma: no cover - typing-only base; mixins compose at runtime
    SourceStoreBase = object


class SourceReportingOps(SourceStoreBase):
    """Reporting methods for ``SqlAlchemySourceLibrary``."""

    def ingestion_status(self, *, local_government: str | None = None) -> dict[str, object]:
        with self._session_factory() as session:
            statement = select(DbSource).order_by(DbSource.authority, DbSource.title)
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            sources = session.scalars(statement).all()
            items: list[dict[str, object]] = []
            counts = {
                "sources": len(sources),
                "versions": 0,
                "pending_review_versions": 0,
                "approved_citable_versions": 0,
                "metadata_only_versions": 0,
                "chunks": 0,
                "citations": 0,
                "pending_fetches": 0,
                "review_ready_versions": 0,
                "low_signal_versions": 0,
                "parse_repair_ready_versions": 0,
                "parse_repair_missing_raw_artifact_versions": 0,
                "raw_source_artifact_versions": 0,
                "repaired_text_artifact_versions": 0,
            }
            readiness_counts = {
                "pending_lawful_fetch": 0,
                "parse_or_citation_repair_required": 0,
                "parse_quality_review_required": 0,
                "source_review_ready": 0,
                "licence_review_required": 0,
                "source_refresh_required": 0,
                "source_rejected": 0,
                "citable_search_ready": 0,
                "review_follow_up": 0,
            }
            source_type_counts: Counter[str] = Counter()
            pending_action_counts: Counter[str] = Counter()
            latest_requested_at: datetime | None = None
            latest_successful_at: datetime | None = None
            for source in sources:
                version = self._latest_version(session, source)
                fetch_log = self._latest_fetch_log(session, source)
                chunk_count = 0
                citation_count = 0
                version_payload: dict[str, object] | None = None
                source_type_counts[source.source_type] += 1
                if version is not None:
                    counts["versions"] += 1
                    domain_version = self._source_version(version)
                    if domain_version.review_status is SourceReviewStatus.PENDING_REVIEW:
                        counts["pending_review_versions"] += 1
                    if domain_version.metadata_only:
                        counts["metadata_only_versions"] += 1
                    if domain_version.can_support_citable_retrieval:
                        counts["approved_citable_versions"] += 1
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
                    counts["chunks"] += chunk_count
                    counts["citations"] += citation_count
                    parse_quality = _version_parse_quality(version=version, fetch_log=fetch_log)
                    metadata_low_signal = _parse_quality_requires_review(parse_quality)
                    artifact_rows = session.scalars(
                        select(DbArtifact).where(DbArtifact.subject_id == version.id)
                    ).all()
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
                    repair_profile = _parse_repair_profile(
                        source=source,
                        version=domain_version,
                        chunk_count=chunk_count,
                        citation_count=citation_count,
                        parse_quality=parse_quality,
                        artifact_rows=artifact_rows,
                        low_signal=low_signal,
                    )
                    if low_signal:
                        counts["low_signal_versions"] += 1
                    if repair_profile["raw_artifact_count"]:
                        counts["raw_source_artifact_versions"] += 1
                    if repair_profile["status"] == "repair_ready":
                        counts["parse_repair_ready_versions"] += 1
                    if repair_profile["status"] == "raw_source_missing":
                        counts["parse_repair_missing_raw_artifact_versions"] += 1
                    if repair_profile["repair_artifact_count"]:
                        counts["repaired_text_artifact_versions"] += 1
                    readiness = _quality_readiness(
                        version=domain_version,
                        chunk_count=chunk_count,
                        citation_count=citation_count,
                        low_signal=low_signal,
                    )
                    if readiness in readiness_counts:
                        readiness_counts[readiness] += 1
                    if (
                        not domain_version.metadata_only
                        and not low_signal
                        and chunk_count > 0
                        and citation_count > 0
                    ):
                        counts["review_ready_versions"] += 1
                    version_payload = {
                        "id": str(version.id),
                        "version_label": version.version_label,
                        "licence_status": domain_version.licence_status.value,
                        "review_status": domain_version.review_status.value,
                        "metadata_only": domain_version.metadata_only,
                        "can_support_search": (
                            domain_version.can_support_citable_retrieval
                            and chunk_count > 0
                            and citation_count > 0
                        ),
                    }
                if fetch_log is not None and fetch_log.status == "pending_fetch":
                    counts["pending_fetches"] += 1
                if fetch_log is not None:
                    if latest_requested_at is None or fetch_log.requested_at > latest_requested_at:
                        latest_requested_at = fetch_log.requested_at
                    if fetch_log.status == "success" and (
                        latest_successful_at is None or fetch_log.requested_at > latest_successful_at
                    ):
                        latest_successful_at = fetch_log.requested_at
                pending_action_counts[_pending_action(version, fetch_log)] += 1
                items.append(
                    {
                        "source_id": str(source.id),
                        "title": source.title,
                        "authority": source.authority,
                        "local_government": source.local_government,
                        "source_type": source.source_type,
                        "canonical_url": source.canonical_url,
                        "access_type": source.access_type,
                        "status": source.status,
                        "latest_version": version_payload,
                        "chunk_count": chunk_count,
                        "citation_count": citation_count,
                        "latest_fetch": (
                            {
                                "status": fetch_log.status,
                                "fetch_kind": fetch_log.fetch_kind,
                                "requested_at": fetch_log.requested_at.isoformat(),
                            }
                            if fetch_log is not None
                            else None
                        ),
                        "pending_action": _pending_action(version, fetch_log),
                    }
                )
            return {
                "status": "ingestion_in_progress" if counts["sources"] else "not_started",
                "answer_policy": "cite_or_refuse",
                "local_government": local_government,
                "beta_status": "not_beta_accurate_yet",
                "counts": counts,
                "items": items,
                "blocked_outputs": [
                    "final_compliance_claims",
                    "uncited_regulatory_answers",
                    "unpromoted_measurement_verdicts",
                ],
                "pending": [
                    "lawful source fetch",
                    "automated source validation",
                    "rule extraction review",
                    "deterministic check promotion",
                ],
                "quality_gates": _source_quality_gates(counts),
                "readiness_counts": readiness_counts,
                "source_type_counts": dict(source_type_counts),
                "pending_action_counts": dict(pending_action_counts),
                "latest_fetch_summary": {
                    "requested_at": latest_requested_at.isoformat() if latest_requested_at else None,
                    "successful_at": latest_successful_at.isoformat() if latest_successful_at else None,
                },
            }

    def review_worklist(
        self,
        *,
        local_government: str | None = None,
        source_type: str | None = None,
        include_metadata_only: bool = True,
        limit: int = 100,
    ) -> dict[str, object]:
        with self._session_factory() as session:
            statement = select(DbSource).order_by(DbSource.authority, DbSource.title)
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            if source_type:
                statement = statement.where(DbSource.source_type == source_type)
            items: list[dict[str, object]] = []
            counts = {
                "review_items": 0,
                "fetched_review_items": 0,
                "pending_fetch_items": 0,
                "approved_citable_versions": 0,
                "rejected_versions": 0,
                "chunks": 0,
                "citations": 0,
            }
            for source in session.scalars(statement).all():
                version = self._latest_version(session, source)
                fetch_log = self._latest_fetch_log(session, source)
                if version is None:
                    continue
                domain_version = self._source_version(version)
                if domain_version.can_support_citable_retrieval:
                    counts["approved_citable_versions"] += 1
                    continue
                if domain_version.review_status is SourceReviewStatus.REJECTED:
                    counts["rejected_versions"] += 1
                if domain_version.metadata_only and not include_metadata_only:
                    continue
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
                issue_codes = _review_issue_codes(
                    source=source,
                    version=domain_version,
                    chunk_count=chunk_count,
                    citation_count=citation_count,
                )
                item: dict[str, object] = {
                    "source_id": str(source.id),
                    "source_version_id": str(version.id),
                    "title": source.title,
                    "authority": source.authority,
                    "local_government": source.local_government,
                    "source_type": source.source_type,
                    "canonical_url": source.canonical_url,
                    "licence_status": domain_version.licence_status.value,
                    "review_status": domain_version.review_status.value,
                    "metadata_only": domain_version.metadata_only,
                    "chunk_count": chunk_count,
                    "citation_count": citation_count,
                    "latest_fetch": (
                        {
                            "status": fetch_log.status,
                            "fetch_kind": fetch_log.fetch_kind,
                            "requested_at": fetch_log.requested_at.isoformat(),
                        }
                        if fetch_log is not None
                        else None
                    ),
                    "priority": _review_priority(
                        source_type=source.source_type,
                        metadata_only=domain_version.metadata_only,
                        chunk_count=chunk_count,
                    ),
                    "issue_codes": issue_codes,
                    "recommended_action": _review_recommended_action(
                        metadata_only=domain_version.metadata_only,
                        review_status=domain_version.review_status,
                        chunk_count=chunk_count,
                        citation_count=citation_count,
                    ),
                    "can_support_search": False,
                }
                items.append(item)
                counts["review_items"] += 1
                counts["chunks"] += chunk_count
                counts["citations"] += citation_count
                if domain_version.metadata_only:
                    counts["pending_fetch_items"] += 1
                else:
                    counts["fetched_review_items"] += 1
            items.sort(key=_review_sort_key)
            limited_items = items[: max(limit, 0)]
            return {
                "status": "review_required" if counts["review_items"] else "clear",
                "answer_policy": "cite_or_refuse",
                "local_government": local_government,
                "source_type": source_type,
                "counts": counts,
                "items": limited_items,
                "count": len(limited_items),
                "total": len(items),
                "blocked_until": [
                    "automated source review",
                    "licence verification",
                    "rule extraction review",
                    "deterministic rule promotion",
                ],
            }

    def quality_report(
        self,
        *,
        local_government: str | None = None,
        source_type: str | None = None,
        readiness: str | None = None,
        limit: int = 100,
    ) -> dict[str, object]:
        with self._session_factory() as session:
            statement = select(DbSource).order_by(DbSource.authority, DbSource.title)
            if local_government:
                statement = statement.where(DbSource.local_government == local_government)
            if source_type:
                statement = statement.where(DbSource.source_type == source_type)
            counts: dict[str, Any] = {
                "sources": 0,
                "versions": 0,
                "pending_review_versions": 0,
                "approved_citable_versions": 0,
                "rejected_versions": 0,
                "metadata_only_versions": 0,
                "fetched_review_items": 0,
                "pending_fetch_items": 0,
                "review_ready_versions": 0,
                "low_signal_versions": 0,
                "raw_source_artifact_versions": 0,
                "parse_repair_ready_versions": 0,
                "parse_repair_missing_raw_artifact_versions": 0,
                "repaired_text_artifact_versions": 0,
                "large_controlled_fetch_items": 0,
                "chunks": 0,
                "citations": 0,
                "source_types": {},
            }
            items: list[dict[str, object]] = []
            for source in session.scalars(statement).all():
                counts["sources"] = int(counts["sources"]) + 1
                _increment_nested_count(counts, "source_types", source.source_type)
                version = self._latest_version(session, source)
                fetch_log = self._latest_fetch_log(session, source)
                if version is None:
                    items.append(_quality_item_without_version(source=source, fetch_log=fetch_log))
                    continue
                counts["versions"] = int(counts["versions"]) + 1
                domain_version = self._source_version(version)
                if domain_version.review_status is SourceReviewStatus.PENDING_REVIEW:
                    counts["pending_review_versions"] = int(counts["pending_review_versions"]) + 1
                if domain_version.review_status is SourceReviewStatus.REJECTED:
                    counts["rejected_versions"] = int(counts["rejected_versions"]) + 1
                if domain_version.metadata_only:
                    counts["metadata_only_versions"] = int(counts["metadata_only_versions"]) + 1
                    counts["pending_fetch_items"] = int(counts["pending_fetch_items"]) + 1
                    if _declared_size_mb(source.title) is not None and (_declared_size_mb(source.title) or 0) >= 25:
                        counts["large_controlled_fetch_items"] = int(counts["large_controlled_fetch_items"]) + 1
                else:
                    counts["fetched_review_items"] = int(counts["fetched_review_items"]) + 1
                if domain_version.can_support_citable_retrieval:
                    counts["approved_citable_versions"] = int(counts["approved_citable_versions"]) + 1
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
                artifact_rows = session.scalars(
                    select(DbArtifact).where(DbArtifact.subject_id == version.id)
                ).all()
                counts["chunks"] = int(counts["chunks"]) + chunk_count
                counts["citations"] = int(counts["citations"]) + citation_count
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
                repair_profile = _parse_repair_profile(
                    source=source,
                    version=domain_version,
                    chunk_count=chunk_count,
                    citation_count=citation_count,
                    parse_quality=parse_quality,
                    artifact_rows=artifact_rows,
                    low_signal=low_signal,
                )
                if low_signal:
                    counts["low_signal_versions"] = int(counts["low_signal_versions"]) + 1
                if repair_profile["raw_artifact_count"]:
                    counts["raw_source_artifact_versions"] = (
                        int(counts["raw_source_artifact_versions"]) + 1
                    )
                if repair_profile["status"] == "repair_ready":
                    counts["parse_repair_ready_versions"] = (
                        int(counts["parse_repair_ready_versions"]) + 1
                    )
                if repair_profile["status"] == "raw_source_missing":
                    counts["parse_repair_missing_raw_artifact_versions"] = (
                        int(counts["parse_repair_missing_raw_artifact_versions"]) + 1
                    )
                if repair_profile["repair_artifact_count"]:
                    counts["repaired_text_artifact_versions"] = (
                        int(counts["repaired_text_artifact_versions"]) + 1
                    )
                if (
                    not domain_version.metadata_only
                    and not low_signal
                    and chunk_count > 0
                    and citation_count > 0
                ):
                    counts["review_ready_versions"] = int(counts["review_ready_versions"]) + 1
                issue_codes = _review_issue_codes(
                    source=source,
                    version=domain_version,
                    chunk_count=chunk_count,
                    citation_count=citation_count,
                )
                if low_signal:
                    issue_codes.append("low_signal_parse_review")
                if metadata_low_signal:
                    issue_codes.append("parse_quality_metadata_review")
                item: dict[str, object] = {
                    "source_id": str(source.id),
                    "source_version_id": str(version.id),
                    "title": source.title,
                    "authority": source.authority,
                    "local_government": source.local_government,
                    "source_type": source.source_type,
                    "canonical_url": source.canonical_url,
                    "licence_status": domain_version.licence_status.value,
                    "review_status": domain_version.review_status.value,
                    "metadata_only": domain_version.metadata_only,
                    "chunk_count": chunk_count,
                    "citation_count": citation_count,
                    "readiness": _quality_readiness(
                        version=domain_version,
                        chunk_count=chunk_count,
                        citation_count=citation_count,
                        low_signal=low_signal,
                    ),
                    "parse_quality": parse_quality,
                    "repair_profile": repair_profile,
                    "issue_codes": issue_codes,
                    "recommended_action": _review_recommended_action(
                        metadata_only=domain_version.metadata_only,
                        review_status=domain_version.review_status,
                        chunk_count=chunk_count,
                        citation_count=citation_count,
                    ),
                    "priority": _review_priority(
                        source_type=source.source_type,
                        metadata_only=domain_version.metadata_only,
                        chunk_count=chunk_count,
                    ),
                    "can_support_search": domain_version.can_support_citable_retrieval
                    and chunk_count > 0
                    and citation_count > 0,
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
                items.append(item)
            items.sort(key=_quality_sort_key)
            if readiness:
                items = [item for item in items if item.get("readiness") == readiness]
            limited_items = items[: max(limit, 0)]
            gates = _source_quality_gates(counts)
            return {
                "status": "blocked" if any(gate["status"] == "blocked" for gate in gates) else "review_ready",
                "answer_policy": "cite_or_refuse",
                "beta_status": "not_beta_accurate_yet",
                "local_government": local_government,
                "source_type": source_type,
                "readiness": readiness,
                "counts": counts,
                "quality_gates": gates,
                "items": limited_items,
                "count": len(limited_items),
                "total": len(items),
                "blocked_outputs": [
                    "final_compliance_claims",
                    "uncited_regulatory_answers",
                    "unpromoted_measurement_verdicts",
                ],
            }

    def review_packet(
        self,
        *,
        source_id: str,
        source_version_id: str,
        sample_limit: int = 12,
        sample_chars: int = 4000,
    ) -> dict[str, object]:
        with self._session_factory() as session:
            source = self._get_source_by_id(session, source_id)
            version = self._get_version_by_id(session, source_version_id)
            if version.source_id != source.id:
                raise SourceNotFoundError(f"source version does not belong to source: {source_version_id}")
            domain_version = self._source_version(version)
            fetch_log = self._latest_fetch_log(session, source)
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
            token_count = int(
                session.scalar(
                    select(func.coalesce(func.sum(DbSourceChunk.token_count), 0)).where(
                        DbSourceChunk.source_version_id == version.id,
                    )
                )
                or 0
            )
            artifact_rows = session.scalars(
                select(DbArtifact)
                .where(DbArtifact.subject_id == version.id)
                .order_by(DbArtifact.kind, DbArtifact.created_at)
            ).all()
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
            issue_codes = _review_issue_codes(
                source=source,
                version=domain_version,
                chunk_count=chunk_count,
                citation_count=citation_count,
            )
            if low_signal:
                issue_codes.append("low_signal_parse_review")
            if metadata_low_signal:
                issue_codes.append("parse_quality_metadata_review")
            readiness = _quality_readiness(
                version=domain_version,
                chunk_count=chunk_count,
                citation_count=citation_count,
                low_signal=low_signal,
            )
            sample_ordinals = _sample_ordinals(chunk_count, sample_limit)
            sample_rows: list[tuple[DbSourceChunk, DbSourceCitation | None]] = []
            if sample_ordinals:
                sample_statement = (
                    select(DbSourceChunk, DbSourceCitation)
                    .outerjoin(DbSourceCitation, DbSourceCitation.source_chunk_id == DbSourceChunk.id)
                    .where(
                        DbSourceChunk.source_version_id == version.id,
                        DbSourceChunk.chunk_index.in_(sample_ordinals),
                    )
                    .order_by(DbSourceChunk.chunk_index)
                )
                sample_rows = [
                    (chunk, citation)
                    for chunk, citation in session.execute(sample_statement).all()
                ]
            can_support_search = (
                domain_version.can_support_citable_retrieval
                and chunk_count > 0
                and citation_count > 0
            )
            return {
                "status": "citable_search_ready" if can_support_search else "review_required",
                "answer_policy": "cite_or_refuse",
                "source": _review_packet_source(source),
                "version": _review_packet_version(domain_version),
                "counts": {
                    "chunks": chunk_count,
                    "citations": citation_count,
                    "artifacts": len(artifact_rows),
                    "tokens": token_count,
                },
                "readiness": readiness,
                "issue_codes": issue_codes,
                "recommended_action": _packet_recommended_action(readiness),
                "parse_quality": parse_quality,
                "repair_profile": _parse_repair_profile(
                    source=source,
                    version=domain_version,
                    chunk_count=chunk_count,
                    citation_count=citation_count,
                    parse_quality=parse_quality,
                    artifact_rows=artifact_rows,
                    low_signal=low_signal,
                ),
                "priority": _review_priority(
                    source_type=source.source_type,
                    metadata_only=domain_version.metadata_only,
                    chunk_count=chunk_count,
                ),
                "can_support_search": can_support_search,
                "latest_fetch": _review_packet_fetch_log(fetch_log),
                "artifacts": [_review_packet_artifact(artifact) for artifact in artifact_rows],
                "chunk_samples": [
                    _review_packet_chunk_sample(
                        chunk=chunk,
                        citation=citation,
                        source=source,
                        version=version,
                        sample_chars=sample_chars,
                    )
                    for chunk, citation in sample_rows
                ],
                "blocked_outputs": [
                    "final_compliance_claims",
                    "uncited_regulatory_answers",
                    "unpromoted_measurement_verdicts",
                ],
                "required_before_beta": [
                    "automated source review",
                    "licence verification",
                    "parse quality review when flagged",
                    "rule extraction review",
                    "deterministic rule promotion",
                ],
            }

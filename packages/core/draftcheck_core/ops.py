from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from draftcheck_core.auth import check_api_auth_ready
from draftcheck_core.database import check_database_persistence_ready
from draftcheck_core.json_utils import from_json
from draftcheck_core.models import (
    AddressFact,
    AddressProfile,
    AuditEvent,
    BackgroundJob,
    CheckResult,
    GoldenEvalCase,
    GoldenEvalRun,
    LocalGovernmentBoundary,
    PlanningLayerFeature,
    ReviewQueueItem,
    RuleRow,
    SourceChunk,
    SourceCitation,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    SpatialDataset,
)
from draftcheck_core.source_governance import SourceGovernanceService
from draftcheck_shared.schemas import OpsDashboardRead


EVAL_TRACKS = [
    "rule_extraction",
    "spatial_resolution",
    "retrieval",
    "drawing_extraction",
    "compliance",
]
REVIEW_QUEUE_NAMES = [
    "source_review",
    "rule_review",
    "spatial_ambiguity_review",
    "drawing_extraction_review",
    "conflict_review",
    "licence_review",
    "eval_failure_review",
]
BACKUP_ACTIONS = {"infra.backup.completed", "backup.completed"}
RESTORE_ACTIONS = {"infra.restore.completed", "restore.completed"}
FAILED_JOB_STATUSES = {"failed", "error", "cancelled"}
OPEN_REVIEW_STATUSES = {"open", "in_progress"}
PRODUCTION_ENVIRONMENTS = {"prod", "production"}


class OpsDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def dashboard(self) -> OpsDashboardRead:
        generated_at = datetime.now(UTC).replace(tzinfo=None)
        sources = self._source_summary()
        rules = self._rule_summary()
        spatial = self._spatial_summary()
        jobs = self._job_summary()
        compliance = self._compliance_summary()
        evals = self._eval_summary()
        review_queues = self._review_queue_summary()
        backups = self._backup_summary()
        issues = self._issues(sources, rules, spatial, jobs, evals, review_queues, backups)
        health_signals = self._health_signals(compliance)
        release_gate = {
            "satisfied": not issues,
            "reason": "No blocking ops issues detected." if not issues else "Blocking ops issues are present.",
            "blocking_issue_count": len(issues),
        }
        return OpsDashboardRead(
            generated_at=generated_at,
            sources=sources,
            rules=rules,
            spatial=spatial,
            jobs=jobs,
            compliance=compliance,
            evals=evals,
            review_queues=review_queues,
            backups=backups,
            release_gate=release_gate,
            issues=issues,
            health_signals=health_signals,
        )

    def _source_summary(self) -> dict[str, Any]:
        citable_retrieval = self._citable_retrieval_summary()
        return {
            "documents": {
                "total": self._count(SourceDocument),
                "active": self._count(SourceDocument, SourceDocument.is_active.is_(True)),
                "inactive": self._count(SourceDocument, SourceDocument.is_active.is_(False)),
            },
            "versions": {
                "total": self._count(SourceVersion),
                "current": self._count(SourceVersion, SourceVersion.is_superseded.is_(False)),
                "superseded": self._count(SourceVersion, SourceVersion.is_superseded.is_(True)),
                "parse_error": self._count(SourceVersion, SourceVersion.parse_status != "ok"),
            },
            "licence_reviews": self._status_counts(SourceLicenceReview.review_status),
            "restricted_licence_reviews": self._count(
                SourceLicenceReview,
                SourceLicenceReview.review_status != "approved",
            ),
            "citable_retrieval": citable_retrieval,
        }

    def _citable_retrieval_summary(self) -> dict[str, Any]:
        current_rows = self.db.execute(
            select(SourceVersion, SourceDocument)
            .join(SourceDocument, SourceDocument.id == SourceVersion.source_document_id)
            .where(
                SourceDocument.is_active.is_(True),
                SourceVersion.is_superseded.is_(False),
            )
            .order_by(SourceDocument.title, SourceVersion.created_at)
        ).all()
        accepted_rows = [(version, source) for version, source in current_rows if version.review_status == "accepted"]
        chunked_version_ids = set(self.db.scalars(select(SourceChunk.source_version_id).distinct()).all())
        cited_version_ids = set(self.db.scalars(select(SourceCitation.source_version_id).distinct()).all())
        citable_artifact_version_ids = chunked_version_ids & cited_version_ids

        supported_versions = 0
        blocked_by_check: dict[str, int] = {}
        sample_blocked_versions: list[dict[str, Any]] = []
        governance = SourceGovernanceService(self.db)
        for version, source in accepted_rows:
            gate = governance.acceptance_gate(source.id, version.id)
            if gate.can_support_retrieval:
                supported_versions += 1
                continue
            blocking_checks = [check.name for check in gate.checks if check.blocking]
            for check_name in blocking_checks:
                blocked_by_check[check_name] = blocked_by_check.get(check_name, 0) + 1
            if len(sample_blocked_versions) < 5:
                sample_blocked_versions.append(
                    {
                        "source_document_id": source.id,
                        "source_title": source.title,
                        "source_version_id": version.id,
                        "version_label": version.version_label,
                        "blocking_checks": blocking_checks,
                    }
                )

        accepted_current_versions = len(accepted_rows)
        accepted_with_citable_artifacts = sum(
            1 for version, _source in accepted_rows if version.id in citable_artifact_version_ids
        )
        blocked_accepted_versions = accepted_current_versions - supported_versions
        if supported_versions:
            readiness_status = "ready"
            next_action = "Citable retrieval has at least one supported source version."
        elif accepted_current_versions:
            readiness_status = "blocked"
            next_action = (
                "Complete source acceptance blockers: rule coverage, no-orphan review, blocking review queues, "
                "licence/source review, and required evals before chat can cite these sources."
            )
        else:
            readiness_status = "missing_sources"
            next_action = (
                "Ingest public sources, complete licence/source review, and approve rule-backed source versions "
                "before source-library chat can cite them."
            )

        return {
            "readiness_status": readiness_status,
            "accepted_current_versions": accepted_current_versions,
            "accepted_with_citable_artifacts": accepted_with_citable_artifacts,
            "supported_versions": supported_versions,
            "blocked_accepted_versions": blocked_accepted_versions,
            "blocked_by_check": dict(sorted(blocked_by_check.items())),
            "sample_blocked_versions": sample_blocked_versions,
            "next_action": next_action,
        }

    def _rule_summary(self) -> dict[str, Any]:
        statuses = self._status_counts(RuleRow.lifecycle_status)
        return {
            "total": self._count(RuleRow),
            "by_lifecycle_status": statuses,
            "approved": statuses.get("approved", 0) + statuses.get("auto_accepted", 0),
            "pending": statuses.get("pending_review", 0),
            "stale": statuses.get("stale", 0),
            "superseded": statuses.get("superseded", 0),
            "rejected": statuses.get("rejected", 0),
        }

    def _spatial_summary(self) -> dict[str, Any]:
        profile_statuses = self._status_counts(AddressProfile.resolution_status)
        fact_review_statuses = self._status_counts(AddressFact.review_status)
        dataset_count = self._count(SpatialDataset)
        stale_profile_ids = {
            profile_id
            for (profile_id,) in self.db.execute(
                select(AddressFact.address_profile_id).where(AddressFact.stale_at.is_not(None)).distinct()
            ).all()
        }
        return {
            "spatial_datasets": {
                "total": dataset_count,
                "with_source_version": self._count(SpatialDataset, SpatialDataset.source_version_id.is_not(None)),
                "without_source_version": self._count(SpatialDataset, SpatialDataset.source_version_id.is_(None)),
                "current": self._count(
                    SpatialDataset,
                    SpatialDataset.source_version_id.is_not(None),
                    SpatialDataset.retrieved_at.is_not(None),
                ),
                "stale": self._count(
                    SpatialDataset,
                    or_(
                        SpatialDataset.source_version_id.is_(None),
                        SpatialDataset.retrieved_at.is_(None),
                    ),
                ),
            },
            "address_profiles": {
                "total": self._count(AddressProfile),
                "by_resolution_status": profile_statuses,
                "resolved": profile_statuses.get("resolved", 0),
                "needs_human_review": profile_statuses.get("needs_human_review", 0),
                "missing_info": profile_statuses.get("missing_info", 0),
                "current": max(0, self._count(AddressProfile) - len(stale_profile_ids)),
                "stale": len(stale_profile_ids),
            },
            "address_facts": {
                "total": self._count(AddressFact),
                "by_review_status": fact_review_statuses,
                "stale": self._count(AddressFact, AddressFact.stale_at.is_not(None)),
                "without_source_or_dataset": self._count(
                    AddressFact,
                    AddressFact.source_version_id.is_(None),
                    AddressFact.spatial_dataset_id.is_(None),
                    AddressFact.planning_layer_feature_id.is_(None),
                ),
            },
            "planning_layer_features": {
                "total": self._count(PlanningLayerFeature),
                "without_source_or_dataset": self._count(
                    PlanningLayerFeature,
                    PlanningLayerFeature.source_version_id.is_(None),
                    PlanningLayerFeature.spatial_dataset_id.is_(None),
                ),
            },
            "local_government_boundaries": {
                "total": self._count(LocalGovernmentBoundary),
                "without_source_or_dataset": self._count(
                    LocalGovernmentBoundary,
                    LocalGovernmentBoundary.source_version_id.is_(None),
                    LocalGovernmentBoundary.spatial_dataset_id.is_(None),
                ),
            },
        }

    def _job_summary(self) -> dict[str, Any]:
        statuses = self._status_counts(BackgroundJob.status)
        failed_count = sum(statuses.get(status, 0) for status in FAILED_JOB_STATUSES)
        latest_failed = self.db.scalar(
            select(BackgroundJob)
            .where(BackgroundJob.status.in_(FAILED_JOB_STATUSES))
            .order_by(BackgroundJob.updated_at.desc(), BackgroundJob.created_at.desc())
        )
        return {
            "total": self._count(BackgroundJob),
            "by_status": statuses,
            "failed": failed_count,
            "latest_failed": _job_snapshot(latest_failed),
        }

    def _compliance_summary(self) -> dict[str, Any]:
        statuses = self._status_counts(CheckResult.status)
        total = sum(statuses.values())
        return {
            "total_results": total,
            "by_status": statuses,
            "unsupported_count": statuses.get("unsupported", 0),
            "missing_info_count": statuses.get("missing_info", 0),
            "needs_human_review_count": statuses.get("needs_human_review", 0),
            "unsupported_rate": _rate(statuses.get("unsupported", 0), total),
            "missing_info_rate": _rate(statuses.get("missing_info", 0), total),
            "needs_human_review_rate": _rate(statuses.get("needs_human_review", 0), total),
        }

    def _eval_summary(self) -> dict[str, Any]:
        tracks: dict[str, dict[str, Any]] = {}
        for track in EVAL_TRACKS:
            active_case_count = self._count(
                GoldenEvalCase,
                GoldenEvalCase.track == track,
                GoldenEvalCase.is_active.is_(True),
            )
            latest_run = self.db.scalar(
                select(GoldenEvalRun)
                .where(GoldenEvalRun.track == track)
                .order_by(GoldenEvalRun.created_at.desc(), GoldenEvalRun.id.desc())
            )
            tracks[track] = {
                "active_case_count": active_case_count,
                "latest_run": _eval_run_snapshot(latest_run),
                "release_gate_satisfied": bool(active_case_count and latest_run and latest_run.passed),
            }
        return {
            "tracks": tracks,
            "active_case_count": self._count(GoldenEvalCase, GoldenEvalCase.is_active.is_(True)),
            "active_track_count": sum(1 for track in tracks.values() if track["active_case_count"]),
            "latest_runs_passed": sum(
                1 for track in tracks.values() if track["active_case_count"] and track["release_gate_satisfied"]
            ),
            "latest_runs_failed_or_missing": sum(
                1 for track in tracks.values() if track["active_case_count"] and not track["release_gate_satisfied"]
            ),
        }

    def _review_queue_summary(self) -> dict[str, Any]:
        items = list(self.db.scalars(select(ReviewQueueItem)))
        by_queue: dict[str, dict[str, Any]] = {
            queue: {"total": 0, "open": 0, "blocking_open": 0} for queue in REVIEW_QUEUE_NAMES
        }
        by_status: dict[str, int] = {}
        blocking_open = 0
        for item in items:
            queue_summary = by_queue.setdefault(item.queue, {"total": 0, "open": 0, "blocking_open": 0})
            queue_summary["total"] += 1
            by_status[item.status] = by_status.get(item.status, 0) + 1
            if item.status in OPEN_REVIEW_STATUSES:
                queue_summary["open"] += 1
                if item.blocking_level == "blocking":
                    queue_summary["blocking_open"] += 1
                    blocking_open += 1
        return {
            "total": len(items),
            "by_queue": by_queue,
            "by_status": by_status,
            "blocking_open": blocking_open,
        }

    def _backup_summary(self) -> dict[str, Any]:
        latest_backup = self._latest_audit_event(BACKUP_ACTIONS)
        latest_restore = self._latest_audit_event(RESTORE_ACTIONS)
        backup_verification_issues = _backup_verification_issues(latest_backup)
        restore_verification_issues = _restore_verification_issues(latest_restore)
        return {
            "last_successful_backup": _audit_event_snapshot(latest_backup),
            "last_successful_restore_test": _audit_event_snapshot(latest_restore),
            "backup_recorded": latest_backup is not None,
            "restore_recorded": latest_restore is not None,
            "backup_verified": not backup_verification_issues,
            "restore_verified": not restore_verification_issues,
            "backup_verification_issues": backup_verification_issues,
            "restore_verification_issues": restore_verification_issues,
        }

    def _issues(
        self,
        sources: dict[str, Any],
        rules: dict[str, Any],
        spatial: dict[str, Any],
        jobs: dict[str, Any],
        evals: dict[str, Any],
        review_queues: dict[str, Any],
        backups: dict[str, Any],
    ) -> list[str]:
        issues: list[str] = []
        auth_status = check_api_auth_ready()
        if auth_status["status"] == "error":
            issues.append("api_auth_not_ready_for_public_deployment")
        if check_database_persistence_ready()["status"] == "error":
            issues.append("durable_database_required_but_sqlite_configured")
        if sources["versions"]["parse_error"]:
            issues.append("source_parse_errors_present")
        if sources["restricted_licence_reviews"]:
            issues.append("restricted_or_unapproved_source_licence_reviews_present")
        citable_retrieval = sources.get("citable_retrieval", {})
        if (
            citable_retrieval.get("accepted_with_citable_artifacts", 0)
            and not citable_retrieval.get("supported_versions", 0)
        ):
            issues.append("no_citable_source_versions_available")
        if rules["pending"] or rules["stale"]:
            issues.append("rules_pending_or_stale")
        if spatial["address_facts"]["stale"] or spatial["address_facts"]["without_source_or_dataset"]:
            issues.append("spatial_facts_stale_or_without_provenance")
        if spatial["spatial_datasets"]["stale"]:
            issues.append("spatial_datasets_stale_or_without_freshness")
        if jobs["failed"]:
            issues.append("background_job_failures_present")
        if evals["latest_runs_failed_or_missing"]:
            issues.append("golden_eval_release_gate_not_satisfied")
        if review_queues["blocking_open"]:
            issues.append("blocking_review_queue_items_open")
        if not backups["backup_recorded"]:
            issues.append("last_successful_backup_not_recorded")
        elif not backups["backup_verified"]:
            issues.append("production_backup_not_verified")
        if not backups["restore_recorded"]:
            issues.append("last_successful_restore_test_not_recorded")
        elif not backups["restore_verified"]:
            issues.append("production_restore_test_not_verified")
        return issues

    def _health_signals(self, compliance: dict[str, Any]) -> list[str]:
        signals: list[str] = []
        if compliance["unsupported_count"]:
            signals.append("unsupported_compliance_results_present")
        if compliance["missing_info_count"]:
            signals.append("missing_info_compliance_results_present")
        if compliance["needs_human_review_count"]:
            signals.append("needs_human_review_compliance_results_present")
        return signals

    def _count(self, model: type[Any], *conditions: Any) -> int:
        stmt = select(func.count()).select_from(model)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int(self.db.scalar(stmt) or 0)

    def _status_counts(self, column: Any) -> dict[str, int]:
        rows = self.db.execute(select(column, func.count()).group_by(column)).all()
        return {str(status): int(count) for status, count in rows if status is not None}

    def _latest_audit_event(self, actions: set[str]) -> AuditEvent | None:
        return self.db.scalar(
            select(AuditEvent)
            .where(AuditEvent.action.in_(actions))
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        )


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 4)


def _backup_verification_issues(event: AuditEvent | None) -> list[str]:
    if not event:
        return ["backup_event_missing"]
    metadata = from_json(event.metadata_json, {})
    issues = _common_infra_verification_issues(metadata)
    if not _is_truthy(metadata.get("offsite")):
        issues.append("offsite_backup_required")
    if not _is_truthy(metadata.get("encrypted")):
        issues.append("encrypted_backup_required")
    if not _has_daily_schedule(metadata):
        issues.append("daily_backup_schedule_required")
    if not (metadata.get("db_backup") or metadata.get("database_backup")):
        issues.append("database_backup_artifact_required")
    if not (metadata.get("minio_backup") or metadata.get("object_storage_backup") or metadata.get("storage_backup")):
        issues.append("object_storage_backup_artifact_required")
    return issues


def _restore_verification_issues(event: AuditEvent | None) -> list[str]:
    if not event:
        return ["restore_event_missing"]
    metadata = from_json(event.metadata_json, {})
    issues = _common_infra_verification_issues(metadata)
    if not _is_truthy(metadata.get("clean_machine_restore")):
        issues.append("clean_machine_restore_required")
    if not _is_truthy(metadata.get("checksum_validated")):
        issues.append("checksum_validation_required")
    return issues


def _common_infra_verification_issues(metadata: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if str(metadata.get("environment", "")).strip().lower() not in PRODUCTION_ENVIRONMENTS:
        issues.append("production_environment_required")
    if not metadata.get("manifest_sha256"):
        issues.append("manifest_sha256_required")
    duration = metadata.get("duration_seconds")
    if not isinstance(duration, int | float) or duration <= 0:
        issues.append("duration_seconds_required")
    return issues


def _has_daily_schedule(metadata: dict[str, Any]) -> bool:
    if _is_truthy(metadata.get("scheduled")):
        return True
    schedule = str(metadata.get("schedule", "")).strip().lower()
    return schedule in {"daily", "nightly"}


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _job_snapshot(job: BackgroundJob | None) -> dict[str, Any] | None:
    if not job:
        return None
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "project_id": job.project_id,
        "source_version_id": job.source_version_id,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


def _eval_run_snapshot(run: GoldenEvalRun | None) -> dict[str, Any] | None:
    if not run:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "passed": run.passed,
        "case_count": run.case_count,
        "passed_count": run.passed_count,
        "failed_count": run.failed_count,
        "metrics": from_json(run.metrics_json, {}),
        "created_at": run.created_at.isoformat(),
    }


def _audit_event_snapshot(event: AuditEvent | None) -> dict[str, Any] | None:
    if not event:
        return None
    return {
        "id": event.id,
        "action": event.action,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "metadata": from_json(event.metadata_json, {}),
        "created_at": event.created_at.isoformat(),
    }

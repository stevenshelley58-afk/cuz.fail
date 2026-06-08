from __future__ import annotations

from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_compliance.rule_audits import RuleAuditService
from draftcheck_compliance.rules import RuleGovernanceService
from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import (
    AddressFact,
    CheckResult,
    CheckRun,
    DecisionTrace,
    Export,
    GoldenEvalCase,
    GoldenEvalRun,
    LocalGovernmentFact,
    ResponseDraft,
    ReviewQueueItem,
    ResolvedRule,
    RfiItem,
    RuleExtractionCandidate,
    RuleRow,
    SourceDocument,
    SourceLicenceReview,
    SourceVersion,
    utcnow,
)
from draftcheck_core.review_queue import OPEN_REVIEW_STATUSES, ReviewQueueService
from draftcheck_core.source_support import (
    ACCEPTABLE_SOURCE_PARSE_STATUSES,
    CITABLE_RETRIEVAL_BLOCKING_QUEUES,
    source_version_can_support_citable_retrieval,
)
from draftcheck_shared.schemas import (
    NoOrphanAuditItem,
    SourceAcceptanceGateCheck,
    SourceAcceptanceGateRead,
    SourceReviewQueueReconciliationRead,
    SourceReviewRequest,
    ReviewQueueItemCreate,
    ReviewQueueName,
    RuleCoverageAuditItem,
)


ACCEPTABLE_PARSE_STATUSES = {"ok", "partial"}
SOURCE_ACCEPTANCE_EVAL_TRACKS = ("rule_extraction", "retrieval")
SOURCE_ACCEPTANCE_QUEUE_NAMES = {
    "source_review",
    "rule_review",
    "licence_review",
    "eval_failure_review",
}
ReviewItemKey = tuple[str, str, str, str]


class SourceGovernanceService:
    def __init__(self, db: Session):
        self.db = db

    def acceptance_gate(
        self,
        source_id: str,
        source_version_id: str,
        *,
        enqueue_review_items: bool = False,
    ) -> SourceAcceptanceGateRead:
        source, version = self._source_and_version(source_id, source_version_id)
        checks = [
            self._source_state_check(version),
            self._licence_check(source, version),
            self._coverage_check(version),
            self._no_orphan_check(version),
            self._review_queue_check(version),
            self._eval_check(version),
        ]
        enqueued_review_item_ids: list[str] = []
        if enqueue_review_items:
            enqueued_review_item_ids = self._enqueue_blocking_reviews(version, checks)
        blocking_reasons = [check.reason for check in checks if check.blocking]
        return SourceAcceptanceGateRead(
            source_document_id=source.id,
            source_version_id=version.id,
            review_status=version.review_status,
            status="blocked" if blocking_reasons else "pass",
            can_support_retrieval=source_version_can_support_citable_retrieval(self.db, version.id),
            blocking_reasons=blocking_reasons,
            checks=checks,
            enqueued_review_item_ids=enqueued_review_item_ids,
        )

    def reconcile_source_version_review_queue(
        self,
        source_id: str,
        source_version_id: str,
        *,
        reviewed_by: str = "system",
    ) -> SourceReviewQueueReconciliationRead:
        source, version = self._source_and_version(source_id, source_version_id)
        checks = [
            self._source_state_check(version),
            self._licence_check(source, version),
            self._coverage_check(version),
            self._no_orphan_check(version),
            self._eval_check(version),
        ]
        active_keys = self._active_review_item_keys(version, checks)
        open_items = list(
            self.db.scalars(
                select(ReviewQueueItem)
                .where(
                    ReviewQueueItem.source_version_id == version.id,
                    ReviewQueueItem.queue.in_(SOURCE_ACCEPTANCE_QUEUE_NAMES),
                    ReviewQueueItem.status.in_(OPEN_REVIEW_STATUSES),
                    ReviewQueueItem.blocking_level == "blocking",
                )
                .order_by(ReviewQueueItem.created_at, ReviewQueueItem.id)
            )
        )

        resolved_item_ids: list[str] = []
        still_open_item_ids: list[str] = []
        for item in open_items:
            if _review_item_key(item) in active_keys:
                still_open_item_ids.append(item.id)
                continue
            item.status = "resolved"
            item.evidence_json = to_json(
                {
                    **from_json(item.evidence_json, {}),
                    "reconciled_by": reviewed_by,
                    "reconciliation_reason": "Current source acceptance audits no longer report this blocker.",
                }
            )
            resolved_item_ids.append(item.id)
            record_audit(
                self.db,
                action="review_queue.reconciled",
                target_type="review_queue_item",
                target_id=item.id,
                actor_id=reviewed_by,
                metadata={
                    "source_version_id": version.id,
                    "previous_status": "open",
                    "status": "resolved",
                    "reason": item.reason,
                },
            )

        self.db.flush()
        gate = self.acceptance_gate(source.id, version.id)
        return SourceReviewQueueReconciliationRead(
            source_document_id=source.id,
            source_version_id=version.id,
            resolved_item_ids=resolved_item_ids,
            still_open_item_ids=still_open_item_ids,
            current_blocker_keys=[_review_item_key_payload(key) for key in sorted(active_keys)],
            gate=gate,
        )

    def review_source(self, source_id: str, payload: SourceReviewRequest) -> SourceAcceptanceGateRead:
        source, version = self._review_target_source_and_version(source_id, payload.source_version_id)
        if payload.review_status == "accepted":
            gate = self.acceptance_gate(source_id, version.id, enqueue_review_items=True)
            if self._citable_review_preconditions_pass(source, version):
                version.review_status = "accepted"
                version.reviewed_by = payload.reviewed_by
                version.reviewed_at = utcnow()
                record_audit(
                    self.db,
                    action="source_version.reviewed",
                    target_type="source_version",
                    target_id=version.id,
                    actor_id=payload.reviewed_by,
                    metadata={
                        "review_status": "accepted",
                        "notes": payload.notes,
                        "acceptance_gate_status": gate.status,
                        "blocking_reasons": gate.blocking_reasons,
                    },
                )
                self.db.flush()
                updated_gate = self.acceptance_gate(source_id, version.id)
                updated_gate.enqueued_review_item_ids = gate.enqueued_review_item_ids
                return updated_gate
            return gate

        version.review_status = payload.review_status
        version.reviewed_by = payload.reviewed_by
        version.reviewed_at = utcnow()
        if payload.review_status != "accepted":
            self._stale_source_dependents(version)
        record_audit(
            self.db,
            action="source_version.reviewed",
            target_type="source_version",
            target_id=version.id,
            actor_id=payload.reviewed_by,
            metadata={"review_status": payload.review_status, "notes": payload.notes},
        )
        self.db.flush()
        return self.acceptance_gate(source_id, version.id)

    def _source_and_version(self, source_id: str, source_version_id: str) -> tuple[SourceDocument, SourceVersion]:
        source = self.db.get(SourceDocument, source_id)
        if not source:
            raise KeyError("Source not found")
        version = self.db.get(SourceVersion, source_version_id)
        if not version or version.source_document_id != source.id:
            raise KeyError("Source version not found")
        return source, version

    def _review_target_source_and_version(
        self, source_id: str, source_version_id: str | None
    ) -> tuple[SourceDocument, SourceVersion]:
        if source_version_id:
            return self._source_and_version(source_id, source_version_id)
        version = self.db.scalar(
            select(SourceVersion)
            .where(SourceVersion.source_document_id == source_id)
            .order_by(SourceVersion.retrieved_at.desc(), SourceVersion.created_at.desc())
        )
        if not version:
            raise KeyError("Source version not found")
        source = self.db.get(SourceDocument, source_id)
        if not source:
            raise KeyError("Source not found")
        return source, version

    def _citable_review_preconditions_pass(self, source: SourceDocument, version: SourceVersion) -> bool:
        if not source.is_active or version.is_superseded:
            return False
        if version.parse_status not in ACCEPTABLE_SOURCE_PARSE_STATUSES:
            return False
        approved_licence = self.db.scalar(
            select(SourceLicenceReview.id)
            .where(
                SourceLicenceReview.source_version_id == version.id,
                SourceLicenceReview.review_status == "approved",
                SourceLicenceReview.allowed_storage.is_(True),
                SourceLicenceReview.allowed_ai_processing.is_(True),
            )
            .limit(1)
        )
        if approved_licence is None:
            return False
        citable_blocking_review = self.db.scalar(
            select(ReviewQueueItem.id)
            .where(
                ReviewQueueItem.source_version_id == version.id,
                ReviewQueueItem.queue.in_(CITABLE_RETRIEVAL_BLOCKING_QUEUES),
                ReviewQueueItem.status.in_(OPEN_REVIEW_STATUSES),
                ReviewQueueItem.blocking_level == "blocking",
            )
            .limit(1)
        )
        return citable_blocking_review is None

    def _active_review_item_keys(
        self,
        version: SourceVersion,
        checks: list[SourceAcceptanceGateCheck],
    ) -> set[ReviewItemKey]:
        keys: set[ReviewItemKey] = set()
        for check in checks:
            if not check.blocking:
                continue
            if check.name == "blocking_review_queue":
                continue
            if check.name == "rule_coverage":
                keys.update(self._rule_coverage_review_item_keys(version))
                continue
            if check.name == "no_orphan":
                keys.update(self._no_orphan_review_item_keys(version))
                continue
            queue = _queue_for_check(check.name)
            keys.add(
                (
                    queue,
                    "source_version",
                    version.id,
                    f"Source acceptance blocked: {check.reason}",
                )
            )
        return keys

    def _rule_coverage_review_item_keys(self, version: SourceVersion) -> set[ReviewItemKey]:
        audit = RuleGovernanceService(self.db).coverage_audit(
            source_version_id=version.id,
            only_gaps=True,
        )
        keys: set[ReviewItemKey] = set()
        for audit_item in audit.items:
            target_type, target_id = _coverage_review_target(audit_item)
            keys.add(
                (
                    "rule_review",
                    target_type,
                    target_id,
                    f"Rule coverage gap: {audit_item.status} in clause {audit_item.clause_id}",
                )
            )
        return keys

    def _no_orphan_review_item_keys(self, version: SourceVersion) -> set[ReviewItemKey]:
        audit = RuleAuditService(self.db).no_orphan_audit(
            source_version_id=version.id,
            summary_only=False,
        )
        keys: set[ReviewItemKey] = set()
        for audit_item in audit.items:
            target_type, target_id = _no_orphan_review_target(audit_item)
            keys.add(
                (
                    "rule_review",
                    target_type,
                    target_id,
                    f"No-orphan finding: {audit_item.status} in clause {audit_item.clause_id}",
                )
            )
        return keys

    def _source_state_check(self, version: SourceVersion) -> SourceAcceptanceGateCheck:
        if version.is_superseded:
            return _check(
                "source_state",
                "fail",
                "Source version is superseded.",
                {"is_superseded": True, "parse_status": version.parse_status},
            )
        if version.parse_status not in ACCEPTABLE_PARSE_STATUSES:
            return _check(
                "source_state",
                "fail",
                "Source version parse status cannot support acceptance.",
                {"is_superseded": False, "parse_status": version.parse_status},
            )
        return _check(
            "source_state",
            "pass",
            "Source version is current and parseable.",
            {"is_superseded": False, "parse_status": version.parse_status},
            blocking=False,
        )

    def _licence_check(self, source: SourceDocument, version: SourceVersion) -> SourceAcceptanceGateCheck:
        reviews = list(
            self.db.scalars(
                select(SourceLicenceReview).where(SourceLicenceReview.source_version_id == version.id)
            )
        )
        approved = [
            review
            for review in reviews
            if review.review_status == "approved" and review.allowed_ai_processing and review.allowed_storage
        ]
        if not approved:
            return _check(
                "licence",
                "fail",
                "No approved licence review allows storage and AI processing for this source version.",
                {
                    "source_document_id": source.id,
                    "review_count": len(reviews),
                    "access_type": source.access_type,
                },
            )
        return _check(
            "licence",
            "pass",
            "Approved licence review allows storage and AI processing.",
            {"source_document_id": source.id, "review_count": len(reviews)},
            blocking=False,
        )

    def _coverage_check(self, version: SourceVersion) -> SourceAcceptanceGateCheck:
        coverage = RuleGovernanceService(self.db).coverage_audit(
            source_version_id=version.id,
            summary_only=True,
        )
        if coverage.gap_count:
            return _check(
                "rule_coverage",
                "fail",
                "Rule coverage audit has blocking gaps.",
                {"gap_count": coverage.gap_count, "summary": coverage.summary},
            )
        return _check(
            "rule_coverage",
            "pass",
            "Rule coverage audit has no gaps.",
            {"gap_count": 0, "summary": coverage.summary},
            blocking=False,
        )

    def _no_orphan_check(self, version: SourceVersion) -> SourceAcceptanceGateCheck:
        audit = RuleAuditService(self.db).no_orphan_audit(
            source_version_id=version.id,
            summary_only=True,
        )
        if audit.blocking_count:
            return _check(
                "no_orphan",
                "fail",
                "No-orphan audit has blocking clause findings.",
                {"blocking_count": audit.blocking_count, "summary": audit.summary},
            )
        return _check(
            "no_orphan",
            "pass",
            "No-orphan audit has no blocking findings.",
            {"blocking_count": 0, "summary": audit.summary},
            blocking=False,
        )

    def _review_queue_check(self, version: SourceVersion) -> SourceAcceptanceGateCheck:
        count = int(
            self.db.scalar(
                select(ReviewQueueItem.id)
                .where(
                    ReviewQueueItem.source_version_id == version.id,
                    ReviewQueueItem.queue.in_(SOURCE_ACCEPTANCE_QUEUE_NAMES),
                    ReviewQueueItem.status.in_(OPEN_REVIEW_STATUSES),
                    ReviewQueueItem.blocking_level == "blocking",
                )
                .limit(1)
            )
            is not None
        )
        if count:
            return _check(
                "blocking_review_queue",
                "fail",
                "Open blocking review queue items target this source version.",
                {"open_blocking_item_present": True},
            )
        return _check(
            "blocking_review_queue",
            "pass",
            "No open blocking source-acceptance review queue items target this source version.",
            {"open_blocking_item_present": False},
            blocking=False,
        )

    def _eval_check(self, version: SourceVersion) -> SourceAcceptanceGateCheck:
        failed_tracks: list[str] = []
        skipped_tracks: list[str] = []
        passed_tracks: list[str] = []
        for track in SOURCE_ACCEPTANCE_EVAL_TRACKS:
            active_cases = self._active_eval_cases_for_version(track, version.id)
            if not active_cases:
                skipped_tracks.append(track)
                continue
            latest_run = self.db.scalar(
                select(GoldenEvalRun)
                .where(GoldenEvalRun.track == track)
                .order_by(GoldenEvalRun.created_at.desc(), GoldenEvalRun.id.desc())
            )
            if latest_run and _latest_run_passed_cases(latest_run, [case.id for case in active_cases]):
                passed_tracks.append(track)
            else:
                failed_tracks.append(track)
        if failed_tracks:
            return _check(
                "golden_evals",
                "fail",
                "Required source-acceptance eval tracks have active cases without a passing latest run.",
                {"failed_tracks": failed_tracks, "passed_tracks": passed_tracks, "skipped_tracks": skipped_tracks},
            )
        status = "warning" if skipped_tracks else "pass"
        return _check(
            "golden_evals",
            status,
            (
                "No active eval cases exist for some required tracks."
                if skipped_tracks
                else "Required source-acceptance eval tracks have passing latest runs."
            ),
            {"passed_tracks": passed_tracks, "skipped_tracks": skipped_tracks},
            blocking=False,
        )

    def _active_eval_cases_for_version(self, track: str, source_version_id: str) -> list[GoldenEvalCase]:
        cases = self.db.scalars(
            select(GoldenEvalCase).where(GoldenEvalCase.track == track, GoldenEvalCase.is_active.is_(True))
        )
        relevant_cases: list[GoldenEvalCase] = []
        for case in cases:
            case_source_version_ids: list[str] = from_json(case.source_version_ids_json, [])
            if not case_source_version_ids or source_version_id in case_source_version_ids:
                relevant_cases.append(case)
        return relevant_cases

    def _enqueue_blocking_reviews(
        self,
        version: SourceVersion,
        checks: list[SourceAcceptanceGateCheck],
    ) -> list[str]:
        queue_service = ReviewQueueService(self.db)
        item_ids: list[str] = []
        for check in checks:
            if not check.blocking:
                continue
            if check.name == "blocking_review_queue":
                continue
            if check.name == "rule_coverage":
                detailed_ids = self._enqueue_rule_coverage_reviews(version, queue_service)
                if detailed_ids:
                    item_ids.extend(detailed_ids)
                    continue
            if check.name == "no_orphan":
                detailed_ids = self._enqueue_no_orphan_reviews(version, queue_service)
                if detailed_ids:
                    item_ids.extend(detailed_ids)
                    continue
            queue = _queue_for_check(check.name)
            item = queue_service.enqueue(
                ReviewQueueItemCreate(
                    queue=queue,
                    source_version_id=version.id,
                    target_type="source_version",
                    target_id=version.id,
                    reason=f"Source acceptance blocked: {check.reason}",
                    blocking_level="blocking",
                    evidence={"check": check.name, **check.evidence},
                    suggested_action=_suggested_action_for_check(check.name),
                    priority="critical" if check.name == "golden_evals" else "high",
                )
            )
            item_ids.append(item.id)
        return item_ids

    def _enqueue_rule_coverage_reviews(
        self,
        version: SourceVersion,
        queue_service: ReviewQueueService,
    ) -> list[str]:
        audit = RuleGovernanceService(self.db).coverage_audit(
            source_version_id=version.id,
            only_gaps=True,
        )
        item_ids: list[str] = []
        for audit_item in audit.items:
            target_type, target_id = _coverage_review_target(audit_item)
            item = queue_service.enqueue(
                ReviewQueueItemCreate(
                    queue="rule_review",
                    source_version_id=version.id,
                    target_type=target_type,
                    target_id=target_id,
                    reason=f"Rule coverage gap: {audit_item.status} in clause {audit_item.clause_id}",
                    blocking_level="blocking",
                    evidence={"audit": "rule_coverage", **audit_item.model_dump(mode="json")},
                    suggested_action=audit_item.recommended_action,
                    priority="high",
                )
            )
            item_ids.append(item.id)
        return item_ids

    def _enqueue_no_orphan_reviews(
        self,
        version: SourceVersion,
        queue_service: ReviewQueueService,
    ) -> list[str]:
        audit = RuleAuditService(self.db).no_orphan_audit(
            source_version_id=version.id,
            summary_only=False,
        )
        item_ids: list[str] = []
        for audit_item in audit.items:
            target_type, target_id = _no_orphan_review_target(audit_item)
            item = queue_service.enqueue(
                ReviewQueueItemCreate(
                    queue="rule_review",
                    source_version_id=version.id,
                    target_type=target_type,
                    target_id=target_id,
                    reason=f"No-orphan finding: {audit_item.status} in clause {audit_item.clause_id}",
                    blocking_level="blocking",
                    evidence={"audit": "no_orphan", **audit_item.model_dump(mode="json")},
                    suggested_action=audit_item.recommended_action,
                    priority="high",
                )
            )
            item_ids.append(item.id)
        return item_ids

    def _stale_source_dependents(self, version: SourceVersion) -> None:
        stale_rule_ids: list[str] = []
        for rule_row in self.db.scalars(select(RuleRow).where(RuleRow.source_version_id == version.id)):
            if rule_row.lifecycle_status in {"approved", "auto_accepted", "pending_review"}:
                rule_row.lifecycle_status = "stale"
                rule_row.approved_by = None
                rule_row.approved_at = None
                stale_rule_ids.append(rule_row.id)
        stale_candidate_ids: list[str] = []
        for candidate in self.db.scalars(
            select(RuleExtractionCandidate).where(RuleExtractionCandidate.source_version_id == version.id)
        ):
            if candidate.status not in {"rejected", "stale", "superseded"}:
                candidate.status = "stale"
                candidate.review_notes = _append_note(
                    candidate.review_notes,
                    f"Stale: source version {version.id} is no longer accepted.",
                )
                stale_candidate_ids.append(candidate.id)
        if stale_rule_ids:
            for resolved_rule in self.db.scalars(
                select(ResolvedRule).where(ResolvedRule.rule_row_id.in_(stale_rule_ids))
            ):
                resolved_rule.status = "stale"
                resolved_rule.applies_reason = (
                    f"{resolved_rule.applies_reason}\n"
                    f"Stale: source version {version.id} is no longer accepted."
                )
            record_audit(
                self.db,
                action="source_version.dependent_rules_marked_stale",
                target_type="source_version",
                target_id=version.id,
                metadata={"rule_row_ids": stale_rule_ids, "rule_candidate_ids": stale_candidate_ids},
            )
        elif stale_candidate_ids:
            record_audit(
                self.db,
                action="source_version.dependent_rules_marked_stale",
                target_type="source_version",
                target_id=version.id,
                metadata={"rule_row_ids": [], "rule_candidate_ids": stale_candidate_ids},
            )
        output_counts = self._stale_regulatory_outputs(version)
        spatial_counts = self._stale_source_spatial_facts(version)
        if any(output_counts.values()) or any(spatial_counts.values()):
            record_audit(
                self.db,
                action="source_version.dependent_outputs_marked_stale",
                target_type="source_version",
                target_id=version.id,
                metadata={"outputs": output_counts, "spatial": spatial_counts},
            )

    def _stale_regulatory_outputs(self, version: SourceVersion) -> dict[str, int]:
        stale_note = f"Source version {version.id} is no longer accepted."
        counts = {
            "check_runs": 0,
            "check_results": 0,
            "decision_traces": 0,
            "rfi_items": 0,
            "response_drafts": 0,
            "exports": 0,
        }
        for check_run in self.db.scalars(select(CheckRun)):
            if _json_contains_source_version_id(check_run.source_version_ids_json, version.id):
                check_run.status = "stale"
                counts["check_runs"] += 1

        for result in self.db.scalars(select(CheckResult)):
            if _json_contains_source_version_id(result.citations_json, version.id):
                result.status = "unsupported"
                result.confidence = 0.0
                result.requires_human_review = True
                result.missing_information_json = _append_json_list(result.missing_information_json, stale_note)
                counts["check_results"] += 1

        for trace in self.db.scalars(select(DecisionTrace)):
            if not (
                _json_contains_source_version_id(trace.citation_ids_json, version.id)
                or _json_contains_source_version_id(trace.input_sources_json, version.id)
            ):
                continue
            trace.result = "unsupported"
            applicability: dict[str, Any] = from_json(trace.applicability_trace_json, {})
            missing = applicability.get("missing_information")
            if not isinstance(missing, list):
                missing = []
            if stale_note not in missing:
                missing.append(stale_note)
            applicability["missing_information"] = missing
            applicability["source_support_status"] = "stale_source"
            trace.applicability_trace_json = to_json(applicability)
            counts["decision_traces"] += 1

        for item in self.db.scalars(select(RfiItem)):
            if _json_contains_source_version_id(item.source_requirement_candidates_json, version.id):
                item.source_requirement_candidates_json = "[]"
                item.missing_evidence_json = _append_json_list(item.missing_evidence_json, stale_note)
                counts["rfi_items"] += 1

        for draft in self.db.scalars(select(ResponseDraft)):
            if _json_contains_source_version_id(draft.citations_json, version.id):
                draft.citations_json = "[]"
                draft.confidence = 0.0
                draft.requires_human_review = True
                draft.missing_information_json = _append_json_list(draft.missing_information_json, stale_note)
                _mark_response_draft_content_stale(draft, version.id, stale_note)
                counts["response_drafts"] += 1

        for export in self.db.scalars(select(Export)):
            manifest: dict[str, Any] = from_json(export.manifest_json, {})
            if not _json_contains(version.id, manifest):
                continue
            export.status = "stale"
            stale_ids = manifest.get("stale_source_version_ids")
            if not isinstance(stale_ids, list):
                stale_ids = []
            if version.id not in stale_ids:
                stale_ids.append(version.id)
            manifest["stale_source_version_ids"] = stale_ids
            manifest["source_support_status"] = "stale_source"
            manifest["requires_human_signoff"] = True
            manifest["submission_ready"] = False
            manifest["human_signoff_status"] = "required_after_source_stale"
            manifest["source_signoff_notice"] = (
                f"Source version {version.id} is no longer accepted; regenerate and obtain human signoff "
                "before treating this export as submission-ready."
            )
            export.manifest_json = to_json(manifest)
            counts["exports"] += 1
        return counts

    def _stale_source_spatial_facts(self, version: SourceVersion) -> dict[str, int]:
        now = utcnow()
        counts = {"address_facts": 0, "local_government_facts": 0}
        for address_fact in self.db.scalars(select(AddressFact).where(AddressFact.source_version_id == version.id)):
            address_fact.stale_at = now
            address_fact.review_status = "stale"
            counts["address_facts"] += 1
        for local_government_fact in self.db.scalars(
            select(LocalGovernmentFact).where(LocalGovernmentFact.source_version_id == version.id)
        ):
            local_government_fact.review_status = "stale"
            counts["local_government_facts"] += 1
        return counts


def _check(
    name: str,
    status: str,
    reason: str,
    evidence: dict[str, object],
    *,
    blocking: bool = True,
) -> SourceAcceptanceGateCheck:
    return SourceAcceptanceGateCheck(
        name=name,
        status=status,  # type: ignore[arg-type]
        blocking=blocking,
        reason=reason,
        evidence=evidence,
    )


def _queue_for_check(check_name: str) -> ReviewQueueName:
    if check_name == "licence":
        return "licence_review"
    if check_name == "golden_evals":
        return "eval_failure_review"
    if check_name in {"rule_coverage", "no_orphan"}:
        return "rule_review"
    return cast(ReviewQueueName, "source_review")


def _suggested_action_for_check(check_name: str) -> str:
    return {
        "source_state": "Refresh or replace the source version before acceptance.",
        "licence": "Complete licence review and allow storage plus AI processing before acceptance.",
        "rule_coverage": "Resolve coverage-audit gaps by approving source-cited rules or recording manual review.",
        "no_orphan": "Disposition every clause and represent exception language in conditions or carveouts.",
        "blocking_review_queue": "Resolve existing blocking review queue items for this source version.",
        "golden_evals": "Run and pass the required golden eval tracks before acceptance.",
    }.get(check_name, "Resolve the blocking source acceptance finding.")


def _coverage_review_target(item: RuleCoverageAuditItem) -> tuple[str, str]:
    if item.status == "candidate_not_promoted" and item.rule_candidate_ids:
        return "rule_extraction_candidate", item.rule_candidate_ids[0]
    if item.status == "rule_not_approved" and item.rule_row_ids:
        return "rule_row", item.rule_row_ids[0]
    return "clause", item.clause_row_id


def _no_orphan_review_target(item: NoOrphanAuditItem) -> tuple[str, str]:
    rule_row_ids = item.evidence.get("rule_row_ids")
    if isinstance(rule_row_ids, list) and rule_row_ids:
        return "rule_row", str(rule_row_ids[0])
    rule_candidate_ids = item.evidence.get("rule_candidate_ids")
    if isinstance(rule_candidate_ids, list) and rule_candidate_ids:
        return "rule_extraction_candidate", str(rule_candidate_ids[0])
    return "clause", item.clause_row_id


def _review_item_key(item: ReviewQueueItem) -> ReviewItemKey:
    return (item.queue, item.target_type, item.target_id, item.reason)


def _review_item_key_payload(key: ReviewItemKey) -> dict[str, str]:
    queue, target_type, target_id, reason = key
    return {
        "queue": queue,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
    }


def _append_note(existing: str, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing}\n{note}"


def _append_json_list(raw_json: str, item: str) -> str:
    values: list[str] = from_json(raw_json, [])
    if item not in values:
        values.append(item)
    return to_json(values)


def _mark_response_draft_content_stale(draft: ResponseDraft, source_version_id: str, stale_note: str) -> None:
    content: dict[str, Any] = from_json(draft.content_json, {})
    content["source_support_status"] = "stale_source"
    stale_ids = content.get("stale_source_version_ids")
    if not isinstance(stale_ids, list):
        stale_ids = []
    if source_version_id not in stale_ids:
        stale_ids.append(source_version_id)
    content["stale_source_version_ids"] = stale_ids

    item_table = content.get("item_table")
    if isinstance(item_table, list):
        for row in item_table:
            if not isinstance(row, dict):
                continue
            if row.get("source_support_status") == "cited" or row.get("source_citation_count"):
                row["source_support_status"] = "stale_source"
                row["source_citation_count"] = 0
                missing_evidence = row.get("missing_evidence")
                if not isinstance(missing_evidence, list):
                    missing_evidence = []
                if stale_note not in missing_evidence:
                    missing_evidence.append(stale_note)
                row["missing_evidence"] = missing_evidence

    draft.content_json = to_json(content)
    notice = f"STALE SOURCE NOTICE: {stale_note} Regenerate this draft before relying on it."
    if notice not in draft.draft_text:
        draft.draft_text = f"{notice}\n\n{draft.draft_text}"


def _latest_run_passed_cases(run: GoldenEvalRun, case_ids: list[str]) -> bool:
    results: list[dict[str, Any]] = from_json(run.case_results_json, [])
    passed_case_ids = {result.get("case_id") for result in results if result.get("status") == "passed"}
    return all(case_id in passed_case_ids for case_id in case_ids)


def _json_contains_source_version_id(raw_json: str, source_version_id: str) -> bool:
    return _json_contains(source_version_id, from_json(raw_json, None))


def _json_contains(source_version_id: str, value: Any) -> bool:
    if isinstance(value, str):
        return value == source_version_id
    if isinstance(value, list):
        return any(_json_contains(source_version_id, item) for item in value)
    if isinstance(value, dict):
        if value.get("source_version_id") == source_version_id:
            return True
        source_version_ids = value.get("source_version_ids")
        if isinstance(source_version_ids, list) and source_version_id in source_version_ids:
            return True
        return any(_json_contains(source_version_id, item) for item in value.values())
    return False

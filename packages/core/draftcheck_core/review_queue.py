from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import ReviewQueueItem
from draftcheck_shared.schemas import ReviewQueueItemCreate, ReviewQueueItemPatch, ReviewQueueItemRead


OPEN_REVIEW_STATUSES = {"open", "in_progress"}


class ReviewQueueService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, payload: ReviewQueueItemCreate) -> ReviewQueueItemRead:
        item = self.db.scalar(
            select(ReviewQueueItem).where(
                ReviewQueueItem.queue == payload.queue,
                ReviewQueueItem.target_type == payload.target_type,
                ReviewQueueItem.target_id == payload.target_id,
                ReviewQueueItem.reason == payload.reason,
                ReviewQueueItem.status.in_(OPEN_REVIEW_STATUSES),
            )
        )
        created = False
        if not item:
            item = ReviewQueueItem(
                queue=payload.queue,
                project_id=payload.project_id,
                source_version_id=payload.source_version_id,
                target_type=payload.target_type,
                target_id=payload.target_id,
                reason=payload.reason,
                blocking_level=payload.blocking_level,
                evidence_json=to_json(payload.evidence),
                suggested_action=payload.suggested_action,
                assignee=payload.assignee,
                priority=payload.priority,
                status="open",
            )
            self.db.add(item)
            created = True
        else:
            item.project_id = payload.project_id or item.project_id
            item.source_version_id = payload.source_version_id or item.source_version_id
            item.blocking_level = payload.blocking_level
            item.evidence_json = to_json(payload.evidence)
            item.suggested_action = payload.suggested_action
            item.assignee = payload.assignee or item.assignee
            item.priority = payload.priority
        self.db.flush()
        record_audit(
            self.db,
            action="review_queue.enqueued" if created else "review_queue.updated",
            target_type="review_queue_item",
            target_id=item.id,
            project_id=item.project_id,
            metadata={
                "queue": item.queue,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "reason": item.reason,
                "blocking_level": item.blocking_level,
                "status": item.status,
            },
        )
        self.db.flush()
        return _review_queue_item_read(item)

    def list_items(
        self,
        *,
        queue: str | None = None,
        status: str | None = None,
        project_id: str | None = None,
        source_version_id: str | None = None,
    ) -> list[ReviewQueueItemRead]:
        stmt = select(ReviewQueueItem).order_by(ReviewQueueItem.created_at.desc(), ReviewQueueItem.id)
        if queue:
            stmt = stmt.where(ReviewQueueItem.queue == queue)
        if status:
            stmt = stmt.where(ReviewQueueItem.status == status)
        if project_id:
            stmt = stmt.where(ReviewQueueItem.project_id == project_id)
        if source_version_id:
            stmt = stmt.where(ReviewQueueItem.source_version_id == source_version_id)
        return [_review_queue_item_read(item) for item in self.db.scalars(stmt)]

    def update_item(self, item_id: str, payload: ReviewQueueItemPatch) -> ReviewQueueItemRead:
        item = self.db.get(ReviewQueueItem, item_id)
        if not item:
            raise KeyError("Review queue item not found")
        if payload.status is not None:
            item.status = payload.status
        if payload.assignee is not None:
            item.assignee = payload.assignee
        if payload.priority is not None:
            item.priority = payload.priority
        if payload.evidence is not None:
            item.evidence_json = to_json(payload.evidence)
        if payload.suggested_action is not None:
            item.suggested_action = payload.suggested_action
        record_audit(
            self.db,
            action="review_queue.reviewed",
            target_type="review_queue_item",
            target_id=item.id,
            project_id=item.project_id,
            actor_id=payload.reviewed_by,
            metadata={
                "status": item.status,
                "assignee": item.assignee,
                "priority": item.priority,
            },
        )
        self.db.flush()
        return _review_queue_item_read(item)


def _review_queue_item_read(item: ReviewQueueItem) -> ReviewQueueItemRead:
    return ReviewQueueItemRead(
        id=item.id,
        queue=item.queue,  # type: ignore[arg-type]
        project_id=item.project_id,
        source_version_id=item.source_version_id,
        target_type=item.target_type,
        target_id=item.target_id,
        reason=item.reason,
        blocking_level=item.blocking_level,  # type: ignore[arg-type]
        evidence=from_json(item.evidence_json, {}),
        suggested_action=item.suggested_action,
        assignee=item.assignee,
        status=item.status,  # type: ignore[arg-type]
        priority=item.priority,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )

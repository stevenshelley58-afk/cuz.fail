from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import AuditEvent


def record_audit(
    db: Session,
    *,
    action: str,
    target_type: str,
    target_id: str,
    actor_id: str = "system",
    project_id: str | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        project_id=project_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=to_json(metadata or {}),
    )
    db.add(event)
    db.flush()
    return event


def list_audit_events(db: Session, project_id: str | None = None) -> list[dict]:
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if project_id:
        stmt = stmt.where(AuditEvent.project_id == project_id)
    events = db.scalars(stmt).all()
    return [
        {
            "id": event.id,
            "actor_id": event.actor_id,
            "project_id": event.project_id,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "metadata": from_json(event.metadata_json, {}),
            "created_at": event.created_at,
        }
        for event in events
    ]

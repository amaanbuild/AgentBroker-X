"""Audit trail service - append-only event log for every economy action."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditEvent


def record(
    db: Session,
    *,
    action: str,
    actor: str = "system",
    entity_type: str = "",
    entity_id: str | None = None,
    job_id: str | None = None,
    agent_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    """Write one immutable audit row. Caller is responsible for committing."""
    event = AuditEvent(
        action=action,
        actor=actor,
        entity_type=entity_type,
        entity_id=entity_id,
        job_id=job_id,
        agent_id=agent_id,
        payload=payload or {},
    )
    db.add(event)
    db.flush()
    return event

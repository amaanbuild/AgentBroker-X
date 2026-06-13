"""Audit trail endpoints - query the immutable action log."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


def _serialize(e: AuditEvent) -> dict:
    return {
        "id": e.id,
        "actor": e.actor,
        "action": e.action,
        "entity_type": e.entity_type,
        "entity_id": e.entity_id,
        "job_id": e.job_id,
        "agent_id": e.agent_id,
        "payload": e.payload,
        "at": e.created_at.isoformat(),
    }


@router.get("/job/{job_id}")
def audit_for_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.job_id == job_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    return {"job_id": job_id, "count": len(events), "events": [_serialize(e) for e in events]}


@router.get("/agent/{agent_id}")
def audit_for_agent(agent_id: str, db: Session = Depends(get_db)) -> dict:
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.agent_id == agent_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    return {"agent_id": agent_id, "count": len(events), "events": [_serialize(e) for e in events]}

"""Reputation engine endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Agent, ReputationEvent
from ..schemas import RateRequest, ReputationOut
from ..services import reputation

router = APIRouter(prefix="/reputation", tags=["Reputation Engine"])


@router.get("/{agent_id}", response_model=ReputationOut)
def get_reputation(agent_id: str, db: Session = Depends(get_db)) -> ReputationOut:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    events = (
        db.query(ReputationEvent)
        .filter(ReputationEvent.agent_id == agent_id)
        .order_by(ReputationEvent.created_at.desc())
        .limit(50)
        .all()
    )
    return ReputationOut(
        agent_id=agent.id,
        reputation=agent.reputation,
        successful_jobs=agent.successful_jobs,
        failed_jobs=agent.failed_jobs,
        total_ratings=agent.total_ratings,
        avg_rating=agent.avg_rating,
        trust_tier=reputation.trust_tier(agent.reputation),
        history=[
            {
                "kind": e.kind,
                "rating": e.rating,
                "delta": e.delta,
                "reason": e.reason,
                "task_id": e.related_task_id,
                "at": e.created_at.isoformat(),
            }
            for e in events
        ],
    )


@router.post("/rate", response_model=ReputationOut)
def rate_agent(payload: RateRequest, db: Session = Depends(get_db)) -> ReputationOut:
    agent = db.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    reputation.record_rating(
        db, agent, rating=payload.rating, task_id=payload.task_id, reason=payload.reason
    )
    db.commit()
    return get_reputation(payload.agent_id, db)

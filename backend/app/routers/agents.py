"""Agent registry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Agent
from ..schemas import AgentCreate, AgentOut, AgentSearchResult
from ..services import audit, discovery, reputation

router = APIRouter(prefix="/agents", tags=["Agent Registry"])


@router.post("/register", response_model=AgentOut, status_code=201)
def register_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> Agent:
    agent = Agent(
        name=payload.name,
        description=payload.description,
        skills=payload.skills,
        endpoint=payload.endpoint,
        price_per_task=payload.price_per_task,
        avg_latency_ms=payload.avg_latency_ms,
        metadata_json=payload.metadata,
        balance=settings.default_starting_balance,
    )
    reputation.recompute(agent)
    db.add(agent)
    db.flush()
    audit.record(
        db,
        action="agent.registered",
        entity_type="agent",
        entity_id=agent.id,
        agent_id=agent.id,
        payload={"name": agent.name, "skills": agent.skills},
    )
    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentOut])
def list_agents(
    skill: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[Agent]:
    q = db.query(Agent)
    agents = q.all()
    if skill:
        agents = [a for a in agents if skill.lower() in [s.lower() for s in a.skills]]
    return agents


@router.get("/search", response_model=list[AgentSearchResult])
def search_agents(
    skill: str | None = Query(None, description="Skill to match"),
    max_price: float | None = Query(None),
    min_reputation: float | None = Query(None),
    max_latency_ms: int | None = Query(None),
    available_only: bool = Query(True),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
) -> list[AgentSearchResult]:
    ranked = discovery.rank(
        db,
        skill=skill,
        max_price=max_price,
        min_reputation=min_reputation,
        max_latency_ms=max_latency_ms,
        available_only=available_only,
        limit=limit,
    )
    out: list[AgentSearchResult] = []
    for agent, score, reason in ranked:
        item = AgentSearchResult.model_validate(agent)
        item.match_score = score
        item.match_reason = reason
        out.append(item)
    return out


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

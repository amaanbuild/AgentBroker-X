"""SKILL.md generator endpoint - produce a NANDA-compatible manifest."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Agent
from ..schemas import SkillMDRequest, SkillMDResponse
from ..services import skillmd

router = APIRouter(prefix="/skillmd", tags=["SkillMD Generator"])


@router.post("/generate", response_model=SkillMDResponse)
def generate_skillmd(payload: SkillMDRequest, db: Session = Depends(get_db)) -> SkillMDResponse:
    name = payload.name
    description = payload.description or ""
    skills = payload.skills
    endpoint = payload.endpoint
    agent_id = payload.agent_id

    if payload.agent_id:
        agent = db.get(Agent, payload.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        name = name or agent.name
        description = description or agent.description
        skills = skills or agent.skills
        endpoint = endpoint or agent.endpoint

    if not name:
        raise HTTPException(status_code=422, detail="name or agent_id is required")

    md, manifest = skillmd.generate(
        name=name, description=description, skills=skills,
        endpoint=endpoint, agent_id=agent_id,
    )
    return SkillMDResponse(skillmd=md, json_manifest=manifest)

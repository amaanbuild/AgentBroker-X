"""Multi-agent demo endpoints - seed agents and run the full economy."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..seed import seed_agents
from ..services import demo

router = APIRouter(prefix="/demo", tags=["Multi-Agent Demo"])


@router.post("/seed")
def seed(db: Session = Depends(get_db)) -> dict:
    """(Re)create the demo agent roster. Idempotent."""
    agents = seed_agents(db)
    return {
        "seeded": len(agents),
        "agents": [{"id": a.id, "name": a.name, "skills": a.skills} for a in agents],
    }


@router.post("/run")
def run(db: Session = Depends(get_db)) -> dict:
    """Execute the autonomous ResearchAgent → Data → Writer → Reviewer workflow."""
    return demo.run_demo(db)

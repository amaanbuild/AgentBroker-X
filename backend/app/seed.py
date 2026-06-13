"""Seed data - the demo agent roster for AgentBroker X."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .config import settings
from .models import Agent, AgentStatus
from .services import reputation

SEED_AGENTS = [
    {
        "name": "ResearchAgent",
        "description": "Orchestrates market research by hiring specialist agents.",
        "skills": ["research", "orchestration", "market-analysis"],
        "endpoint": "https://agents.agentbroker.x/research",
        "price_per_task": 40.0, "avg_latency_ms": 1500,
        "successful_jobs": 24, "failed_jobs": 1, "ratings": [5, 5, 4, 5, 5],
    },
    {
        "name": "DataAgent",
        "description": "Sources and structures market data with cited references.",
        "skills": ["market-data", "data-collection", "analytics"],
        "endpoint": "https://agents.agentbroker.x/data",
        "price_per_task": 16.0, "avg_latency_ms": 900,
        "successful_jobs": 58, "failed_jobs": 2, "ratings": [5, 5, 5, 4, 5, 5],
    },
    {
        "name": "DataAgentLite",
        "description": "Budget market data provider, slower but cheap.",
        "skills": ["market-data", "data-collection"],
        "endpoint": "https://agents.agentbroker.x/data-lite",
        "price_per_task": 9.0, "avg_latency_ms": 4200,
        "successful_jobs": 12, "failed_jobs": 5, "ratings": [3, 4, 3, 4],
    },
    {
        "name": "WriterAgent",
        "description": "Drafts executive briefs and reports from structured inputs.",
        "skills": ["report-writing", "writing", "summarization"],
        "endpoint": "https://agents.agentbroker.x/writer",
        "price_per_task": 20.0, "avg_latency_ms": 1800,
        "successful_jobs": 41, "failed_jobs": 1, "ratings": [5, 5, 5, 5, 4],
    },
    {
        "name": "ReviewerAgent",
        "description": "Quality-gates outputs against rubrics; returns pass/fail.",
        "skills": ["quality-review", "verification", "editing"],
        "endpoint": "https://agents.agentbroker.x/reviewer",
        "price_per_task": 14.0, "avg_latency_ms": 1100,
        "successful_jobs": 33, "failed_jobs": 0, "ratings": [5, 5, 5, 5],
    },
    {
        "name": "TranslatorAgent",
        "description": "Translates reports across 30+ languages.",
        "skills": ["translation", "localization"],
        "endpoint": "https://agents.agentbroker.x/translator",
        "price_per_task": 12.0, "avg_latency_ms": 1300,
        "successful_jobs": 19, "failed_jobs": 1, "ratings": [5, 4, 5],
    },
]


def seed_agents(db: Session) -> list[Agent]:
    """Insert demo agents if they don't already exist (idempotent by name)."""
    created: list[Agent] = []
    for spec in SEED_AGENTS:
        existing = db.query(Agent).filter(Agent.name == spec["name"]).first()
        if existing:
            created.append(existing)
            continue
        agent = Agent(
            name=spec["name"],
            description=spec["description"],
            skills=spec["skills"],
            endpoint=spec["endpoint"],
            price_per_task=spec["price_per_task"],
            avg_latency_ms=spec["avg_latency_ms"],
            status=AgentStatus.available,
            successful_jobs=spec["successful_jobs"],
            failed_jobs=spec["failed_jobs"],
            total_ratings=len(spec["ratings"]),
            rating_sum=float(sum(spec["ratings"])),
            balance=settings.default_starting_balance,
        )
        reputation.recompute(agent)
        db.add(agent)
        created.append(agent)
    db.commit()
    for a in created:
        db.refresh(a)
    return created


if __name__ == "__main__":
    from .database import SessionLocal, init_db

    init_db()
    with SessionLocal() as session:
        agents = seed_agents(session)
        print(f"Seeded {len(agents)} agents:")
        for a in agents:
            print(f"  - {a.name:16} rep={a.reputation:5.1f}  skills={a.skills}")

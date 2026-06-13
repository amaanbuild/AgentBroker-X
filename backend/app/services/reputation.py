"""Reputation engine - trust scoring from job outcomes and ratings.

Trust score is a 0-100 blend of three signals:

    success_ratio  (50%)  - completed vs failed jobs
    avg_rating     (35%)  - peer ratings, 0-5 scaled to 0-100
    volume_bonus   (15%)  - log-scaled experience, rewards proven agents

New agents start at a neutral 50 so they are discoverable but unproven.
"""
from __future__ import annotations

import math

from sqlalchemy.orm import Session

from ..models import Agent, ReputationEvent
from . import audit


def _trust_tier(score: float) -> str:
    if score >= 85:
        return "elite"
    if score >= 70:
        return "trusted"
    if score >= 50:
        return "established"
    if score >= 30:
        return "emerging"
    return "unproven"


def recompute(agent: Agent) -> float:
    """Recompute and store the denormalized reputation score for an agent."""
    # Column defaults are applied at flush time, so freshly constructed agents
    # may still carry None here - coerce to zero for the computation.
    agent.successful_jobs = agent.successful_jobs or 0
    agent.failed_jobs = agent.failed_jobs or 0
    agent.total_ratings = agent.total_ratings or 0
    agent.rating_sum = agent.rating_sum or 0.0
    total_jobs = agent.successful_jobs + agent.failed_jobs
    if total_jobs == 0:
        success_ratio = 0.5  # neutral prior
    else:
        success_ratio = agent.successful_jobs / total_jobs

    avg_rating = (agent.rating_sum / agent.total_ratings) if agent.total_ratings else 2.5
    rating_component = avg_rating / 5.0

    volume_bonus = min(1.0, math.log10(total_jobs + 1) / 2.0)  # saturates ~100 jobs

    score = (
        success_ratio * 50.0
        + rating_component * 35.0
        + volume_bonus * 15.0
    )
    agent.reputation = round(min(100.0, max(0.0, score)), 2)
    return agent.reputation


def record_job_outcome(
    db: Session, agent: Agent, *, success: bool, task_id: str | None, reason: str = ""
) -> None:
    """Update job counters and reputation after a task resolves."""
    if success:
        agent.successful_jobs += 1
    else:
        agent.failed_jobs += 1

    before = agent.reputation
    recompute(agent)
    db.add(
        ReputationEvent(
            agent_id=agent.id,
            kind="job_success" if success else "job_failure",
            delta=round(agent.reputation - before, 2),
            reason=reason,
            related_task_id=task_id,
        )
    )
    audit.record(
        db,
        action="reputation.job_outcome",
        agent_id=agent.id,
        entity_type="agent",
        entity_id=agent.id,
        payload={"success": success, "reputation": agent.reputation, "task_id": task_id},
    )


def record_rating(
    db: Session, agent: Agent, *, rating: float, task_id: str | None, reason: str = ""
) -> None:
    agent.total_ratings += 1
    agent.rating_sum += rating
    before = agent.reputation
    recompute(agent)
    db.add(
        ReputationEvent(
            agent_id=agent.id,
            kind="rating",
            rating=rating,
            delta=round(agent.reputation - before, 2),
            reason=reason,
            related_task_id=task_id,
        )
    )
    audit.record(
        db,
        action="reputation.rated",
        agent_id=agent.id,
        entity_type="agent",
        entity_id=agent.id,
        payload={"rating": rating, "reputation": agent.reputation},
    )


def trust_tier(score: float) -> str:
    return _trust_tier(score)

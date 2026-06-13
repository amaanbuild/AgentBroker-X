"""Agent supervisor - monitor active jobs and auto-reassign on failure.

The supervisor is what makes the economy self-healing: if an assignee times
out, dies, or abandons a task, the supervisor penalises it, finds the next
best available agent via the discovery engine, and re-delegates - no human
intervention.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Agent, AgentStatus, Task, TaskStatus
from . import audit, discovery, reputation

ACTIVE_STATES = (TaskStatus.assigned, TaskStatus.in_progress, TaskStatus.submitted)


def _seconds_since(ts: datetime | None) -> float | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds()


def detect_stalls(db: Session) -> list[dict]:
    """Return active tasks that have breached timeout or heartbeat grace."""
    stalled = []
    tasks = db.query(Task).filter(Task.status.in_(ACTIVE_STATES)).all()
    for t in tasks:
        elapsed = _seconds_since(t.started_at)
        hb = _seconds_since(t.last_heartbeat)
        reason = None
        if elapsed is not None and elapsed > t.deadline_seconds:
            reason = "timeout"
        elif hb is not None and hb > 45:
            reason = "abandonment"
        if reason:
            stalled.append({"task_id": t.id, "reason": reason, "elapsed": elapsed})
    return stalled


def reassign(db: Session, task: Task, reason: str = "timeout") -> Task:
    """Penalise the failing assignee and delegate to the next best agent."""
    failed_assignee = db.get(Agent, task.assignee_id) if task.assignee_id else None
    if failed_assignee:
        reputation.record_job_outcome(
            db, failed_assignee, success=False, task_id=task.id,
            reason=f"reassigned ({reason})",
        )
        failed_assignee.status = AgentStatus.available

    # Find a replacement, excluding the agent that just failed.
    ranked = discovery.rank(db, skill=task.skill, available_only=True, limit=10)
    replacement = next(
        (a for a, _, _ in ranked if a.id != task.assignee_id), None
    )

    audit.record(
        db,
        action="supervisor.reassign",
        entity_type="task",
        entity_id=task.id,
        job_id=task.contract_id,
        agent_id=task.assignee_id,
        payload={"reason": reason, "replacement": replacement.id if replacement else None},
    )

    task.attempts += 1
    if replacement is None:
        task.status = TaskStatus.failed
        task.assignee_id = None
        return task

    task.assignee_id = replacement.id
    task.status = TaskStatus.assigned
    task.started_at = None
    task.last_heartbeat = None
    replacement.status = AgentStatus.busy
    return task

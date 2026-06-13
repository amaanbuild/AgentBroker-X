"""Agent supervisor endpoints - monitor active jobs and reassign failures."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Task, TaskStatus
from ..schemas import ReassignRequest, TaskOut
from ..services import supervisor

router = APIRouter(prefix="/jobs", tags=["Agent Supervisor"])

ACTIVE = (TaskStatus.assigned, TaskStatus.in_progress, TaskStatus.submitted,
          TaskStatus.verifying, TaskStatus.reassigned)


@router.get("/active")
def active_jobs(db: Session = Depends(get_db)) -> dict:
    tasks = db.query(Task).filter(Task.status.in_(ACTIVE)).all()
    stalls = supervisor.detect_stalls(db)
    return {
        "active_count": len(tasks),
        "stalled": stalls,
        "tasks": [TaskOut.model_validate(t).model_dump(mode="json") for t in tasks],
    }


@router.post("/reassign", response_model=TaskOut)
def reassign_job(payload: ReassignRequest, db: Session = Depends(get_db)) -> Task:
    task = db.get(Task, payload.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task = supervisor.reassign(db, task, reason=payload.reason)
    db.commit()
    db.refresh(task)
    return task


@router.post("/sweep")
def sweep(db: Session = Depends(get_db)) -> dict:
    """Detect every stalled task and auto-reassign it in one pass."""
    stalls = supervisor.detect_stalls(db)
    reassigned = []
    for s in stalls:
        task = db.get(Task, s["task_id"])
        if task:
            supervisor.reassign(db, task, reason=s["reason"])
            reassigned.append({"task_id": task.id, "new_assignee": task.assignee_id})
    db.commit()
    return {"detected": len(stalls), "reassigned": reassigned}

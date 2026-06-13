"""Task delegation endpoints - create, assign, start, submit, complete.

This router owns the work lifecycle and ties together verification, escrow
release, and reputation updates when a task completes - the autonomous
settlement loop.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Agent,
    AgentStatus,
    Contract,
    ContractStatus,
    Escrow,
    EscrowStatus,
    Task,
    TaskStatus,
    Verification,
)
from ..schemas import (
    TaskAction,
    TaskAssign,
    TaskCreate,
    TaskOut,
    TaskSubmit,
)
from ..services import audit, escrow as escrow_service, reputation, verification

router = APIRouter(prefix="/tasks", tags=["Task Delegation"])


def _get_task(db: Session, task_id: str) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/create", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    task = Task(
        requester_id=payload.requester_id,
        skill=payload.skill,
        spec=payload.spec,
        acceptance_criteria=payload.acceptance_criteria,
        contract_id=payload.contract_id,
        deadline_seconds=payload.deadline_seconds,
        status=TaskStatus.created,
    )
    db.add(task)
    db.flush()
    audit.record(db, action="task.created", entity_type="task", entity_id=task.id,
                 job_id=task.contract_id, agent_id=task.requester_id,
                 payload={"skill": task.skill})
    db.commit()
    db.refresh(task)
    return task


@router.post("/assign", response_model=TaskOut)
def assign_task(payload: TaskAssign, db: Session = Depends(get_db)) -> Task:
    task = _get_task(db, payload.task_id)
    assignee = db.get(Agent, payload.assignee_id)
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")
    task.assignee_id = assignee.id
    task.status = TaskStatus.assigned
    assignee.status = AgentStatus.busy
    audit.record(db, action="task.assigned", entity_type="task", entity_id=task.id,
                 job_id=task.contract_id, agent_id=assignee.id, payload={})
    db.commit()
    db.refresh(task)
    return task


@router.post("/start", response_model=TaskOut)
def start_task(payload: TaskAction, db: Session = Depends(get_db)) -> Task:
    task = _get_task(db, payload.task_id)
    if task.status not in (TaskStatus.assigned, TaskStatus.reassigned):
        raise HTTPException(status_code=409, detail=f"Cannot start task in {task.status}")
    now = datetime.now(timezone.utc)
    task.status = TaskStatus.in_progress
    task.started_at = now
    task.last_heartbeat = now
    audit.record(db, action="task.started", entity_type="task", entity_id=task.id,
                 job_id=task.contract_id, agent_id=task.assignee_id, payload={})
    db.commit()
    db.refresh(task)
    return task


@router.post("/submit", response_model=TaskOut)
def submit_task(payload: TaskSubmit, db: Session = Depends(get_db)) -> Task:
    task = _get_task(db, payload.task_id)
    if task.status not in (TaskStatus.in_progress, TaskStatus.assigned):
        raise HTTPException(status_code=409, detail=f"Cannot submit in {task.status}")
    task.result = payload.result
    task.status = TaskStatus.submitted
    task.last_heartbeat = datetime.now(timezone.utc)
    audit.record(db, action="task.submitted", entity_type="task", entity_id=task.id,
                 job_id=task.contract_id, agent_id=task.assignee_id,
                 payload={"result_keys": list(payload.result.keys())})
    db.commit()
    db.refresh(task)
    return task


@router.post("/complete", response_model=TaskOut)
def complete_task(payload: TaskAction, db: Session = Depends(get_db)) -> Task:
    """Verify, settle escrow, and update reputation - the autonomous close-out.

    On a passing verification: release escrow to the provider and credit a
    successful job. On failure: refund the requester and penalise the provider.
    """
    task = _get_task(db, payload.task_id)
    if task.result is None:
        raise HTTPException(status_code=409, detail="No result submitted to verify")

    task.status = TaskStatus.verifying
    verdict, score, checks, notes = verification.verify(task)
    record = Verification(
        task_id=task.id, verdict=verdict, score=score, checks=checks, notes=notes
    )
    db.add(record)
    audit.record(db, action="task.verified", entity_type="task", entity_id=task.id,
                 job_id=task.contract_id, agent_id=task.assignee_id,
                 payload={"verdict": verdict.value, "score": score})

    escrow = (
        db.query(Escrow).filter(Escrow.contract_id == task.contract_id).first()
        if task.contract_id
        else None
    )
    assignee = db.get(Agent, task.assignee_id) if task.assignee_id else None

    if verdict.value == "passed":
        task.status = TaskStatus.completed
        if escrow and escrow.status == EscrowStatus.funded:
            escrow_service.release(db, escrow)
        if task.contract_id:
            contract = db.get(Contract, task.contract_id)
            if contract:
                contract.status = ContractStatus.completed
        if assignee:
            reputation.record_job_outcome(db, assignee, success=True,
                                          task_id=task.id, reason="task verified")
            assignee.status = AgentStatus.available
    else:
        task.status = TaskStatus.failed
        if escrow and escrow.status == EscrowStatus.funded:
            escrow_service.refund(db, escrow)
        if assignee:
            reputation.record_job_outcome(db, assignee, success=False,
                                          task_id=task.id, reason="verification failed")
            assignee.status = AgentStatus.available

    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> Task:
    return _get_task(db, task_id)

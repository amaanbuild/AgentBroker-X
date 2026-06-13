"""Verification engine endpoint - validate a task output on demand."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Task, Verification
from ..schemas import VerificationOut, VerifyRequest
from ..services import audit, verification

router = APIRouter(prefix="/verify", tags=["Verification Engine"])


@router.post("/task", response_model=VerificationOut)
def verify_task(payload: VerifyRequest, db: Session = Depends(get_db)) -> Verification:
    task = db.get(Task, payload.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.result is None:
        raise HTTPException(status_code=409, detail="Task has no submitted result")

    verdict, score, checks, notes = verification.verify(task)
    record = Verification(
        task_id=task.id, verdict=verdict, score=score, checks=checks, notes=notes
    )
    db.add(record)
    audit.record(db, action="verify.run", entity_type="task", entity_id=task.id,
                 job_id=task.contract_id, payload={"verdict": verdict.value, "score": score})
    db.commit()
    db.refresh(record)
    return record

"""Escrow payment endpoints - lock, release, refund."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Contract, ContractStatus, Escrow
from ..schemas import EscrowAction, EscrowCreate, EscrowOut
from ..services import escrow as escrow_service

router = APIRouter(prefix="/escrow", tags=["Escrow Payments"])


@router.post("/create", response_model=EscrowOut, status_code=201)
def create_escrow(payload: EscrowCreate, db: Session = Depends(get_db)) -> Escrow:
    contract = db.get(Contract, payload.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.status not in (ContractStatus.signed, ContractStatus.active):
        raise HTTPException(
            status_code=409, detail="Contract must be signed before funding escrow"
        )
    escrow = escrow_service.create_and_fund(db, contract)
    contract.status = ContractStatus.active
    db.commit()
    db.refresh(escrow)
    return escrow


@router.post("/release", response_model=EscrowOut)
def release_escrow(payload: EscrowAction, db: Session = Depends(get_db)) -> Escrow:
    escrow = db.get(Escrow, payload.escrow_id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    escrow = escrow_service.release(db, escrow)
    db.commit()
    db.refresh(escrow)
    return escrow


@router.post("/refund", response_model=EscrowOut)
def refund_escrow(payload: EscrowAction, db: Session = Depends(get_db)) -> Escrow:
    escrow = db.get(Escrow, payload.escrow_id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    escrow = escrow_service.refund(db, escrow)
    db.commit()
    db.refresh(escrow)
    return escrow


@router.get("/{escrow_id}", response_model=EscrowOut)
def get_escrow(escrow_id: str, db: Session = Depends(get_db)) -> Escrow:
    escrow = db.get(Escrow, escrow_id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return escrow

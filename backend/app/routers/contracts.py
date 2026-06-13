"""Contract system endpoints - autonomous, dual-signed agreements."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Agent, Contract, ContractStatus, Offer, OfferStatus
from ..schemas import ContractCreate, ContractOut, ContractSign
from ..services import audit

router = APIRouter(prefix="/contracts", tags=["Contract System"])


def _signature(contract_id: str, agent_id: str) -> str:
    return hashlib.sha256(f"{contract_id}:{agent_id}".encode()).hexdigest()[:16]


@router.post("/create", response_model=ContractOut, status_code=201)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db)) -> Contract:
    if payload.offer_id:
        offer = db.get(Offer, payload.offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")
        if offer.status != OfferStatus.accepted:
            raise HTTPException(
                status_code=409, detail="Contract requires an accepted offer"
            )

    contract = Contract(
        offer_id=payload.offer_id,
        requester_id=payload.requester_id,
        provider_id=payload.provider_id,
        skill=payload.skill,
        amount=payload.amount,
        terms=payload.terms,
        deadline_seconds=payload.deadline_seconds,
        status=ContractStatus.draft,
    )
    db.add(contract)
    db.flush()
    audit.record(db, action="contract.created", entity_type="contract",
                 entity_id=contract.id, job_id=contract.id,
                 agent_id=contract.requester_id, payload={"amount": contract.amount})
    db.commit()
    db.refresh(contract)
    return contract


@router.post("/sign", response_model=ContractOut)
def sign_contract(payload: ContractSign, db: Session = Depends(get_db)) -> Contract:
    contract = db.get(Contract, payload.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    sig = _signature(contract.id, payload.actor_id)

    if payload.actor_id == contract.requester_id:
        contract.requester_signature = sig
    elif payload.actor_id == contract.provider_id:
        contract.provider_signature = sig
    else:
        raise HTTPException(status_code=403, detail="Signer is not a party to contract")

    if contract.requester_signature and contract.provider_signature:
        contract.status = ContractStatus.signed

    audit.record(db, action="contract.signed", entity_type="contract",
                 entity_id=contract.id, job_id=contract.id,
                 agent_id=payload.actor_id, payload={"status": contract.status.value})
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: str, db: Session = Depends(get_db)) -> Contract:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract

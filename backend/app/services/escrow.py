"""Escrow service - lock funds before work, release on success, refund on failure."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Agent, Contract, Escrow, EscrowStatus
from . import audit


def create_and_fund(db: Session, contract: Contract) -> Escrow:
    """Create escrow and atomically debit the payer's wallet (locks funds)."""
    payer = db.get(Agent, contract.requester_id)
    if payer.balance < contract.amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient balance: {payer.balance} < {contract.amount}",
        )
    fee = round(contract.amount * settings.platform_fee_bps / 10_000, 2)
    payer.balance = round(payer.balance - contract.amount, 2)  # funds locked

    escrow = Escrow(
        contract_id=contract.id,
        payer_id=contract.requester_id,
        payee_id=contract.provider_id,
        amount=contract.amount,
        fee=fee,
        status=EscrowStatus.funded,
    )
    db.add(escrow)
    db.flush()
    audit.record(
        db,
        action="escrow.funded",
        entity_type="escrow",
        entity_id=escrow.id,
        job_id=contract.id,
        agent_id=contract.requester_id,
        payload={"amount": contract.amount, "fee": fee},
    )
    return escrow


def release(db: Session, escrow: Escrow) -> Escrow:
    """Release locked funds to the payee, minus platform fee."""
    if escrow.status != EscrowStatus.funded:
        raise HTTPException(status_code=409, detail=f"Escrow not funded: {escrow.status}")
    payee = db.get(Agent, escrow.payee_id)
    payout = round(escrow.amount - escrow.fee, 2)
    payee.balance = round(payee.balance + payout, 2)
    escrow.status = EscrowStatus.released
    escrow.released_at = datetime.now(timezone.utc)
    audit.record(
        db,
        action="escrow.released",
        entity_type="escrow",
        entity_id=escrow.id,
        job_id=escrow.contract_id,
        agent_id=escrow.payee_id,
        payload={"payout": payout, "fee": escrow.fee},
    )
    return escrow


def refund(db: Session, escrow: Escrow) -> Escrow:
    """Return locked funds to the payer (work failed / cancelled)."""
    if escrow.status not in (EscrowStatus.funded, EscrowStatus.created):
        raise HTTPException(status_code=409, detail=f"Cannot refund: {escrow.status}")
    payer = db.get(Agent, escrow.payer_id)
    payer.balance = round(payer.balance + escrow.amount, 2)
    escrow.status = EscrowStatus.refunded
    audit.record(
        db,
        action="escrow.refunded",
        entity_type="escrow",
        entity_id=escrow.id,
        job_id=escrow.contract_id,
        agent_id=escrow.payer_id,
        payload={"amount": escrow.amount},
    )
    return escrow

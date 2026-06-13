"""Negotiation engine endpoints - autonomous offer/counter/accept/reject."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Agent, Offer, OfferStatus
from ..schemas import OfferAction, OfferCounter, OfferCreate, OfferOut
from ..services import audit, negotiation

router = APIRouter(prefix="/offers", tags=["Negotiation Engine"])


def _get_offer(db: Session, offer_id: str) -> Offer:
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


@router.post("/create", response_model=OfferOut, status_code=201)
def create_offer(payload: OfferCreate, db: Session = Depends(get_db)) -> Offer:
    for aid in (payload.requester_id, payload.provider_id):
        if not db.get(Agent, aid):
            raise HTTPException(status_code=404, detail=f"Agent {aid} not found")

    offer = Offer(
        requester_id=payload.requester_id,
        provider_id=payload.provider_id,
        skill=payload.skill,
        amount=payload.amount,
        task_spec=payload.task_spec,
        deadline_seconds=payload.deadline_seconds,
        history=[
            {
                "round": 0,
                "actor_id": payload.requester_id,
                "action": "offer",
                "amount": payload.amount,
                "note": "initial offer",
            }
        ],
    )
    # The provider agent responds autonomously the moment the offer lands.
    negotiation.auto_respond(db, offer)
    db.add(offer)
    db.flush()
    audit.record(
        db,
        action="offer.created",
        entity_type="offer",
        entity_id=offer.id,
        agent_id=payload.requester_id,
        payload={"amount": payload.amount, "status": offer.status.value},
    )
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/counter", response_model=OfferOut)
def counter_offer(payload: OfferCounter, db: Session = Depends(get_db)) -> Offer:
    offer = _get_offer(db, payload.offer_id)
    if offer.status in (OfferStatus.accepted, OfferStatus.rejected):
        raise HTTPException(status_code=409, detail=f"Offer is {offer.status.value}")

    offer.rounds += 1
    offer.amount = payload.amount
    offer.status = OfferStatus.pending
    offer.history = list(offer.history or []) + [
        {
            "round": offer.rounds,
            "actor_id": payload.actor_id,
            "action": "counter",
            "amount": payload.amount,
            "note": payload.note,
        }
    ]
    # Provider re-evaluates the new amount autonomously.
    negotiation.auto_respond(db, offer)
    audit.record(
        db,
        action="offer.countered",
        entity_type="offer",
        entity_id=offer.id,
        agent_id=payload.actor_id,
        payload={"amount": payload.amount, "status": offer.status.value},
    )
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/accept", response_model=OfferOut)
def accept_offer(payload: OfferAction, db: Session = Depends(get_db)) -> Offer:
    offer = _get_offer(db, payload.offer_id)
    offer.status = OfferStatus.accepted
    offer.history = list(offer.history or []) + [
        {"round": offer.rounds, "actor_id": payload.actor_id, "action": "accept",
         "amount": offer.amount, "note": "manually accepted"}
    ]
    audit.record(db, action="offer.accepted", entity_type="offer", entity_id=offer.id,
                 agent_id=payload.actor_id, payload={"amount": offer.amount})
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/reject", response_model=OfferOut)
def reject_offer(payload: OfferAction, db: Session = Depends(get_db)) -> Offer:
    offer = _get_offer(db, payload.offer_id)
    offer.status = OfferStatus.rejected
    offer.history = list(offer.history or []) + [
        {"round": offer.rounds, "actor_id": payload.actor_id, "action": "reject",
         "amount": offer.amount, "note": "manually rejected"}
    ]
    audit.record(db, action="offer.rejected", entity_type="offer", entity_id=offer.id,
                 agent_id=payload.actor_id, payload={})
    db.commit()
    db.refresh(offer)
    return offer


@router.get("/{offer_id}", response_model=OfferOut)
def get_offer(offer_id: str, db: Session = Depends(get_db)) -> Offer:
    return _get_offer(db, offer_id)

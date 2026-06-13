"""Negotiation engine - autonomous offer/counter logic between agents.

The provider runs a simple reservation-price strategy: it accepts any offer
at or above its `price_per_task`, otherwise it counters by meeting the
requester partway (bounded by its reservation price). This lets two agents
converge on a price with no human in the loop.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Agent, Offer, OfferStatus

MAX_ROUNDS = 5


def _append_history(offer: Offer, actor_id: str, action: str, amount: float, note: str = "") -> None:
    entry = {
        "round": offer.rounds,
        "actor_id": actor_id,
        "action": action,
        "amount": round(amount, 2),
        "note": note,
    }
    # SQLAlchemy needs a new list object to detect JSON mutation.
    offer.history = list(offer.history or []) + [entry]


def auto_respond(db: Session, offer: Offer) -> Offer:
    """Provider agent evaluates a pending offer and accepts or counters.

    Returns the offer with an updated status. This is the autonomous core:
    no human decides - the provider's reservation price does.
    """
    # Column defaults apply at flush; coerce in case auto_respond runs first.
    offer.rounds = offer.rounds or 0
    offer.history = offer.history or []
    provider = db.get(Agent, offer.provider_id)
    reservation = provider.price_per_task if provider else offer.amount

    if offer.amount >= reservation:
        offer.status = OfferStatus.accepted
        _append_history(offer, offer.provider_id, "accept", offer.amount,
                        "offer meets reservation price")
        return offer

    if offer.rounds >= MAX_ROUNDS:
        offer.status = OfferStatus.rejected
        _append_history(offer, offer.provider_id, "reject", offer.amount,
                        "max negotiation rounds reached")
        return offer

    # Counter: split the gap between the offer and the reservation price.
    counter_amount = round((offer.amount + reservation) / 2, 2)
    offer.rounds += 1
    offer.amount = counter_amount
    offer.status = OfferStatus.countered
    _append_history(offer, offer.provider_id, "counter", counter_amount,
                    "meeting requester partway")
    return offer

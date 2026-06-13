"""Multi-agent demo orchestration.

Runs the full autonomous economy end-to-end with four real agents:

    ResearchAgent (requester / orchestrator)
        → discovers + hires DataAgent     (market data)
        → discovers + hires WriterAgent    (report draft)
        → discovers + hires ReviewerAgent  (quality gate)
    Payment released at every successful step; reputation updated.

Every step is logged so the frontend can render the workflow as a timeline.
"""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    Agent,
    AgentStatus,
    Contract,
    ContractStatus,
    Offer,
    OfferStatus,
    Task,
    TaskStatus,
    Verification,
)
from . import audit, discovery, escrow as escrow_service, negotiation, reputation, verification


def _sig(contract_id: str, agent_id: str) -> str:
    return hashlib.sha256(f"{contract_id}:{agent_id}".encode()).hexdigest()[:16]


def _hire(
    db: Session,
    *,
    requester: Agent,
    skill: str,
    spec: dict,
    acceptance: dict,
    result: dict,
    opening_bid: float,
    steps: list,
) -> dict:
    """Run discover → negotiate → contract → escrow → delegate → verify → pay."""

    # 1. DISCOVERY -------------------------------------------------------------
    ranked = discovery.rank(db, skill=skill, available_only=True, limit=5)
    ranked = [(a, s, r) for a, s, r in ranked if a.id != requester.id]
    if not ranked:
        raise RuntimeError(f"No available agent for skill '{skill}'")
    provider, match_score, reason = ranked[0]
    steps.append({
        "stage": "discovery", "skill": skill, "provider": provider.name,
        "match_score": match_score, "reason": reason,
        "candidates": [a.name for a, _, _ in ranked],
    })

    # 2. NEGOTIATION -----------------------------------------------------------
    offer = Offer(
        requester_id=requester.id, provider_id=provider.id, skill=skill,
        amount=opening_bid, task_spec=spec,
        history=[{"round": 0, "actor_id": requester.id, "action": "offer",
                  "amount": opening_bid, "note": "opening bid"}],
    )
    negotiation.auto_respond(db, offer)
    # If countered, the requester accepts the counter (it is within budget).
    if offer.status == OfferStatus.countered:
        offer.status = OfferStatus.accepted
        offer.history = list(offer.history) + [
            {"round": offer.rounds, "actor_id": requester.id, "action": "accept",
             "amount": offer.amount, "note": "accepted counter"}
        ]
    db.add(offer)
    db.flush()
    steps.append({
        "stage": "negotiation", "rounds": offer.rounds,
        "final_amount": offer.amount, "status": offer.status.value,
        "history": offer.history,
    })

    # 3. CONTRACT --------------------------------------------------------------
    contract = Contract(
        offer_id=offer.id, requester_id=requester.id, provider_id=provider.id,
        skill=skill, amount=offer.amount, terms={"spec": spec, "acceptance": acceptance},
        status=ContractStatus.draft,
    )
    db.add(contract)
    db.flush()
    contract.requester_signature = _sig(contract.id, requester.id)
    contract.provider_signature = _sig(contract.id, provider.id)
    contract.status = ContractStatus.signed
    steps.append({"stage": "contract", "contract_id": contract.id,
                  "amount": contract.amount, "status": "signed (dual)"})

    # 4. ESCROW ----------------------------------------------------------------
    escrow = escrow_service.create_and_fund(db, contract)
    contract.status = ContractStatus.active
    steps.append({"stage": "escrow", "escrow_id": escrow.id, "locked": escrow.amount,
                  "fee": escrow.fee, "status": escrow.status.value})

    # 5. DELEGATION ------------------------------------------------------------
    task = Task(
        contract_id=contract.id, requester_id=requester.id, assignee_id=provider.id,
        skill=skill, spec=spec, acceptance_criteria=acceptance,
        status=TaskStatus.in_progress,
    )
    provider.status = AgentStatus.busy
    db.add(task)
    db.flush()
    # The provider does the work and submits a result.
    task.result = result
    task.status = TaskStatus.submitted
    steps.append({"stage": "delegation", "task_id": task.id, "assignee": provider.name,
                  "status": "submitted"})

    # 6. VERIFICATION ----------------------------------------------------------
    verdict, score, checks, notes = verification.verify(task)
    db.add(Verification(task_id=task.id, verdict=verdict, score=score,
                        checks=checks, notes=notes))
    steps.append({"stage": "verification", "verdict": verdict.value, "score": score,
                  "checks": checks, "notes": notes})

    # 7. SETTLEMENT + REPUTATION ----------------------------------------------
    if verdict.value == "passed":
        escrow_service.release(db, escrow)
        task.status = TaskStatus.completed
        contract.status = ContractStatus.completed
        reputation.record_job_outcome(db, provider, success=True, task_id=task.id,
                                      reason="demo task verified")
        reputation.record_rating(db, provider, rating=5.0, task_id=task.id,
                                 reason="demo 5-star")
        payout = round(escrow.amount - escrow.fee, 2)
    else:
        escrow_service.refund(db, escrow)
        task.status = TaskStatus.failed
        reputation.record_job_outcome(db, provider, success=False, task_id=task.id,
                                      reason="demo verification failed")
        payout = 0.0
    provider.status = AgentStatus.available

    steps.append({"stage": "settlement", "verdict": verdict.value,
                  "payout": payout, "provider": provider.name,
                  "new_reputation": provider.reputation})

    audit.record(db, action="demo.hire_completed", entity_type="task", entity_id=task.id,
                 job_id=contract.id, agent_id=provider.id,
                 payload={"skill": skill, "verdict": verdict.value, "payout": payout})

    return {
        "skill": skill, "provider": provider.name, "provider_id": provider.id,
        "amount": contract.amount, "verdict": verdict.value, "payout": payout,
        "task_id": task.id, "contract_id": contract.id,
    }


def run_demo(db: Session) -> dict:
    """Execute the full ResearchAgent → Data → Writer → Reviewer pipeline."""
    research = db.query(Agent).filter(Agent.name == "ResearchAgent").first()
    if not research:
        raise RuntimeError("Seed data missing - run /demo/seed or seed.py first")

    timeline: list[dict] = []
    hires: list[dict] = []

    # Step 1 - hire DataAgent for market data.
    hires.append(_hire(
        db, requester=research, skill="market-data",
        spec={"topic": "AI agent infrastructure", "region": "global"},
        acceptance={"type": "json", "schema": {
            "properties": {"market_size_usd": {"type": "number"},
                           "cagr_pct": {"type": "number"},
                           "sources": {"type": "array"}},
            "required": ["market_size_usd", "cagr_pct", "sources"]}},
        result={"data": {"market_size_usd": 5_200_000_000, "cagr_pct": 38.4,
                         "sources": ["gartner-2026", "cbinsights"]}},
        opening_bid=18.0, steps=timeline,
    ))

    # Step 2 - hire WriterAgent to draft a report from the data.
    hires.append(_hire(
        db, requester=research, skill="report-writing",
        spec={"input": "market-data", "format": "executive-brief"},
        acceptance={"type": "text", "min_length": 120,
                    "must_include": ["market", "growth", "agent"]},
        result={"text": (
            "Executive Brief: The autonomous AI agent infrastructure market is "
            "experiencing explosive growth, projected at a 38.4% CAGR toward a "
            "multi-billion-dollar valuation. Agent-to-agent commerce - where agents "
            "discover, contract, and pay other agents - is the key growth driver, "
            "with broker networks emerging as critical economic infrastructure."
        )},
        opening_bid=22.0, steps=timeline,
    ))

    # Step 3 - hire ReviewerAgent as a quality gate.
    hires.append(_hire(
        db, requester=research, skill="quality-review",
        spec={"input": "report-draft", "rubric": "clarity,accuracy,completeness"},
        acceptance={"type": "json", "schema": {
            "properties": {"approved": {"type": "boolean"},
                           "score": {"type": "number"},
                           "notes": {"type": "string"}},
            "required": ["approved", "score"]}},
        result={"data": {"approved": True, "score": 9.1,
                         "notes": "Clear, well-sourced, publication-ready."}},
        opening_bid=15.0, steps=timeline,
    ))

    db.commit()

    total_paid = round(sum(h["payout"] for h in hires), 2)
    return {
        "orchestrator": research.name,
        "orchestrator_id": research.id,
        "hires": hires,
        "timeline": timeline,
        "total_paid_out": total_paid,
        "platform_fee_bps": settings.platform_fee_bps,
        "summary": (
            f"{research.name} autonomously discovered, negotiated with, contracted, "
            f"funded, supervised, verified, and paid {len(hires)} agents - "
            f"releasing ${total_paid} with zero human intervention."
        ),
    }

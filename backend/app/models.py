"""SQLAlchemy ORM models - the complete database schema for AgentBroker X.

The schema models an autonomous agent economy:

    Agent  -> Offer <- Agent           (negotiation)
    Offer  -> Contract -> Escrow       (agreement + funds)
    Contract -> Task                   (work)
    Task   -> Verification             (proof of work)
    any    -> AuditEvent               (immutable trail)
    Agent  -> ReputationEvent          (trust accrual)
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class AgentStatus(str, enum.Enum):
    available = "available"
    busy = "busy"
    offline = "offline"


class OfferStatus(str, enum.Enum):
    pending = "pending"
    countered = "countered"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class ContractStatus(str, enum.Enum):
    draft = "draft"
    signed = "signed"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"
    disputed = "disputed"


class EscrowStatus(str, enum.Enum):
    created = "created"
    funded = "funded"
    released = "released"
    refunded = "refunded"


class TaskStatus(str, enum.Enum):
    created = "created"
    assigned = "assigned"
    in_progress = "in_progress"
    submitted = "submitted"
    verifying = "verifying"
    completed = "completed"
    failed = "failed"
    reassigned = "reassigned"


class VerificationVerdict(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    inconclusive = "inconclusive"


# --------------------------------------------------------------------------- #
# Core tables
# --------------------------------------------------------------------------- #
class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # Skills + pricing are stored as JSON for flexible discovery.
    skills: Mapped[list] = mapped_column(JSON, default=list)
    endpoint: Mapped[str] = mapped_column(String(512), default="")
    price_per_task: Mapped[float] = mapped_column(Float, default=10.0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=2000)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.available
    )

    # Reputation (denormalized for fast discovery; source of truth is events).
    reputation: Mapped[float] = mapped_column(Float, default=50.0)
    successful_jobs: Mapped[int] = mapped_column(Integer, default=0)
    failed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    total_ratings: Mapped[int] = mapped_column(Integer, default=0)
    rating_sum: Mapped[float] = mapped_column(Float, default=0.0)

    # Wallet - the economy needs balances to move.
    balance: Mapped[float] = mapped_column(Float, default=1000.0)

    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    reputation_events: Mapped[list["ReputationEvent"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )

    @property
    def avg_rating(self) -> float:
        return round(self.rating_sum / self.total_ratings, 2) if self.total_ratings else 0.0


class ReputationEvent(Base):
    __tablename__ = "reputation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # job_success | job_failure | rating
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, default="")
    related_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    agent: Mapped["Agent"] = relationship(back_populates="reputation_events")


class Offer(Base):
    """A negotiation thread between a requester and a provider agent."""

    __tablename__ = "offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    requester_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    skill: Mapped[str] = mapped_column(String(120))
    task_spec: Mapped[dict] = mapped_column(JSON, default=dict)
    amount: Mapped[float] = mapped_column(Float)
    deadline_seconds: Mapped[int] = mapped_column(Integer, default=120)
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus), default=OfferStatus.pending
    )
    rounds: Mapped[int] = mapped_column(Integer, default=0)
    # Full counter-offer ledger so negotiation history is auditable.
    history: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    offer_id: Mapped[str | None] = mapped_column(
        ForeignKey("offers.id"), nullable=True, index=True
    )
    requester_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    skill: Mapped[str] = mapped_column(String(120))
    terms: Mapped[dict] = mapped_column(JSON, default=dict)
    amount: Mapped[float] = mapped_column(Float)
    deadline_seconds: Mapped[int] = mapped_column(Integer, default=120)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.draft
    )
    requester_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Escrow(Base):
    __tablename__ = "escrows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), index=True)
    payer_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    payee_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    amount: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus), default=EscrowStatus.created
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contract_id: Mapped[str | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True, index=True
    )
    requester_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    assignee_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    skill: Mapped[str] = mapped_column(String(120))
    spec: Mapped[dict] = mapped_column(JSON, default=dict)
    # The verification contract: how the output will be judged.
    acceptance_criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.created
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    deadline_seconds: Mapped[int] = mapped_column(Integer, default=120)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    verdict: Mapped[VerificationVerdict] = mapped_column(Enum(VerificationVerdict))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEvent(Base):
    """Append-only audit trail. Every state transition writes one row."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(60), default="")
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

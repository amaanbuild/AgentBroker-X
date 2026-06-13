"""Pydantic request/response schemas (API contract)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Agents
# --------------------------------------------------------------------------- #
class AgentCreate(BaseModel):
    name: str
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    endpoint: str = ""
    price_per_task: float = 10.0
    avg_latency_ms: int = 2000
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    skills: list[str]
    endpoint: str
    price_per_task: float
    avg_latency_ms: int
    status: str
    reputation: float
    successful_jobs: int
    failed_jobs: int
    avg_rating: float
    balance: float
    created_at: datetime


class AgentSearchResult(AgentOut):
    match_score: float = 0.0
    match_reason: str = ""


# --------------------------------------------------------------------------- #
# Reputation
# --------------------------------------------------------------------------- #
class RateRequest(BaseModel):
    agent_id: str
    rating: float = Field(ge=0, le=5)
    task_id: str | None = None
    reason: str = ""


class ReputationOut(BaseModel):
    agent_id: str
    reputation: float
    successful_jobs: int
    failed_jobs: int
    total_ratings: int
    avg_rating: float
    trust_tier: str
    history: list[dict[str, Any]]


# --------------------------------------------------------------------------- #
# Negotiation
# --------------------------------------------------------------------------- #
class OfferCreate(BaseModel):
    requester_id: str
    provider_id: str
    skill: str
    amount: float
    task_spec: dict[str, Any] = Field(default_factory=dict)
    deadline_seconds: int = 120


class OfferCounter(BaseModel):
    offer_id: str
    actor_id: str
    amount: float
    note: str = ""


class OfferAction(BaseModel):
    offer_id: str
    actor_id: str


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requester_id: str
    provider_id: str
    skill: str
    amount: float
    status: str
    rounds: int
    deadline_seconds: int
    history: list[dict[str, Any]]
    created_at: datetime


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #
class ContractCreate(BaseModel):
    offer_id: str | None = None
    requester_id: str
    provider_id: str
    skill: str
    amount: float
    terms: dict[str, Any] = Field(default_factory=dict)
    deadline_seconds: int = 120


class ContractSign(BaseModel):
    contract_id: str
    actor_id: str


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    offer_id: str | None
    requester_id: str
    provider_id: str
    skill: str
    amount: float
    status: str
    terms: dict[str, Any]
    requester_signature: str | None
    provider_signature: str | None
    created_at: datetime


# --------------------------------------------------------------------------- #
# Escrow
# --------------------------------------------------------------------------- #
class EscrowCreate(BaseModel):
    contract_id: str


class EscrowAction(BaseModel):
    escrow_id: str


class EscrowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    payer_id: str
    payee_id: str
    amount: float
    fee: float
    status: str
    created_at: datetime
    released_at: datetime | None


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #
class TaskCreate(BaseModel):
    requester_id: str
    skill: str
    spec: dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria: dict[str, Any] = Field(default_factory=dict)
    contract_id: str | None = None
    deadline_seconds: int = 120


class TaskAssign(BaseModel):
    task_id: str
    assignee_id: str


class TaskAction(BaseModel):
    task_id: str


class TaskSubmit(BaseModel):
    task_id: str
    result: dict[str, Any]


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str | None
    requester_id: str
    assignee_id: str | None
    skill: str
    spec: dict[str, Any]
    acceptance_criteria: dict[str, Any]
    result: dict[str, Any] | None
    status: str
    attempts: int
    deadline_seconds: int
    created_at: datetime


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
class VerifyRequest(BaseModel):
    task_id: str


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    verdict: str
    score: float
    checks: list[dict[str, Any]]
    notes: str
    created_at: datetime


# --------------------------------------------------------------------------- #
# Supervisor
# --------------------------------------------------------------------------- #
class ReassignRequest(BaseModel):
    task_id: str
    reason: str = "manual"


# --------------------------------------------------------------------------- #
# SkillMD
# --------------------------------------------------------------------------- #
class SkillMDRequest(BaseModel):
    agent_id: str | None = None
    name: str | None = None
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    endpoint: str | None = None


class SkillMDResponse(BaseModel):
    skillmd: str
    json_manifest: dict[str, Any]

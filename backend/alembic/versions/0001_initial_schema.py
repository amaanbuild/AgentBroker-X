"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-14 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, index=True),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("skills", sa.JSON()),
        sa.Column("endpoint", sa.String(512), default=""),
        sa.Column("price_per_task", sa.Float(), default=10.0),
        sa.Column("avg_latency_ms", sa.Integer(), default=2000),
        sa.Column("status", sa.String(20), default="available"),
        sa.Column("reputation", sa.Float(), default=50.0),
        sa.Column("successful_jobs", sa.Integer(), default=0),
        sa.Column("failed_jobs", sa.Integer(), default=0),
        sa.Column("total_ratings", sa.Integer(), default=0),
        sa.Column("rating_sum", sa.Float(), default=0.0),
        sa.Column("balance", sa.Float(), default=1000.0),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "reputation_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), index=True),
        sa.Column("kind", sa.String(40)),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("delta", sa.Float(), default=0.0),
        sa.Column("reason", sa.Text(), default=""),
        sa.Column("related_task_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "offers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("agents.id"), index=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("agents.id"), index=True),
        sa.Column("skill", sa.String(120)),
        sa.Column("task_spec", sa.JSON()),
        sa.Column("amount", sa.Float()),
        sa.Column("deadline_seconds", sa.Integer(), default=120),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("rounds", sa.Integer(), default=0),
        sa.Column("history", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("offer_id", sa.String(36), sa.ForeignKey("offers.id"), nullable=True, index=True),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("agents.id"), index=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("agents.id"), index=True),
        sa.Column("skill", sa.String(120)),
        sa.Column("terms", sa.JSON()),
        sa.Column("amount", sa.Float()),
        sa.Column("deadline_seconds", sa.Integer(), default=120),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("requester_signature", sa.String(64), nullable=True),
        sa.Column("provider_signature", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "escrows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), index=True),
        sa.Column("payer_id", sa.String(36), sa.ForeignKey("agents.id")),
        sa.Column("payee_id", sa.String(36), sa.ForeignKey("agents.id")),
        sa.Column("amount", sa.Float()),
        sa.Column("fee", sa.Float(), default=0.0),
        sa.Column("status", sa.String(20), default="created"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=True, index=True),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("agents.id"), index=True),
        sa.Column("assignee_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=True, index=True),
        sa.Column("skill", sa.String(120)),
        sa.Column("spec", sa.JSON()),
        sa.Column("acceptance_criteria", sa.JSON()),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), default="created"),
        sa.Column("attempts", sa.Integer(), default=0),
        sa.Column("deadline_seconds", sa.Integer(), default=120),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), index=True),
        sa.Column("verdict", sa.String(20)),
        sa.Column("score", sa.Float(), default=0.0),
        sa.Column("checks", sa.JSON()),
        sa.Column("notes", sa.Text(), default=""),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), nullable=True, index=True),
        sa.Column("agent_id", sa.String(36), nullable=True, index=True),
        sa.Column("actor", sa.String(120), default="system"),
        sa.Column("action", sa.String(120), index=True),
        sa.Column("entity_type", sa.String(60), default=""),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in (
        "audit_events", "verifications", "tasks", "escrows",
        "contracts", "offers", "reputation_events", "agents",
    ):
        op.drop_table(table)

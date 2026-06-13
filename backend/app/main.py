"""AgentBroker X - FastAPI application entrypoint.

Wires together the twelve modules of the autonomous agent economy and exposes
a single OpenAPI surface at /docs.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import (
    agents,
    audit,
    contracts,
    demo,
    escrow,
    negotiation,
    reputation,
    skillmd,
    supervisor,
    tasks,
    verification,
)

DESCRIPTION = """
**AgentBroker X** is an autonomous agent economy network where AI agents
**discover, negotiate with, contract, supervise, verify, replace, and pay**
other AI agents - with no human in the loop.

Built for **NANDAHack 2026** (MIT Media Lab + HCLTech).

Lifecycle: `discover → negotiate → contract → escrow → delegate → verify →
settle → reputation`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on boot. Never block startup on the database: /health must
    # respond so the platform marks the service live even if the DB is briefly
    # unreachable. Schema is retried inside init_db().
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] database not ready, continuing without init: {exc}")
    yield


app = FastAPI(
    title="AgentBroker X",
    description=DESCRIPTION,
    version="1.0.0",
    contact={"name": "Amaan Khan", "url": "https://github.com/amaancoderx"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    agents.router,
    reputation.router,
    negotiation.router,
    contracts.router,
    escrow.router,
    tasks.router,
    verification.router,
    supervisor.router,
    audit.router,
    skillmd.router,
    demo.router,
):
    app.include_router(r, prefix=settings.api_prefix)


@app.get("/", tags=["Meta"])
def root() -> dict:
    return {
        "name": "AgentBroker X",
        "tagline": "Autonomous Agent Economy Network",
        "author": "Amaan Khan",
        "event": "NANDAHack 2026 - MIT Media Lab + HCLTech",
        "docs": "/docs",
        "modules": [
            "agent-registry", "reputation-engine", "discovery-engine",
            "negotiation-engine", "contract-system", "escrow-payments",
            "task-delegation", "verification-engine", "agent-supervisor",
            "audit-trail", "skillmd-generator", "multi-agent-demo",
        ],
    }


@app.get("/health", tags=["Meta"])
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}

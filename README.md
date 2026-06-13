<div align="center">

# AgentBroker X

### Autonomous Agent Economy Network

**An economy where AI agents hire AI agents.**
Agents discover, negotiate, contract, supervise, verify, replace, and pay other agents with zero human intervention.

<br/>

[![NANDAHack 2026](https://img.shields.io/badge/NANDAHack-2026-6366f1?style=for-the-badge)](https://www.nanda.media.mit.edu/)
[![MIT Media Lab](https://img.shields.io/badge/MIT-Media%20Lab-a4123f?style=for-the-badge)](https://www.media.mit.edu/)
[![HCLTech](https://img.shields.io/badge/HCLTech-Partner-0f62fe?style=for-the-badge)](https://www.hcltech.com/)

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-6%20passing-brightgreen?style=flat-square)](backend/tests)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/amaancoderx/AgentBroker-X/pulls)

<br/>

`discover` &rarr; `negotiate` &rarr; `contract` &rarr; `escrow` &rarr; `delegate` &rarr; `verify` &rarr; `settle` &rarr; `reputation`

</div>

---

## Table of Contents

- [Why AgentBroker X](#why-agentbroker-x)
- [The Autonomous Loop](#the-autonomous-loop)
- [Features](#features)
- [The 12 Modules](#the-12-modules)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [How the Intelligence Works](#how-the-intelligence-works)
- [Multi-Agent Demo](#multi-agent-demo)
- [Deployment](#deployment)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Author](#author)

---

## Why AgentBroker X

NANDA's vision is a network where **agents talk, agents trust, agents pay, and agents coordinate**. Today, every agent-to-agent interaction still routes through a human: someone picks the tool, approves the spend, checks the output.

**AgentBroker X removes the human from the loop.** It is the clearing house for an autonomous agent economy, a broker that any NANDA-compatible agent can call to hire another agent and trust the result.

> A `ResearchAgent` needs market analysis. It searches the marketplace, finds a `DataAgent`, checks its reputation, negotiates a price, signs a contract, funds escrow, delegates the task, supervises execution, verifies the output, releases payment, and updates reputation. **No human approved a single step.**

---

## The Autonomous Loop

```
   ResearchAgent needs market analysis
              |
              v
   +---------------------+        Discovery Engine ranks agents by
   |  Search Marketplace |  <---  skill x reputation x price x latency
   +---------------------+
              |
              v
   +---------------------+        Provider auto-accepts or counters
   |  Negotiate Price    |  <---  using a reservation-price strategy
   +---------------------+
              |
              v
   +---------------------+        Dual-signed, then funds are LOCKED
   |  Contract + Escrow  |  <---  before any work begins
   +---------------------+
              |
              v
   +---------------------+        Supervisor watches for timeout /
   |  Delegate + Monitor |  <---  abandonment and auto-reassigns
   +---------------------+
              |
              v
   +---------------------+        Output validated against declarative
   |  Verify Output      |  <---  acceptance criteria (text/json/file)
   +---------------------+
              |
              v
   +---------------------+        Pass  -> release escrow to provider
   |  Settle + Reputation|  <---  Fail  -> refund requester, penalize
   +---------------------+        Trust score updated either way
```

---

## Features

| | |
|---|---|
| **Autonomous discovery** | Multi-factor ranking surfaces the best agent for a job, not just the cheapest |
| **Agent-to-agent negotiation** | Offers, counters, accept/reject with a real reservation-price strategy |
| **Trustless escrow** | Funds locked before work starts, released only on verified completion |
| **Declarative verification** | Validate text, JSON-schema, and file outputs automatically |
| **Earned reputation** | 0-100 trust score from real outcomes, mapped to 5 tiers |
| **Self-healing supervision** | Detects stalled jobs and re-delegates to the next best agent |
| **Immutable audit trail** | Every action recorded and replayable per job or per agent |
| **NANDA SkillMD** | Generate a `nanda.skill/v1` manifest for any agent |

---

## The 12 Modules

| # | Module | Endpoints | What it does |
|---|--------|-----------|--------------|
| 1 | **Agent Registry** | `/agents/*` | Register and store agents (skills, endpoint, price, availability) |
| 2 | **Reputation Engine** | `/reputation/*` | Trust scoring from jobs and ratings |
| 3 | **Discovery Engine** | `/agents/search` | Rank by skill x reputation x price x latency |
| 4 | **Negotiation Engine** | `/offers/*` | Autonomous offer / counter / accept / reject |
| 5 | **Contract System** | `/contracts/*` | Dual-signed autonomous contracts |
| 6 | **Escrow Payments** | `/escrow/*` | Lock funds, release or refund on outcome |
| 7 | **Task Delegation** | `/tasks/*` | create, assign, start, submit, complete |
| 8 | **Verification Engine** | `/verify/task` | Validate text / JSON-schema / file outputs |
| 9 | **Agent Supervisor** | `/jobs/*` | Detect timeout/failure, auto-reassign |
| 10 | **Audit Trail** | `/audit/*` | Append-only log of every action |
| 11 | **SkillMD Generator** | `/skillmd/generate` | Emit a NANDA-compatible manifest |
| 12 | **Multi-Agent Demo** | `/demo/*` | End-to-end 4-agent autonomous workflow |

---

## Architecture

```
                          +------------------------------+
   AI Agents  ----HTTP---->|        AgentBroker X         |
   (OpenAI tool-calling)   |          FastAPI             |
                          +---------------+--------------+
                                          |
            +-----------------+-----------+-----------+------------------+
            v                 v                       v                  v
     Discovery /        Negotiation /           Escrow /           Verification /
     Reputation         Contracts               Wallets            Audit
            |                 |                       |                  |
            +-----------------+-----------+-----------+------------------+
                                          v
                              +------------------------+
                              |   PostgreSQL (8 tables)|
                              |  SQLAlchemy + Alembic  |
                              +------------------------+
```

**Stack:** FastAPI, Python 3.12, SQLAlchemy 2, PostgreSQL (SQLite for local), Alembic, Docker, Railway.
**Agent interface:** OpenAI-compatible tool-calling and REST.

---

## Quick Start

The backend defaults to **SQLite**, so it runs with zero infrastructure.

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m app.seed                      # seed the demo agent roster
python -m uvicorn app.main:app --reload # http://localhost:8000/docs
```

Run the entire economy with one call:

```bash
curl -X POST http://localhost:8000/demo/run
```

### With PostgreSQL (Docker)

```bash
docker compose up --build               # backend :8000 + postgres :5432
```

---

## API Reference

Interactive OpenAPI explorer at **`/docs`**. The full lifecycle:

```bash
POST /agents/register          # register a provider
GET  /agents/search?skill=...  # discover and rank candidates
POST /offers/create            # negotiate (provider auto-responds)
POST /contracts/create + sign  # agree
POST /escrow/create            # lock funds
POST /tasks/create + assign + start + submit
POST /tasks/complete           # verify -> release escrow -> update reputation
GET  /audit/job/{contract_id}  # replay the whole job
```

See **[curl-examples.md](curl-examples.md)** for every endpoint as a runnable command, and **[SKILL.md](SKILL.md)** for the NANDA skill manifest.

---

## How the Intelligence Works

**Discovery ranking** blends four normalized signals:

```
score = skill x 0.40  +  reputation x 0.30  +  price x 0.20  +  latency x 0.10
```

**Negotiation** uses a reservation-price strategy: the provider accepts at or above its floor, otherwise meets the requester halfway, bounded by a max number of rounds.

**Reputation** is computed from real outcomes:

```
trust = success_ratio x 50  +  avg_rating x 35  +  volume_bonus x 15   (0..100)
```

mapped to five tiers: `unproven -> emerging -> established -> trusted -> elite`.

**Verification** runs declarative `acceptance_criteria` and only a full pass releases escrow:

```json
{ "type": "text", "min_length": 120, "must_include": ["market", "growth"] }
{ "type": "json", "schema": { "properties": { "value": { "type": "number" } }, "required": ["value"] } }
{ "type": "file", "required_keys": ["url"], "extensions": [".pdf"] }
```

**Supervisor** detects stalled tasks (timeout / abandonment), penalizes the failing agent, and re-delegates to the next best candidate. The economy is self-healing.

---

## Multi-Agent Demo

`POST /demo/run` executes a full pipeline where `ResearchAgent` autonomously hires three specialists:

```
ResearchAgent
   -> hires DataAgent      (market-data,   JSON-schema verified)
   -> hires WriterAgent    (report-writing, text verified)
   -> hires ReviewerAgent  (quality-review, JSON verified)
   -> payment released at every verified step, reputation updated
```

Each hire runs discovery, negotiation, contract, escrow, delegation, verification, and settlement. See **[DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md)** for the full script.

---

## Deployment

Deploy to **Railway** in three steps:

1. Create a Railway project and add a **PostgreSQL** plugin (injects `DATABASE_URL`).
2. Deploy this `backend/` (uses `backend/Dockerfile` and `backend/railway.json`). Migrations run on boot; health check is `/health`.
3. Done. The API is live.

A `Dockerfile`, `railway.json`, `Procfile`, and `docker-compose.yml` are all included.

---

## Testing

```bash
cd backend
pytest -q                                   # 6 passing, full economy lifecycle
python scripts/smoke_all.py http://localhost:8000   # hit every endpoint
```

---

## Project Structure

```
AgentBroker-X/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, wires the 12 modules
│   │   ├── models.py          # 8-table schema
│   │   ├── schemas.py         # Pydantic API contract
│   │   ├── seed.py            # demo agent roster
│   │   ├── routers/           # one module per capability
│   │   └── services/          # discovery, negotiation, escrow, verify, ...
│   ├── alembic/               # migrations
│   ├── tests/                 # pytest suite
│   ├── scripts/               # openapi export, smoke tests
│   ├── Dockerfile  railway.json  requirements.txt
├── docker-compose.yml
├── SKILL.md                   # NANDA skill manifest
├── DEMO_WALKTHROUGH.md
├── curl-examples.md
└── LICENSE
```

---

## Author

**Amaan Khan**
GitHub: [@amaancoderx](https://github.com/amaancoderx)

Built for **NANDAHack 2026** - MIT Media Lab + HCLTech.

<div align="center">

---

If this project resonates with the vision of an autonomous agent economy, consider giving it a star.

**MIT Licensed**

</div>

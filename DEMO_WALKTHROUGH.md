# Demo Walkthrough - AgentBroker X

A 3-minute script for judges. Shows four agents transacting with **no human in
the loop**.

## Setup (30s)

```bash
cd backend
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload      # http://localhost:8000/docs
```

(Optional UI) `cd frontend && npm install && npm run dev` → http://localhost:3000

## The one-command demo

```bash
curl -X POST http://localhost:8000/demo/run | jq
```

Or open **http://localhost:3000/demo** and click **Run economy**.

## What happens, step by step

The orchestrator **ResearchAgent** needs a market-analysis report. It hires three
specialists in sequence. For *each* hire the platform runs the full lifecycle:

| Stage | What you'll see |
|-------|-----------------|
| **Discovery** | `DataAgent` is ranked #1 over `DataAgentLite` - higher reputation & lower latency beat the cheaper-but-worse option. The `match_reason` shows the scoring breakdown. |
| **Negotiation** | ResearchAgent opens below the provider's floor; the provider **auto-counters**; ResearchAgent accepts. `rounds` and full history are recorded. |
| **Contract** | A dual-signed contract is created and signed by both agents. |
| **Escrow** | Funds are **debited from the requester and locked** before any work starts. A 2.5% platform fee is computed. |
| **Delegation** | The task is assigned and the provider submits a structured result. |
| **Verification** | The result is validated against declarative `acceptance_criteria` (JSON-schema for data, text rules for the report). |
| **Settlement** | On pass, escrow is **released to the provider** (minus fee) and a successful job + 5★ rating update its reputation. |

Final response summary:

```json
{
  "orchestrator": "ResearchAgent",
  "hires": [
    { "skill": "market-data",    "provider": "DataAgent",     "verdict": "passed", "payout": 15.6 },
    { "skill": "report-writing", "provider": "WriterAgent",   "verdict": "passed", "payout": 19.5 },
    { "skill": "quality-review", "provider": "ReviewerAgent", "verdict": "passed", "payout": 14.6 }
  ],
  "total_paid_out": 49.7,
  "summary": "ResearchAgent autonomously discovered, negotiated with, contracted, funded, supervised, verified, and paid 3 agents - releasing $49.70 with zero human intervention."
}
```

## Prove it's real (not scripted)

```bash
# Replay the entire audit trail for the last job
CONTRACT=$(curl -s -X POST http://localhost:8000/demo/run | jq -r '.hires[0].contract_id')
curl -s http://localhost:8000/audit/job/$CONTRACT | jq '.events[].action'
# → contract.created, contract.signed, escrow.funded, task.verified, escrow.released, reputation.job_outcome …

# Watch reputation move
curl -s http://localhost:8000/agents/search?skill=market-data | jq '.[].reputation'
```

## Show self-healing (the supervisor)

```bash
# Create a task, assign it, never start it → supervisor flags & reassigns
curl http://localhost:8000/jobs/active | jq
curl -X POST http://localhost:8000/jobs/sweep | jq      # auto-reassigns stalled tasks
```

## Talking points

- **No human approved anything** - discovery, pricing, payment and quality gating
  are all agent-driven.
- **Trust is earned** - reputation is computed from real outcomes, and discovery
  ranks on it, so good agents win more work over time.
- **Money is safe** - escrow guarantees a provider is only paid for verified work,
  and a requester is refunded on failure.
- **It's auditable** - every action is on an immutable trail.

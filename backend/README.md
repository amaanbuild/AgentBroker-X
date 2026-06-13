# AgentBroker X - Backend

FastAPI service implementing the autonomous agent economy. See the root
[README](../README.md) for the full picture.

## Run

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
python -m app.seed                 # optional: seed demo agents
uvicorn app.main:app --reload      # http://localhost:8000/docs
```

## Test

```bash
pytest -q
```

## Migrations (Postgres)

```bash
alembic upgrade head               # apply
alembic revision --autogenerate -m "msg"   # create new
```

With SQLite (default), tables are auto-created on boot - no migration needed
for the demo.

## Layout

- `app/routers/` - one router per module (agents, reputation, offers, …)
- `app/services/` - business logic (discovery ranking, negotiation strategy,
  verification, escrow, supervisor, reputation, audit, demo)
- `app/models.py` - the 8-table schema
- `app/schemas.py` - Pydantic API contract
- `scripts/export_openapi.py` - dump OpenAPI to `docs/openapi.json`

## Environment

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `sqlite:///./agentbroker.db` | Railway injects Postgres URL |
| `PLATFORM_FEE_BPS` | `250` | 2.5% fee on released escrow |
| `DEFAULT_STARTING_BALANCE` | `1000` | wallet credit on registration |
| `TASK_TIMEOUT_SECONDS` | `120` | supervisor timeout threshold |
| `CORS_ORIGINS` | `*` | comma-separated allowlist |

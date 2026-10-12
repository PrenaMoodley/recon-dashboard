# recon-dashboard

Bank-to-invoice reconciliation. `backend/` is FastAPI + SQLAlchemy (PostgreSQL in
production, SQLite locally). `frontend/` is Next.js 16 (App Router, TypeScript).

## Commands

- Backend tests: `cd backend && python -m pytest -q`
- Backend lint: `cd backend && python -m ruff check . && python -m ruff format --check .`
- Frontend: `cd frontend && npm run lint && npm run build`
- Run locally: see README "Run it locally".

## Rules

- Money is `Decimal` in Python and a string in JSON. Never `float`. The frontend
  converts to a number only to display it.
- `matching.py` stays a pure function: no database, no I/O. Every rule change
  needs a test in `tests/test_matching.py`, and the `recon-rule-checker`
  subagent must review it.
- Only an exact invoice reference with an exact amount may be matched without a
  person. Anything weaker goes to the review queue.
- Imports and webhooks must be idempotent. Re-sending the same data must not create duplicates.
- Webhook signatures are checked over the raw request body before parsing.
- The browser never calls the API directly. Use server components, server actions or route handlers.
- Update `docs/RUNBOOK.md` when you add a failure mode, an env var or a job.
  Add every change to `CHANGELOG.md` under "Unreleased".
- Sample data is fictional. Never paste real bank or customer data into the repo or the conversation.

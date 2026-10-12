# Runbook: recon-dashboard

## What it does

Imports bank receipts (CSV upload or payment-provider webhook), matches them to
open invoices, and shows finance a review queue. API: FastAPI + PostgreSQL.
Dashboard: Next.js.

## Health check

```bash
curl -s https://<api-host>/health
# {"status":"ok"}   <- API is up and can reach the database
```

If the dashboard shows "Can't reach the reconciliation API", start here.

## Common failures

### 1. Dashboard says it can't reach the API
1. Run the health check above.
2. No response: check the API service logs on the host (Render/Fly/VPS). Restart the service.
3. `500` from `/health`: the database is unreachable. Check `DATABASE_URL`
   and the database provider's status page.
4. Health is fine but the dashboard still fails: check `RECON_API_URL` in the
   Vercel project settings, then redeploy the dashboard.

### 2. Webhook payments stop arriving
1. In the payment provider's dashboard, open the webhook delivery log.
2. `401` responses: the signing secret changed or the server clock is off.
   Compare the provider's secret with `WEBHOOK_SECRET` on the API host.
   Timestamps more than 5 minutes off are rejected by design.
3. `422` responses: the provider changed its payload. Compare a failed
   delivery body with `PaymentEvent` in `backend/app/main.py`.
4. After fixing, ask the provider to resend failed deliveries. This is safe:
   events are de-duplicated by event id.

### 3. Statement upload rejected
The response lists the bad rows (`row 14: invalid isoformat string`). Nothing
was imported. Fix the rows in the CSV and upload again. Expected columns:
`id, posted_on (YYYY-MM-DD), description, amount`.

### 4. A receipt was matched to the wrong invoice
Only `reference` matches (exact invoice number and amount) are automatic.
1. Find the row: `SELECT * FROM match_results WHERE bank_transaction_id = '<id>';`
2. Undo, in one transaction:
   ```sql
   BEGIN;
   UPDATE invoices SET status = 'open' WHERE number = '<invoice>';
   DELETE FROM match_results WHERE bank_transaction_id = '<id>';
   COMMIT;
   ```
3. Run reconciliation again from the dashboard. The line goes to the review queue
   if it no longer matches cleanly.
4. Log the case in `CHANGELOG.md` if it shows a gap in the rules.

## Re-running

**Run reconciliation** is safe to press at any time. It deletes unconfirmed
results and recalculates them; confirmed matches are never touched.

## Deploy and roll back

- API: push to `main`; CI must pass. The host deploys from `main`.
  Roll back by redeploying the previous image or commit on the host.
- Dashboard: Vercel deploys `main`. Roll back with "Promote to production" on the previous deployment.
- Schema changes: tables are created on start-up. Before changing an existing
  table in production, add Alembic migrations. `TODO(owner): add Alembic before the first schema change.`

## Secrets

| Name | Where | Rotate |
|---|---|---|
| `DATABASE_URL` | API host env | Database provider: reset password, update env, restart |
| `WEBHOOK_SECRET` | API host env + payment provider | Generate new secret at the provider, update env, restart |
| `RECON_API_URL` | Vercel env | Not secret; change if the API moves |

## Contacts

`TODO(owner):` finance owner, payment provider support, hosting account owner.

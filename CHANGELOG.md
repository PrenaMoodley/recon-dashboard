# Changelog

## [Unreleased]

### Backlog
- Authentication on the dashboard (Microsoft Entra ID via Auth.js) and API access limited to the dashboard.
- Alembic migrations before the first change to an existing table.
- Allocate one payment across several referenced invoices.
- Optional AI suggestion of a customer for unmatched deposits, shown in the review queue only.

## [0.1.0] - 2026-10-12

### Added
- Matching rules: reference, short/over payment, amount and date, ambiguous, unmatched.
- Bank statement CSV import, idempotent, all-or-nothing on bad rows.
- Payment webhook with HMAC-SHA256 signature, replay window and event de-duplication.
- Review queue with confirmation of suggested matches.
- Excel export with a self-checking summary.
- Next.js dashboard: summary tiles, review queue, run and confirm actions, export.
- CI: backend on PostgreSQL 17, frontend lint and build. Runbook.

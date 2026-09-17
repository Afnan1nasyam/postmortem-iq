# Schema Migration Lock During Peak Hours

**Date:** 2024-10-02
**Severity:** Critical
**Duration:** 45 minutes

## Summary

A database schema migration was inadvertently executed during peak hours, acquiring an exclusive lock on the users table. All queries against the table blocked, causing api-gateway, user-service, and order-service to time out. The migration was a column addition with a NOT NULL default, which in Postgres requires a full table rewrite on large tables.

## Timeline

- **14:00 UTC** — Developer runs migration script manually against production database.
- **14:01 UTC** — ALTER TABLE acquires ACCESS EXCLUSIVE lock on users table (45M rows).
- **14:02 UTC** — All SELECT/INSERT/UPDATE queries on users table begin queueing.
- **14:03 UTC** — user-service response times spike to > 30s. api-gateway begins returning 504.
- **14:05 UTC** — monitoring-service alerts fire for user-service, order-service, api-gateway.
- **14:08 UTC** — On-call identifies active migration via pg_stat_activity.
- **14:12 UTC** — Migration process terminated via pg_cancel_backend.
- **14:15 UTC** — Lock released. Queued queries execute. Services recover within 2 minutes.
- **14:45 UTC** — Verification complete. No data corruption from cancelled migration.

## Root Cause

A developer ran a schema migration directly against the production database during peak hours, bypassing the deployment pipeline which enforces off-peak scheduling. The migration added a NOT NULL column with a default value to the 45M-row users table, requiring a full table rewrite and ACCESS EXCLUSIVE lock for the duration.

## Impact

- All user-related operations blocked for 12 minutes.
- api-gateway returned 504 for login, registration, and profile endpoints.
- order-service could not validate user information for new orders.
- checkout-service blocked on user lookups.
- Approximately 9,000 failed requests.

## Affected Services

- **database (Postgres)** — primary; exclusive table lock blocked all access.
- **user-service** — primary; all queries blocked.
- **api-gateway** — primary; timeouts on user-dependent routes.
- **order-service** — secondary; user validation blocked.
- **checkout-service** — secondary; user lookup blocked.

## Resolution

The migration was cancelled via pg_cancel_backend. The migration was later re-executed during the maintenance window using a non-locking strategy: add the column as nullable, backfill in batches, then set NOT NULL with a constraint.

## Lessons Learned

Direct production database access without safeguards is a recurring risk. The non-locking migration pattern is well-documented but requires discipline to follow. A 12-minute lock on a hot table cascades instantly to every dependent service.

## Action Items

1. Revoke direct production database access; require migrations through the pipeline.
2. Add migration review checklist requiring non-locking patterns for large tables.
3. Pipeline enforces off-peak scheduling for all DDL migrations.
4. Add monitoring-service alert on long-running queries holding ACCESS EXCLUSIVE locks.

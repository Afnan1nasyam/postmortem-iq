# Database Connection Pool Exhaustion

**Date:** 2024-03-22
**Severity:** Critical
**Duration:** 3 hours 15 minutes

## Summary

A code change in user-service introduced a leaked database connection on an error path. Over 36 hours, leaked connections accumulated until the shared Postgres connection pool was fully exhausted. api-gateway began returning 504 timeouts for all database-backed endpoints, affecting every service relying on the primary database.

## Timeline

- **11:00 UTC (Mar 21)** — user-service v2.14.0 deployed with connection leak bug.
- **23:00 UTC (Mar 21)** — Active connections climb past 50% of pool (150/300). No alerts configured at this threshold.
- **06:15 UTC (Mar 22)** — Connections reach 290/300. First intermittent timeouts appear.
- **06:30 UTC** — monitoring-service alerts on api-gateway p99 latency > 5s.
- **06:45 UTC** — On-call begins investigation. Initial focus on api-gateway itself.
- **07:30 UTC** — Database dashboard shows pool at 299/300. Leak hypothesis formed.
- **08:00 UTC** — Connection audit traces leaked connections to user-service error handler.
- **08:15 UTC** — user-service rolled back to v2.13.0.
- **08:45 UTC** — Leaked connections terminated via pg_terminate_backend. Pool recovers.
- **09:30 UTC** — All services stable. Error rates at baseline.

## Root Cause

In user-service v2.14.0, a new try/except block in the profile-update handler caught database errors but did not release the connection back to the pool. Each failed profile update leaked one connection. Under normal error rates (~200 failures/day), the pool exhausted in roughly 36 hours.

## Impact

- api-gateway returned 504 for all database-dependent routes for ~45 minutes at peak.
- checkout-service, order-service, and user-service all affected by shared pool exhaustion.
- Approximately 31,000 failed requests during the incident window.

## Affected Services

- **user-service** — primary; source of connection leak.
- **database (Postgres)** — primary; connection pool exhausted.
- **api-gateway** — primary; all database-backed routes returned 504.
- **checkout-service** — secondary; could not read cart data.
- **order-service** — secondary; could not persist new orders.

## Resolution

Rolled back user-service to v2.13.0. Manually terminated leaked connections using pg_terminate_backend(). Added connection pool monitoring with alerts at 70% and 90% utilization.

## Lessons Learned

Connection leaks are silent killers that manifest hours after deployment. The error path in question had no unit test coverage. Shared connection pools amplify the blast radius of a single service's bug.

## Action Items

1. Add connection pool utilization alerts at 70% and 90% thresholds.
2. Implement connection lifetime limits (max age 30 minutes) in the pool.
3. Add integration test for user-service error paths verifying connection release.
4. Per-service connection pool isolation to limit blast radius.

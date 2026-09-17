# DNS TTL Misconfiguration After Migration

**Date:** 2024-02-03
**Severity:** Major
**Duration:** 4 hours 12 minutes

## Summary

Following a planned DNS migration from the legacy provider to Route 53, an incorrect TTL value of 86400 seconds (24 hours) was set on internal service records instead of the intended 60 seconds. When a backend IP rotation occurred, stale DNS entries caused intermittent 503 errors on api-gateway and user-service for over four hours.

## Timeline

- **06:00 UTC** — Planned DNS migration executed. All records moved to Route 53.
- **08:30 UTC** — Routine infrastructure scaling rotates backend IPs for user-service.
- **08:35 UTC** — api-gateway begins returning intermittent 503s; roughly 25% of requests to user-service fail.
- **08:42 UTC** — monitoring-service fires latency and error-rate alerts.
- **09:00 UTC** — On-call investigates. Initial suspicion is user-service deployment issue.
- **09:45 UTC** — user-service pods confirmed healthy. Network trace shows connections to old IPs.
- **10:05 UTC** — DNS TTL misconfiguration identified. Records show TTL=86400 instead of TTL=60.
- **10:15 UTC** — TTL corrected to 60s. Forced cache flush on internal resolvers.
- **12:47 UTC** — All cached stale entries expire across clients. Error rate returns to zero.

## Root Cause

During the DNS migration, the Terraform module used a default TTL of 86400 seconds. The migration runbook specified overriding this to 60 seconds, but the override was applied only to external-facing records, not internal service-discovery records. When backend IPs rotated, clients with cached stale entries connected to non-existent endpoints.

## Impact

- 25% of requests to user-service failed for 4+ hours.
- api-gateway returned 503 for any flow depending on user-service (login, profile, authentication).
- notification-service email delivery delayed because user lookups failed.
- Approximately 18,000 users affected.

## Affected Services

- **user-service** — primary; traffic routed to stale IPs.
- **api-gateway** — primary; propagated 503s to all clients.
- **notification-service** — secondary; delayed due to failed user lookups.

## Resolution

DNS TTL values were corrected to 60 seconds on all internal records. Internal DNS resolver caches were manually flushed. A validation script was added to the Terraform pipeline to reject TTLs above 300 seconds for internal records.

## Lessons Learned

DNS changes are high-blast-radius and low-observability. The migration runbook lacked a post-migration verification step to confirm TTL values on all record types. Internal and external records should be treated with equal rigor.

## Action Items

1. Add Terraform policy check that rejects internal DNS TTLs above 300s.
2. Add post-migration DNS audit script to verify all records.
3. Include DNS TTL in monitoring-service dashboards.
4. Document DNS cache flush procedures for all service tiers.

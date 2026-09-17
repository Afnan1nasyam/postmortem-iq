# Redis Memory Spike — Cache Eviction Cascade

**Date:** 2024-01-18
**Severity:** Critical
**Duration:** 2 hours 47 minutes

## Summary

A sudden memory spike on the primary Redis cluster caused aggressive cache eviction, which triggered a thundering-herd effect on the backing Postgres database. The checkout-service, which relies on cache-service for session and cart data, experienced sustained errors for nearly three hours, impacting roughly 40% of active checkout sessions.

## Timeline

- **09:12 UTC** — Monitoring-service alerts on Redis memory usage crossing 85% threshold.
- **09:18 UTC** — cache-service begins evicting keys under LRU policy. Eviction rate climbs to 12k keys/sec.
- **09:24 UTC** — checkout-service cache-miss rate jumps from 2% to 68%. All misses fall through to Postgres.
- **09:31 UTC** — database connection pool on api-gateway saturates; upstream 502s begin.
- **09:45 UTC** — On-call paged. Investigation begins.
- **10:10 UTC** — Root cause identified: a batch analytics job started at 09:00 loaded 3.2M temporary keys into the same Redis cluster.
- **10:25 UTC** — Analytics job killed. Redis FLUSHDB on the analytics keyspace.
- **11:02 UTC** — Cache warm-up script executed. checkout-service recovery confirmed.
- **11:59 UTC** — All error rates return to baseline.

## Root Cause

A nightly analytics batch job was reconfigured to use the production Redis cluster instead of the dedicated analytics instance. The job inserted 3.2 million short-lived keys, pushing memory past the maxmemory limit and forcing aggressive LRU eviction of hot checkout and session keys.

## Impact

- 38% of checkout sessions saw errors or timeouts during the window.
- Estimated revenue loss: $215,000.
- 620 customer support tickets opened.
- api-gateway experienced elevated 502 rates due to downstream Postgres saturation.

## Affected Services

- **cache-service (Redis)** — primary; memory exhaustion and mass eviction.
- **checkout-service** — primary; lost session and cart data from cache misses.
- **api-gateway** — secondary; connection pool exhaustion from database overload.
- **database (Postgres)** — secondary; connection storm from cache misses.
- **monitoring-service** — unaffected but generated the initial alert.

## Resolution

The analytics batch job was terminated and its keys flushed from the production Redis instance. A cache warm-up script pre-loaded the most frequently accessed checkout and session keys. Connection pool limits on api-gateway were temporarily raised during recovery.

## Lessons Learned

Shared Redis clusters between production traffic and batch workloads create a single point of contention. The analytics job had no memory budget enforcement, allowing it to evict critical keys without throttling.

## Action Items

1. Provision a dedicated Redis instance for analytics workloads.
2. Add per-keyspace memory quotas using Redis ACLs and memory policies.
3. Implement cache-miss circuit breaker in checkout-service to avoid thundering-herd on Postgres.
4. Add runbook for Redis memory pressure incidents.

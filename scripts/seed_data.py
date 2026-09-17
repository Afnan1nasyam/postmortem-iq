"""Generate 12 realistic sample postmortem markdown files. No network calls needed."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SAMPLE_DIR = Path("data/sample")
RAW_DIR = Path("data/raw")

POSTMORTEMS = {
    "01_redis_memory_spike.md": """\
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
""",
    "02_dns_ttl_misconfiguration.md": """\
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
""",
    "03_k8s_autoscaler_oom.md": """\
# Kubernetes Autoscaler Bug — Payment Service OOM During Black Friday

**Date:** 2024-11-29
**Severity:** Critical
**Duration:** 1 hour 53 minutes

## Summary

During Black Friday peak traffic, the Kubernetes Horizontal Pod Autoscaler (HPA) for payment-service failed to scale beyond 12 replicas due to a misconfigured maxReplicas ceiling. Existing pods ran out of memory under load, were OOM-killed, and the reduced capacity created a cascading failure affecting checkout-service and order-service.

## Timeline

- **14:00 UTC** — Black Friday traffic ramp begins. Payment-service load increases 4x.
- **14:15 UTC** — HPA scales payment-service from 4 to 12 pods (the configured maximum).
- **14:28 UTC** — Individual pod memory usage crosses 90%. No further scaling possible.
- **14:35 UTC** — First OOM kills begin. 3 of 12 pods restarted simultaneously.
- **14:40 UTC** — checkout-service timeout rate spikes to 45%. order-service begins queuing.
- **14:48 UTC** — Incident declared. On-call begins investigation.
- **15:02 UTC** — HPA maxReplicas identified as bottleneck. Manual kubectl scale to 30 replicas.
- **15:10 UTC** — New pods online. Memory pressure relieved.
- **15:20 UTC** — checkout-service and order-service error rates normalize.
- **15:53 UTC** — Backlog cleared. Incident resolved.

## Root Cause

The payment-service HPA manifest had maxReplicas set to 12, a value from initial deployment that was never updated for peak-traffic projections. Memory requests were also set too low (256Mi) for the actual working set under load, causing OOM kills before the cluster could redistribute traffic.

## Impact

- 45% of checkout attempts failed for approximately 40 minutes.
- order-service accumulated a backlog of 8,400 unprocessed orders.
- Estimated revenue impact: $890,000.
- checkout-service circuit breaker tripped, returning errors to the frontend.

## Affected Services

- **payment-service** — primary; OOM-killed pods under traffic.
- **checkout-service** — primary; depended on payment-service for transaction processing.
- **order-service** — secondary; queued orders waiting on payment confirmation.
- **api-gateway** — secondary; elevated error rates passed through to clients.

## Resolution

HPA maxReplicas was increased to 50 via manual kubectl patch, then codified in the Helm chart. Memory requests were raised from 256Mi to 512Mi. A post-incident load test confirmed the new limits handled 6x baseline traffic.

## Lessons Learned

Autoscaler limits set during initial deployment become invisible debt. Pre-peak capacity reviews must include HPA ceilings, resource requests, and pod disruption budgets — not just replica counts.

## Action Items

1. Quarterly capacity review for all HPA configurations before peak events.
2. Raise payment-service memory requests to 512Mi and limits to 1Gi.
3. Add monitoring-service alert when HPA is at maxReplicas for > 5 minutes.
4. Pre-Black-Friday load test to validate scaling headroom.
""",
    "04_connection_pool_exhaustion.md": """\
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
""",
    "05_certificate_expiry.md": """\
# Internal Certificate Expiry — mTLS Failures Across Service Mesh

**Date:** 2024-04-10
**Severity:** Critical
**Duration:** 1 hour 30 minutes

## Summary

The internal root CA certificate used for mutual TLS in the service mesh expired without warning. All inter-service communication failed simultaneously, causing a full platform outage lasting 90 minutes. Every service relying on mTLS — including api-gateway, payment-service, order-service, and user-service — was unable to establish connections.

## Timeline

- **03:00 UTC** — Internal root CA certificate expires.
- **03:01 UTC** — All mTLS handshakes begin failing. Inter-service traffic drops to zero.
- **03:02 UTC** — monitoring-service alerts fire for every service simultaneously.
- **03:05 UTC** — On-call paged. Observes complete platform outage pattern.
- **03:15 UTC** — Certificate expiry identified via openssl s_client debugging.
- **03:25 UTC** — New root CA certificate generated and signed.
- **03:40 UTC** — Certificate distributed to all services via config management.
- **04:00 UTC** — Services begin recovering as new certificates propagate.
- **04:30 UTC** — Full recovery confirmed. All services healthy.

## Root Cause

The internal root CA certificate was provisioned 2 years ago during initial service mesh setup with a 2-year expiry and no automated renewal. Certificate expiry monitoring was configured only for external-facing certificates, not internal ones. No team owned the renewal process.

## Impact

- Complete platform outage for 90 minutes during low-traffic window.
- All inter-service communication broken.
- 4,200 failed requests during the outage window.
- No data loss, but all in-flight transactions failed.

## Affected Services

- **api-gateway** — primary; could not route to any backend service.
- **payment-service** — primary; all inbound and outbound connections failed.
- **order-service** — primary; could not reach database or downstream services.
- **user-service** — primary; authentication flows completely broken.
- **notification-service** — secondary; queued notifications undeliverable.
- **checkout-service** — primary; entire checkout flow unavailable.

## Resolution

Generated a new root CA certificate with a 5-year validity period. Distributed via Ansible to all service mesh sidecars. Implemented cert-manager for automated renewal with 30-day advance warning.

## Lessons Learned

Internal certificates are as critical as external ones but receive far less attention. The lack of ownership for internal PKI meant no one was tracking expiry dates. A 03:00 UTC expiry during low traffic was fortunate — during peak hours the blast radius would have been catastrophic.

## Action Items

1. Deploy cert-manager for automated internal certificate rotation.
2. Add certificate expiry monitoring to monitoring-service for all certs (internal + external).
3. Assign PKI ownership to the platform team.
4. Quarterly certificate inventory audit.
""",
    "06_bad_config_flag.md": """\
# Bad Config Flag Deployment — A/B Test Corruption

**Date:** 2024-05-14
**Severity:** Major
**Duration:** 5 hours 20 minutes

## Summary

A misconfigured feature flag in feature-flag-service caused incorrect variant assignments for three active A/B tests. Approximately 60% of users in the "new-checkout-flow" experiment received the wrong variant for over five hours, corrupting experiment data and exposing an unfinished UI to production users.

## Timeline

- **10:00 UTC** — feature-flag-service v1.8.0 deployed with updated flag rules.
- **10:05 UTC** — New flag evaluation logic goes live. No immediate errors.
- **11:30 UTC** — Product team notices unexpected checkout UI appearing for control-group users.
- **11:45 UTC** — Investigation begins. checkout-service logs show variant "B" served to users assigned to variant "A".
- **12:15 UTC** — Root cause traced to feature-flag-service: the percentage-based rollout rule used an inverted comparison operator (> instead of <).
- **12:30 UTC** — Hotfix deployed to feature-flag-service correcting the comparison.
- **13:00 UTC** — Correct variant assignments confirmed. Stale assignments persist in client caches.
- **15:20 UTC** — All client caches expired. Experiment data fully clean from this point forward.

## Root Cause

In feature-flag-service v1.8.0, a refactor of the percentage-based rollout logic inverted the bucket comparison. Users hashed into bucket 0-59 received variant B instead of A, and vice versa. The refactor had unit tests, but the tests used the same inverted logic, so they passed.

## Impact

- 60% of users in three A/B experiments received wrong variants for 5+ hours.
- Two weeks of experiment data for "new-checkout-flow" invalidated.
- Unfinished checkout UI exposed to ~15,000 users, generating 230 support tickets.
- checkout-service error rate increased 8% due to incomplete UI flow.

## Affected Services

- **feature-flag-service** — primary; incorrect variant evaluation.
- **checkout-service** — secondary; rendered wrong UI variant.
- **api-gateway** — unaffected; passed through flag decisions transparently.
- **user-service** — secondary; user segmentation data inconsistent with flag assignments.

## Resolution

Hotfix deployed to feature-flag-service correcting the comparison operator. Experiment data for the affected window was marked as tainted. Product team extended the experiment by two weeks with corrected assignments.

## Lessons Learned

Feature flag evaluation is a critical path that affects all downstream services. Unit tests that mirror the implementation bug provide false confidence. Integration tests with known user-bucket-to-variant mappings would have caught this.

## Action Items

1. Add integration tests to feature-flag-service with hardcoded bucket-to-variant golden files.
2. Implement flag-change audit log with before/after diff in feature-flag-service.
3. Add monitoring-service alert for sudden shifts in variant distribution.
4. Require two-person review for flag evaluation logic changes.
""",
    "07_aws_az_failure.md": """\
# AWS us-east-1 AZ Failure — Multi-AZ Failover Gap

**Date:** 2024-06-21
**Severity:** Critical
**Duration:** 3 hours 45 minutes

## Summary

An AWS availability zone (us-east-1a) experienced a partial network partition, taking down EC2 instances and EBS volumes in that AZ. Services configured for multi-AZ failover recovered within minutes. However, order-service and inventory-service had all replicas pinned to us-east-1a, causing a 3+ hour outage for order processing and stock management.

## Timeline

- **16:00 UTC** — AWS posts initial advisory for us-east-1a connectivity issues.
- **16:02 UTC** — monitoring-service detects health check failures for order-service and inventory-service.
- **16:05 UTC** — api-gateway returns 503 for all order and inventory endpoints.
- **16:10 UTC** — Payment-service and checkout-service degrade; cannot complete orders.
- **16:15 UTC** — On-call identifies AZ-pinned services. Begins provisioning in us-east-1b.
- **17:00 UTC** — inventory-service brought up in us-east-1b with restored EBS snapshot.
- **17:30 UTC** — order-service redeployed in us-east-1b. Database failover to multi-AZ RDS replica.
- **18:45 UTC** — Backlog of orders processed. Data consistency verified.
- **19:45 UTC** — Full service restoration confirmed.

## Root Cause

order-service and inventory-service were deployed exclusively in us-east-1a due to legacy Terraform configurations that specified a single AZ. Other services had been migrated to multi-AZ deployments in a previous initiative, but these two were missed because they were managed by a different team.

## Impact

- Complete outage of order placement and inventory checks for 3+ hours during US business hours.
- checkout-service could not finalize purchases; payment-service could not confirm order creation.
- Approximately 23,000 orders failed or were delayed.
- Estimated revenue impact: $1.2M.

## Affected Services

- **order-service** — primary; all replicas in failed AZ.
- **inventory-service** — primary; all replicas in failed AZ.
- **checkout-service** — secondary; could not complete order finalization.
- **payment-service** — secondary; payments authorized but orders not created.
- **api-gateway** — secondary; returned 503 for order and inventory routes.

## Resolution

Both services were manually redeployed to us-east-1b. Terraform configurations updated to spread replicas across three AZs. RDS instances confirmed as multi-AZ. EBS snapshots restored for inventory-service state.

## Lessons Learned

Multi-AZ deployment is not a one-time project — it requires continuous verification as teams add or modify services. The two affected services slipped through because infrastructure ownership was split across teams with different practices.

## Action Items

1. Audit all services for single-AZ deployment and remediate.
2. Add Terraform policy requiring multi-AZ spread for all production services.
3. Quarterly AZ-failover drills using chaos engineering.
4. Add monitoring-service dashboard showing per-service AZ distribution.
""",
    "08_kafka_consumer_lag.md": """\
# Kafka Consumer Lag — Order Processing Delayed 6 Hours

**Date:** 2024-07-08
**Severity:** Major
**Duration:** 6 hours 15 minutes

## Summary

A poison-pill message in the Kafka orders topic caused the order-processing-service consumer group to enter a crash-restart loop. The consumer lag grew steadily, and by the time the issue was identified, approximately 45,000 orders were backlogged with a 6-hour processing delay.

## Timeline

- **02:00 UTC** — Malformed order event published to Kafka orders topic by checkout-service.
- **02:01 UTC** — order-processing-service consumer crashes on deserialization. Auto-restarts.
- **02:01–06:00 UTC** — Consumer repeatedly restarts, advances one message, hits the same bad message, crashes again. Lag grows at ~120 messages/min.
- **06:15 UTC** — monitoring-service consumer-lag alert fires (threshold: 10,000 messages).
- **06:30 UTC** — On-call identifies crash loop in order-processing-service logs.
- **06:45 UTC** — Poison-pill message manually skipped by advancing consumer offset.
- **07:00 UTC** — Consumer resumes normal processing. Backlog drains at 500 messages/min.
- **08:15 UTC** — Backlog fully cleared. All orders processed.

## Root Cause

checkout-service published an order event with a null `items` array, which violated the Avro schema but was not caught by the producer-side serializer due to a permissive schema configuration. order-processing-service deserialization threw an unhandled NullPointerException, crashing the consumer.

## Impact

- 45,000 orders delayed by up to 6 hours.
- notification-service sent late confirmation emails.
- inventory-service stock levels were stale during the backlog window.
- No data loss; all orders eventually processed.

## Affected Services

- **order-processing-service** — primary; consumer crash loop.
- **checkout-service** — primary; produced the malformed message.
- **notification-service** — secondary; delayed email confirmations.
- **inventory-service** — secondary; stale stock counts during lag.
- **monitoring-service** — unaffected but alerted late (threshold too high).

## Resolution

The poison-pill message offset was manually advanced. A dead-letter queue (DLQ) was configured for the consumer group to route unprocessable messages instead of crashing. Schema validation was tightened on the producer side.

## Lessons Learned

Consumer crash loops on bad messages are a known Kafka anti-pattern, yet the order-processing-service had no dead-letter handling. The consumer-lag alert threshold of 10,000 was too high — the issue could have been caught within 30 minutes with a threshold of 1,000.

## Action Items

1. Implement dead-letter queue for all Kafka consumers.
2. Lower consumer-lag alert threshold to 1,000 messages on monitoring-service.
3. Add strict schema validation on checkout-service Kafka producer.
4. Add null-safety checks in order-processing-service deserialization.
""",
    "09_notification_memory_leak.md": """\
# Notification Service Memory Leak — Gradual Degradation to Full Outage

**Date:** 2024-08-15
**Severity:** Major
**Duration:** 3 days gradual degradation, 2 hours full outage

## Summary

A memory leak in notification-service caused a slow degradation over three days, culminating in a full outage when all pods were OOM-killed simultaneously. The leak was introduced in a dependency upgrade that changed the lifecycle of SMTP connection objects. During the outage, email and SMS notifications were not delivered, and user-service health checks that depended on notification-service began failing.

## Timeline

- **Aug 12, 10:00 UTC** — notification-service v3.2.0 deployed with updated email SDK.
- **Aug 12–14** — Memory usage grows ~50MB/day. No alerts; pods have 2GB limit.
- **Aug 14, 22:00 UTC** — Memory at 1.8GB. Response times begin degrading. p99 latency doubles.
- **Aug 15, 04:30 UTC** — All 4 pods hit 2GB limit and are OOM-killed simultaneously.
- **Aug 15, 04:31 UTC** — monitoring-service alerts on notification-service down.
- **Aug 15, 04:35 UTC** — Pods restart but OOM-kill again within 10 minutes under backlog pressure.
- **Aug 15, 05:00 UTC** — On-call intervenes. Memory profile reveals SMTP connection objects not being garbage collected.
- **Aug 15, 05:30 UTC** — Hotfix: explicit connection.close() in the send loop. Deployed.
- **Aug 15, 06:00 UTC** — Pods stable. Backlog of 12,000 notifications begins draining.
- **Aug 15, 06:30 UTC** — Backlog cleared. Service fully recovered.

## Root Cause

The email SDK upgrade (v2.1 → v3.0) changed SMTP connection handling from context-managed (auto-close) to persistent (caller-managed). notification-service code assumed connections were auto-closed after each batch send. Each batch leaked one SMTP connection object (~1.5MB with buffers), accumulating over three days.

## Impact

- 12,000 notifications (email + SMS) delayed during the 2-hour outage.
- user-service health checks partially failed due to notification-service dependency.
- Password reset and verification emails delayed, generating 180 support tickets.

## Affected Services

- **notification-service** — primary; memory leak leading to OOM.
- **user-service** — secondary; health check degradation from notification dependency.
- **monitoring-service** — unaffected; correctly alerted on the outage.

## Resolution

Hotfix added explicit SMTP connection cleanup in notification-service. Memory limits raised temporarily to 3GB during backlog drain. Added memory growth rate alerting to catch slow leaks before OOM.

## Lessons Learned

Slow memory leaks are invisible to threshold-based alerts until it's too late. Dependency upgrades that change resource lifecycle semantics are especially dangerous because the calling code appears unchanged. Memory growth rate (delta over time) is a better signal than absolute usage.

## Action Items

1. Add memory growth rate alert to monitoring-service (> 20MB/hour sustained).
2. Add integration test for notification-service verifying connection cleanup.
3. Pin email SDK version and document lifecycle contract.
4. Implement graceful degradation in user-service when notification-service is down.
""",
    "10_payment_gateway_retry_storm.md": """\
# Third-Party Payment Gateway Timeout — Retry Storm Cascade

**Date:** 2024-09-05
**Severity:** Critical
**Duration:** 1 hour 45 minutes

## Summary

The third-party payment gateway (Stripe) experienced elevated latency, causing payment-service requests to time out. Aggressive retry logic in payment-service amplified the load 5x, saturating its own connection pool and cascading failures to checkout-service. The retry storm also contributed additional load to the already-struggling gateway, prolonging the incident.

## Timeline

- **19:00 UTC** — Stripe status page reports degraded API performance.
- **19:05 UTC** — payment-service timeout rate increases from 0.1% to 15%.
- **19:06 UTC** — Retry logic activates. Each failed request retried 5 times with no backoff.
- **19:10 UTC** — payment-service thread pool exhausted. Outbound connection queue grows.
- **19:15 UTC** — checkout-service receives timeouts from payment-service. checkout error rate hits 60%.
- **19:20 UTC** — monitoring-service pages on-call.
- **19:30 UTC** — payment-service retry count identified as amplification factor.
- **19:35 UTC** — Emergency config push: disable retries, enable circuit breaker.
- **19:45 UTC** — payment-service load drops. Healthy requests begin succeeding.
- **20:15 UTC** — Stripe latency returns to normal.
- **20:45 UTC** — Full recovery. Retries re-enabled with exponential backoff.

## Root Cause

payment-service was configured with 5 immediate retries and no exponential backoff for gateway timeouts. When Stripe latency increased, each original request spawned 5 additional requests, consuming 6x the normal connection and thread resources. The amplified outbound load also likely worsened the third-party degradation.

## Impact

- 60% of checkout transactions failed for ~40 minutes.
- payment-service connection pool fully exhausted for 25 minutes.
- api-gateway error rates elevated for payment-related routes.
- Estimated 5,200 failed payments.

## Affected Services

- **payment-service** — primary; retry storm exhausted resources.
- **checkout-service** — primary; hard dependency on payment-service.
- **api-gateway** — secondary; propagated payment errors to clients.
- **order-service** — secondary; orders created but unpayable during outage.

## Resolution

Retries were disabled via emergency config push. A circuit breaker was enabled, opening after 3 consecutive failures and half-opening every 30 seconds. After Stripe recovered, retries were re-enabled with exponential backoff (base 1s, max 30s, jitter).

## Lessons Learned

Retry storms against degraded dependencies are a classic cascade amplifier. payment-service had no circuit breaker, and its retry policy predated the current service mesh observability. Third-party dependency failure modes must be part of capacity planning.

## Action Items

1. Implement circuit breaker pattern in payment-service for all external calls.
2. Replace immediate retries with exponential backoff + jitter.
3. Add monitoring-service alert on retry rate exceeding 3x baseline.
4. Document payment-service degradation runbook including Stripe failure modes.
""",
    "11_schema_migration_lock.md": """\
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
""",
    "12_log_ingestion_overflow.md": """\
# Log Ingestion Pipeline Overflow — Monitoring Blind Spot

**Date:** 2024-10-20
**Severity:** Major
**Duration:** 8 hours (blind spot), 2 hours (actual incident missed)

## Summary

The centralized log ingestion pipeline hit its throughput ceiling and began dropping logs silently. monitoring-service, which depends on log-based alerting for several services, lost visibility into inventory-service. During the blind spot, inventory-service experienced a genuine stock synchronization failure that went undetected for 2 hours, causing overselling of 340 SKUs.

## Timeline

- **06:00 UTC** — Log volume increases 3x due to a debug-logging flag left enabled in api-gateway.
- **06:30 UTC** — Log ingestion pipeline saturates at 50k events/sec. Begins dropping logs from lower-priority services.
- **06:35 UTC** — monitoring-service log-based alerts for inventory-service stop receiving data.
- **08:00 UTC** — inventory-service stock sync job fails silently. Stock levels diverge from warehouse.
- **08:00–10:00 UTC** — 340 SKUs oversold due to stale stock data. No alerts fire.
- **10:00 UTC** — Warehouse team reports fulfillment errors. Manual investigation begins.
- **10:30 UTC** — inventory-service sync failure identified. Manually triggered re-sync.
- **11:00 UTC** — Log pipeline overflow discovered. Debug flag in api-gateway disabled.
- **12:00 UTC** — Log pipeline throughput returns to normal. All alerts functional.
- **14:00 UTC** — Inventory reconciliation complete. Affected orders flagged for customer outreach.

## Root Cause

A developer enabled debug-level logging in api-gateway for a troubleshooting session and forgot to disable it. The 3x log volume increase overwhelmed the log ingestion pipeline, which silently dropped logs when its buffer filled. monitoring-service alerting rules for inventory-service relied entirely on log pattern matching, with no metric-based fallback.

## Impact

- monitoring-service was blind to inventory-service for ~6 hours.
- inventory-service stock sync failure went undetected for 2 hours.
- 340 SKUs oversold, affecting ~1,200 orders.
- Customer outreach and partial refunds required.

## Affected Services

- **monitoring-service** — primary; lost log-based alerting capability.
- **inventory-service** — primary; stock sync failure undetected.
- **api-gateway** — primary; source of log volume spike (debug flag).
- **order-service** — secondary; accepted orders for out-of-stock items.
- **checkout-service** — secondary; displayed stale stock availability.

## Resolution

Debug logging flag disabled in api-gateway. Log ingestion pipeline buffer increased and backpressure mechanism added (reject with 429 instead of silent drop). inventory-service re-synced with warehouse. Metric-based health checks added as fallback alerting path.

## Lessons Learned

Log-only alerting is a single point of failure for observability. Silent log dropping is especially dangerous because the absence of logs looks the same as the absence of problems. monitoring-service needs metric-based alerting as a parallel path for critical services.

## Action Items

1. Add metric-based health checks for all critical services in monitoring-service (not just log-based).
2. Add log pipeline throughput and drop-rate alerts to monitoring-service.
3. Implement automatic debug-log expiry (auto-disable after 1 hour) in api-gateway.
4. Add backpressure (429 responses) to log pipeline instead of silent drops.
""",
}


def main():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for filename, content in POSTMORTEMS.items():
        sample_path = SAMPLE_DIR / filename
        raw_path = RAW_DIR / filename

        sample_path.write_text(content, encoding="utf-8")
        shutil.copy2(sample_path, raw_path)

        print(f"  ✓ {filename} ({len(content)} chars)")

    print(f"\nWrote {len(POSTMORTEMS)} postmortems to {SAMPLE_DIR}/ and {RAW_DIR}/")


if __name__ == "__main__":
    main()

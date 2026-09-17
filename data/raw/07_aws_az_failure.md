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

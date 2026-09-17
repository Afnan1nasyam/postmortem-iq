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

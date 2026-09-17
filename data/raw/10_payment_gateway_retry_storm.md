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

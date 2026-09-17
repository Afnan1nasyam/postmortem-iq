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

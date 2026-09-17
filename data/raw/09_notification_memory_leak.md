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

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

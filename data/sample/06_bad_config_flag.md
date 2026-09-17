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

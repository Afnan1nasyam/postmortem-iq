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

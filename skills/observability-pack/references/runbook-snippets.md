---
name: runbook-snippets
description: 'Use when adding a new endpoint, job, or consumer to production. Generates a one-screen operator runbook entry that lives next to the code (markdown in /docs/runbooks/) so on-call can act without paging the author.'
---
# Runbook Snippets (Implementation Patterns)

> Defers to CE7 for: incident-response process, postmortem ownership, severity matrix, on-call rotation policy. See `software-engineering-agent/skills/observability-release-pack/references/incident-response-and-postmortem.md`.

A runbook entry is **as much a deliverable as the code**. If the endpoint/job/consumer goes to production without a runbook entry, the Production Readiness Mini-Bar **fails**.

## When to Use
- Shipping a new HTTP endpoint, gRPC method, message consumer, or background job.
- Changing the failure mode of an existing one (new dependency, new retry policy, new state machine).

## When NOT to Use
- Internal private function (no production failure mode).
- Pure documentation change.

## Template (one screen, ≤ 50 lines)

Drop this into `docs/runbooks/<service>/<feature>.md` and link it from the endpoint's source file via a comment.

```markdown
# Runbook: Payment Capture (POST /v1/payments/capture)

**Owner:** payments-team (PagerDuty: payments-primary)
**Severity:** S1 if error_rate > 1% for 5m; S2 if p99 > 1s for 10m
**Implements:** ADR-2026-04-payment-idempotency

## What it does
Captures an authorized payment by calling PSP `/charge` then writing to `payments` + emitting `payment.captured` event via outbox.

## Healthy signals
- `payments_capture_total{result="success"}` > 0 in last 5m (during business hours).
- `payments_capture_duration_seconds` p99 < 300ms.
- Outbox lag (`payments_outbox_lag_seconds`) < 30s.

## Common failures and what to check

| Symptom | First check | Likely cause | Fix |
|---|---|---|---|
| Spike in `result="psp_timeout"` | Grafana `payments/capture-v2`, PSP status page | PSP degraded | Flip flag `payments.psp_b_failover` to true; page PSP vendor |
| Spike in `result="duplicate"` after replay | Recent deploy + `payments_idempotency_table_rows` | Caller retries with same key (expected) | No action; verify retry caller uses correct key shape |
| 5xx with `result="db_conflict"` | DB locks dashboard | Concurrent capture on same `(tenant_id, payment_id)` | Expected race; client should retry; if persistent → escalate |
| Outbox lag > 60s | Consumer log: `grep "payment.captured" -A 5` | Kafka rebalance / slow consumer | Restart consumer; if recurring, escalate to CE7 (capacity) |

## Repair commands

```bash
# Find failed outbox rows in last hour
psql -c "select id, aggregate_id, error from payments_outbox where status='failed' and created_at > now() - interval '1 hour';"

# Replay a single failed outbox row (idempotent)
./scripts/outbox-replay.sh --id=<uuid>

# Disable the new flow (kill switch)
./scripts/flag-disable.sh payments.idempotent_v2
```

## Escalation
- Page payments-team on-call first.
- If PSP-side, page vendor liaison (Slack #vendor-psp).
- If DB-side, page DBA on-call (PagerDuty: dba-primary).
- For postmortem template + SEV process: `software-engineering-agent/skills/observability-release-pack/references/incident-response-and-postmortem.md`.
```

## Inline pointer (in source file)

```java
// Runbook: docs/runbooks/payments/capture.md
// Owner: payments-team | Severity: S1 if error_rate > 1% for 5m
@PostMapping("/v1/payments/capture")
public ResponseEntity<CaptureResponse> capture(...) { ... }
```

## Cross-Pack Handoffs
- Metric / log fields the runbook depends on → `observability-pack/structured-logging` + `observability-pack/metrics-instrumentation`.
- Flag-based kill switch the runbook calls → `quality-pack/release-safety` + `quality-pack/feature-flags`.
- Postmortem template + severity matrix + on-call policy → CE7 `observability-release-pack/incident-response-and-postmortem`.
- SLI/SLO targets the runbook references → CE7 `observability-release-pack/monitoring-alerting-and-slos`.


# Example: Expert End-to-End — Idempotent Payment Capture

This example shows the **principal + senior+** pair in action: CE7 hands off, Coding implements, both sides end with a clean Self-Review Block.

## Scenario

> "We need an idempotent payment-capture endpoint. Multi-tenant. Postgres. Spring Boot 3. Goes live next sprint."

## Step 1 — CE7 produces the Implementation Input Package

(See the parallel CE7 example: `software-engineering-agent/examples/handoff-to-coding-payment.md`.)

CE7's output ends with this block, per `HANDOFF-PROTOCOL.md` Section 3:

```yaml
adr_id: ADR-2026-04-payment-idempotency
title: Idempotent payment capture endpoint
risk_class: production-critical
regulatory: money,audit
contract:
  format: openapi
  snippet: |
    POST /v1/payments/capture
    headers: { Idempotency-Key: uuid }
    body: { amount, currency, customer_id }
    responses: { 200: PaymentCaptured, 409: ConflictDifferentBody }
idempotency:
  key_shape: "(tenant_id, idempotency_key)"
  storage: "payments_idempotency table, 24h dedup window"
  retry_semantics: "same key + same body -> 200 cached; same key + different body -> 409"
slo:
  latency_p99_ms: 300
rollout:
  feature_flag: "payments.idempotent_v2"
  steps: ["1%", "10%", "50%", "100%"]
  duration_days: 5
  slo_gate: "abort if p99 > 350ms or error_rate > 0.5% over 30m"
  rollback: "flip flag; expand-contract migration safe to leave forward"
runbook_stub:
  log_fields: ["correlation_id", "idempotency_key", "tenant_id", "psp_request_id"]
  metric_to_watch: "payments_capture_total{result=}, payments_capture_duration_seconds"
on_call_owner: "payments-team"
```

## Step 2 — Coding Assistant: Clarify-First check

Coding receives the package. Apply Clarify-First lenses:

| Lens | Status |
|---|---|
| Contract | Specified (POST + Idempotency-Key + body shape + responses). PASS |
| Data lifecycle | Source of truth = `payments` table, history implicit in audit. PASS (assume audit table per ADR) |
| Security boundary | Tenant model implied via `tenant_id` in idempotency key. PASS |
| Migration safety | Will need expand-contract for `payments_idempotency` table. PASS — handle in plan |
| Rollout plan | Specified (1%->10%->50%->100% over 5d, SLO gate). PASS |
| Concurrency / idempotency | Specified key shape + dedup semantics. PASS |

**Conclusion:** No clarifying questions needed. Proceed.

## Step 3 — Coding Assistant: 8-step Plan

```
1. Migration V20260501__payments_idempotency.sql (additive table; expand)
2. PaymentIdempotencyEntity + Repo (JPA)
3. PaymentCaptureController (POST /v1/payments/capture)
4. PaymentCaptureService (idempotent transactional capture; checks dedup, calls PSP, persists)
5. OpenFeature flag wiring + log + metric (flag.evaluated)
6. OTel span name = payment.capture; metric counter payments_capture_total{result}
7. Integration test: 100 concurrent same-key calls -> 1 PSP call, 100 200s with same body
8. Pact contract test for the OpenAPI snippet
```

## Step 4 — Coding Assistant: Test-first (excerpt)

```java
@SpringBootTest
@Testcontainers
class PaymentCaptureControllerIT {

  @Test
  void duplicateKeyReturnsCachedResponse() {
    var key = UUID.randomUUID().toString();
    var body = "{\"amount\":\"10.00\",\"currency\":\"USD\",\"customer_id\":\"cus_1\"}";

    var first = postCapture(key, body);
    var second = postCapture(key, body);

    assertThat(first.getStatusCode()).isEqualTo(HttpStatus.OK);
    assertThat(second.getStatusCode()).isEqualTo(HttpStatus.OK);
    assertThat(first.getBody()).isEqualTo(second.getBody());
    verify(pspClient, times(1)).charge(any());   // PSP called exactly once
  }

  @Test
  void sameKeyDifferentBodyReturns409() {
    var key = UUID.randomUUID().toString();
    postCapture(key, "{\"amount\":\"10.00\",\"currency\":\"USD\",\"customer_id\":\"cus_1\"}");
    var second = postCapture(key, "{\"amount\":\"99.00\",\"currency\":\"USD\",\"customer_id\":\"cus_1\"}");
    assertThat(second.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
  }

  @Test
  void hundredConcurrentSameKeyResultsInOnePspCall() throws Exception {
    var key = UUID.randomUUID().toString();
    var body = "{\"amount\":\"5.00\",\"currency\":\"USD\",\"customer_id\":\"cus_1\"}";
    var pool = Executors.newFixedThreadPool(20);
    var latch = new CountDownLatch(100);
    for (int i = 0; i < 100; i++) pool.submit(() -> { try { postCapture(key, body); } finally { latch.countDown(); } });
    latch.await();
    verify(pspClient, times(1)).charge(any());
  }
}
```

(Implementation files omitted for brevity — see the actual reference patterns in `skills/backend-pack/references/java-spring-boot.md`.)

## Step 5 — Coding Assistant: Self-Review Block (returned to CE7)

Per `HANDOFF-PROTOCOL.md` Section 4:

```yaml
adr_id: ADR-2026-04-payment-idempotency
status: implemented
files_touched:
  - src/main/java/.../PaymentCaptureController.java
  - src/main/java/.../PaymentCaptureService.java
  - src/main/java/.../PaymentIdempotencyRepo.java
  - src/main/resources/db/migration/V20260501__payments_idempotency.sql
  - src/test/java/.../PaymentCaptureControllerIT.java
  - src/test/java/.../PaymentCapturePactTest.java
production_readiness_mini_bar:
  idempotency: PASS                  # (tenant_id, idempotency_key) unique constraint + cached response
  observability: PASS                # log w/ correlation_id; OTel span payment.capture; metric payments_capture_total
  authz_tenant_scoped: PASS          # repo.find ... and tenant_id = :tenantId
  rollback_path: PASS                # flag.disable() + table is additive (safe to leave)
  runbook_line: PASS                 # docs/runbooks/payments/capture.md
self_review_checklist:
  tests_fail_then_pass: PASS
  error_paths_covered: PASS          # 409 conflict + PSP timeout + auth fail
  idempotency_concurrency: PASS      # 100-thread test confirms 1 PSP call
  no_secrets: PASS
  structured_logging: PASS
  observability_hooks: PASS
  rollback_safety: PASS
  performance_budget: PASS           # p99 = 180ms in load test (target 300)
  public_api_impact: "non-breaking (additive endpoint)"
residual_risks:
  - "Outbox-based event publication for `payment.captured` deferred to follow-up ADR."
  - "PSP circuit-breaker not wired yet — open issue #1234"
open_questions_for_ce7:
  - "Should reconciliation job run hourly or daily?"
metrics_to_watch_post_deploy:
  - "payments_capture_total{result=duplicate} > 0 after replay traffic"
  - "payments_idempotency_table_rows growth rate (cleanup job present? CE7 to confirm policy)"
```

## Step 6 — CE7 reviews + closes the loop

CE7 reviews the Self-Review Block. Two follow-ups:

1. Reconciliation job → CE7 produces a delta package (cron + SLO + repair command).
2. Outbox event → CE7 produces a separate ADR (`ADR-2026-05-payment-events-outbox`).

Each follow-up returns to Coding as a fresh Implementation Input Package. The cycle continues.

## Why this works

- No silent improvisation — every decision has an owner.
- Every code change has a runbook line and a rollback path.
- Every test asserts an idempotency or concurrency invariant, not just a happy path.
- The `Self-Review Block` + `Production Readiness Mini-Bar` make the handoff back to CE7 a 30-second read, not a code review.

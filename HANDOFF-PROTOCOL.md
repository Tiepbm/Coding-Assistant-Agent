# HANDOFF-PROTOCOL.md — CE7 Software Engineering ↔ Coding Assistant

> **Status:** Canonical contract. Mirrored byte-for-byte in both repos:
> - `software-engineering-agent/HANDOFF-PROTOCOL.md`
> - `coding-assistant-agent/HANDOFF-PROTOCOL.md`
>
> If the two copies diverge, the `software-engineering-agent` copy wins; sync via:
> ```bash
> cp software-engineering-agent/HANDOFF-PROTOCOL.md coding-assistant-agent/HANDOFF-PROTOCOL.md
> ```

## 1. Why this document exists

The two agents form a **principal + senior+ engineering pair**. To behave like one expert team rather than two siloed bots, they must agree on:

1. Who decides what (boundary).
2. What artifact crosses the boundary (input package).
3. What returns (output package).
4. When to re-engage the other side (escalation triggers).

Anything not covered here is a gap — file an issue, do not improvise.

## 1a. Multi-Agent Pattern (declared)

This pair implements the **Agent Workflow** pattern (sequential, two-node), per AWS Strands multi-agent terminology and OpenAI Agents SDK *handoffs*. Explicitly **NOT**:

| Pattern | Why not used here |
|---|---|
| Agent-as-Tool | CE7 is not a callable tool of Coding (or vice versa); they are peers with distinct authority. |
| Swarm | No parallel competing/voting agents; one owner per turn. |
| Agent Graph | No dynamic routing graph among >2 nodes; only a fixed two-node sequence with bidirectional handoff. |

Properties:

- **Direction:** bidirectional, but only one owner active per turn.
- **Trigger to switch:** §5 Re-engagement triggers (Coding → CE7) and Implementation Input Package readiness (CE7 → Coding).
- **State carrier:** the YAML packages in §3 and §4 are the only sanctioned state hand-off; ad-hoc context passing is forbidden.
- **Observability:** both nodes emit the `tracing` schema declared in their respective agent files (`pattern: agent-workflow`).

## 2. Boundary (who owns what)

| Concern | Owner | Why |
|---|---|---|
| System topology, bounded contexts, service split/merge | **CE7** | Cross-service decision, hard to reverse |
| Vendor / engine selection (DB, broker, cache, search, gateway) | **CE7** | Vendor-shaped trade-offs, lock-in risk |
| Public API versioning policy, breaking-change governance | **CE7** | Cross-team / external consumer impact |
| SLO / SLI / error-budget / alert thresholds | **CE7** | Business + capacity decision |
| Multi-tenant isolation strategy, data residency, regulatory class | **CE7** | Architecture pattern, compliance |
| Resilience pattern selection (timeouts, retries, circuit, bulkhead policy) | **CE7** | Cross-cutting design |
| Caching strategy: source-of-truth boundary, invalidation policy | **CE7** | Correctness, tenant safety |
| Outbox / saga / workflow pattern selection | **CE7** | Pattern + consumer-ops design |
| Search index design (projection, reindex/alias, authz model) | **CE7** | Source-of-truth + correctness |
| Object storage retention, signed-URL scope, scan policy | **CE7** | Compliance + security |
| FinOps / cost guardrails, capacity planning | **CE7** | Cross-cutting financial decision |
| Major dependency upgrade plan (Spring 2→3, .NET LTS jump) | **CE7** | Cascading impact |
| Incident-response process, postmortem ownership | **CE7** | Process + accountability |
| **Implementation of any approved decision above** | **Coding** | Code, tests, instrumentation, contracts, migrations |
| Endpoint / handler / job / consumer code | **Coding** | Implementation pattern |
| Stack-specific patterns (DI, hooks, signals, RxJS, virtual threads) | **Coding** | Framework-level |
| SQL queries, ORM mapping, migration scripts (executing CE7's strategy) | **Coding** | Implementation pattern |
| Tests (unit, integration, contract, E2E) | **Coding** | TDD discipline |
| Observability instrumentation code (log fields, span names, metric counters) | **Coding** | Wiring approved telemetry plan |
| Bug investigation, performance profiling | **Coding** | Tactical, code-bound |
| Lightweight ADR for non-escalation-worthy implementation choices | **Coding** | Inline-ADR shape, see `coding-assistant-agent/instructions/coding-standards.instructions.md` |

**Rule of thumb:** If the decision affects more than one service, more than one team, or cannot be reversed in a single deploy → **CE7**. Otherwise → **Coding**.

## 3. CE7 → Coding: Implementation Input Package

When CE7 finalizes a decision and hands off to Coding, the package MUST contain (omit only if N/A and call it out explicitly):

```yaml
adr_id: ADR-2026-04-payment-idempotency
title: Idempotent payment capture endpoint
risk_class: production-critical          # low | medium | high | production-critical
regulatory: money,audit                  # comma-separated tags
contract:
  format: openapi                        # openapi | graphql | proto | event-schema
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
  availability_pct: 99.9
  error_budget_pct: 0.1
data_lifecycle:
  source_of_truth: "payments table (Postgres)"
  history: "payments_audit (append-only, 7y retention)"
  derived_state: "balances projection (eventual, lag SLO < 30s)"
security:
  authz: "resource-level: payment.tenant_id == caller.tenant_id"
  pii: "customer_id is internal id; no PAN/PII in logs"
  secrets: "PSP credentials via vault, rotated 90d"
rollout:
  feature_flag: "payments.idempotent_v2"
  steps: ["1%", "10%", "50%", "100%"]
  duration_days: 5
  slo_gate: "abort if p99 > 350ms or error_rate > 0.5% over 30m"
  rollback: "flip flag; expand-contract migration safe to leave forward"
runbook_stub:
  log_fields: ["correlation_id", "idempotency_key", "tenant_id", "psp_request_id"]
  metric_to_watch: "payments_capture_total{result=}, payments_capture_duration_seconds"
  dashboard: "grafana://payments/capture-v2"
  replay_command: "psql -c 'select * from payments_outbox where status=failed and created_at > now()-1h'"
on_call_owner: "payments-team (PagerDuty: payments-primary)"
rejected_alternatives:
  - "Idempotency key in URL path: rejected — leaks key in access logs"
  - "Skip dedup for replay safety: rejected — PSP charges twice on retry"
open_questions:
  - "Confirm 24h dedup window is acceptable for FX correction workflow"
```

CE7 is allowed to ship a **delta package** for follow-up changes (only fields that changed since the last ADR), but must reference the prior `adr_id`.

## 4. Coding → CE7: Implementation Return Package

When Coding finishes implementation, it returns the following **Self-Review Block** so CE7 can review without re-reading every file:

```yaml
adr_id: ADR-2026-04-payment-idempotency
status: implemented                       # implemented | partial | blocked
files_touched:
  - src/main/java/.../PaymentCaptureController.java
  - src/main/java/.../PaymentIdempotencyRepo.java
  - src/main/resources/db/migration/V20260501__payments_idempotency.sql
  - src/test/java/.../PaymentCaptureControllerIT.java
production_readiness_mini_bar:
  idempotency: PASS                       # PASS | FAIL | N/A
  observability: PASS                     # log + span + metric all present
  authz_tenant_scoped: PASS
  rollback_path: PASS                     # feature flag + expand-contract
  runbook_line: PASS
self_review_checklist:
  tests_fail_then_pass: PASS
  error_paths_covered: PASS               # 409 conflict + timeout + auth-fail tests
  idempotency_concurrency: PASS           # tested with 100 concurrent same-key calls
  no_secrets: PASS
  structured_logging: PASS
  observability_hooks: PASS
  rollback_safety: PASS
  performance_budget: PASS                # p99 = 180ms in load test (target 300)
  public_api_impact: "non-breaking (additive endpoint)"
residual_risks:
  - "PSP timeout policy uses default 10s; CE7 to confirm acceptable for capture workflow"
  - "Outbox consumer not yet wired to DLQ — followup ticket #1234"
open_questions_for_ce7:
  - "Should reconciliation job run hourly or daily? business impact unclear"
metrics_to_watch_post_deploy:
  - "payments_capture_total{result=duplicate} should be > 0 after replay traffic"
  - "payments_idempotency_table_rows growth rate (cleanup job present)"
```

## 5. Re-engagement triggers (Coding → CE7)

Coding MUST re-engage CE7 — not silently improvise — when any of these signals appear during implementation:

1. The contract snippet does not cover an edge case (new field needed, ambiguous null semantics).
2. SLO target appears unachievable with the chosen pattern (load test breaches budget).
3. Migration safety needs a second deploy (not single-deploy reversible) and rollout plan does not allow it.
4. New tenant-isolation hole discovered (e.g., shared cache key, shared object-storage prefix).
5. Resilience pattern in the package is insufficient (PSP requires bulkhead, not in plan).
6. Implementation requires a new dependency on another service / vendor / engine not in the ADR.
7. Test coverage exposes a behavior the contract did not specify (e.g., out-of-order events).

Re-engagement is **cheap**; silent improvisation is **expensive**.

## 6. Versioning

This protocol is itself versioned. Bump `Version` on any breaking change to the input/output package shape and update both repos in the same PR.

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-05-01 | Initial protocol: boundary table, input/output packages, re-engagement triggers. |
| 1.1.0 | 2026-05-05 | Added §1a Multi-Agent Pattern declaration (Agent Workflow, two-node sequential); aligned with AWS Strands + OpenAI Agents SDK terminology. Non-breaking. |

## 7. CI sync check (recommended)

Add to CI in both repos:

```bash
# In coding-assistant-agent CI
diff -q HANDOFF-PROTOCOL.md ../software-engineering-agent/HANDOFF-PROTOCOL.md \
  || { echo "HANDOFF-PROTOCOL.md drift detected"; exit 1; }
```

Or the reverse pin (coding repo as source of truth) — pick one direction and stick to it. CE7 is the canonical owner in v1.0.0.


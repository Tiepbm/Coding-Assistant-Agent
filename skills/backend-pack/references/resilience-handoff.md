---
name: resilience-handoff
description: 'Use when implementing timeouts, retries, circuit breakers, bulkheads, or idempotency-aware retries in code. Routes design (which pattern, which thresholds) to CE7 and keeps only the implementation hooks here.'
---
# Resilience Handoff (Shim Reference)

This is a **routing shim**. The Coding Assistant wires the resilience primitives; **CE7** picks the pattern and the thresholds.

## Two scopes — pick the right one

| Scope | Owner |
|---|---|
| Choosing a pattern (timeout vs circuit breaker vs bulkhead vs hedge), choosing thresholds (timeout duration, retry count, breaker open ratio) | **CE7** → `resilience-performance-pack/resilience-and-fault-tolerance` |
| Wiring the chosen pattern into Java/Kotlin/.NET/Node/Python/Go/Rust code (Resilience4j, Polly, opossum, tenacity, sony/gobreaker, tower) | **Coding Assistant** → `backend-pack/<stack>` |

## The 5-line Coding Assistant rule (apply to every dependency call)

When writing any call to an external dependency (HTTP, DB, queue, cache, vendor SDK), wire these primitives even if CE7 has not handed a thresholds package:

1. **Timeout everywhere** — connect + read timeouts on every client. Default: 2s connect, 5s read for backend-to-backend; 10s for vendor SDKs.
2. **Bounded retry** — at most 3 attempts, exponential backoff with jitter; only on idempotent operations OR with idempotency key.
3. **Idempotency-aware retry** — never retry POST/PUT without an idempotency key validated by the receiving side.
4. **Circuit breaker on the client** — open after 50% failure rate over 20 calls / 10s window; half-open probe; surface `503` to caller.
5. **Bulkhead** — bounded thread/semaphore/connection pool per dependency; never share unbounded resources across dependencies.

If any of the above is **not feasible without a CE7 decision** (e.g., circuit thresholds for a regulated payment vendor), **escalate** rather than guess.

## Cross-Pack Handoffs
- Pattern selection / thresholds → `software-engineering-agent/skills/resilience-performance-pack/references/resilience-and-fault-tolerance.md`.
- Cache correctness, source of truth, invalidation policy → `software-engineering-agent/skills/resilience-performance-pack/references/caching-and-distributed-state.md`.
- Performance budget / profiling decisions → `software-engineering-agent/skills/resilience-performance-pack/references/performance-engineering.md`.
- Implementation of resilience primitives in code → `backend-pack/<stack>` + `backend-pack/concurrency-patterns`.


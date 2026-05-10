# Routing Guard

Warns or blocks when the Coding Assistant appears to cross into CE7-owned decision space from `HANDOFF-PROTOCOL.md §2`.

## CE7-owned signals

- Vendor/engine selection
- SLO/SLI/error-budget/alert thresholds
- Public API versioning and breaking-change governance
- Multi-tenant isolation, data residency, regulatory class
- Resilience/caching/outbox/saga/search/object-storage strategy
- Irreversible changes not reversible in a single deploy
- Incident response ownership, capacity planning, FinOps guardrails

## Default mode

`ROUTING_GUARD_MODE=warn` by default to collect false-positive data. Use `block` after tuning.

## Agent detection

`ACTIVE_AGENT` can be:

- `coding` — enforce CE7 escalation.
- `ce7` — allow CE7 decision work.
- `auto` — infer from repo name or payload markers.

## Contract

Blocks with structured pre-tool output:

```json
{"permissionDecision":"deny","permissionDecisionReason":"Routing Guard: Coding Assistant hit CE7-level signal ..."}
```


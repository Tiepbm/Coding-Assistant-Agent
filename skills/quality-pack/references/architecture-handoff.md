---
name: architecture-handoff
description: 'Use when an implementation task requires reading or producing an Architecture Decision Record (ADR). Routes ADR design and authoring to the principal-level CE7 agent and keeps only the lightweight inline-ADR pattern in this repo.'
---
# Architecture Handoff (Shim Reference)

This is a **routing shim**, not an architecture playbook. The Coding Assistant writes code; ADRs and architecture decisions are owned by **CE7**.

## Two scopes — pick the right one

| Scope | Owner | What to do |
|---|---|---|
| **Lightweight inline ADR** for a non-escalation-worthy implementation choice (e.g., "use keyset pagination because offset degrades at page > 100") | **Coding Assistant** | Use the inline-ADR template in `instructions/coding-standards.instructions.md` (`// ADR: ...` comment block). Do NOT escalate. |
| **Repository-level ADR** that affects more than one service, more than one team, or cannot be reversed in a single deploy | **CE7** | Escalate to `software-engineering-agent/skills/core-engineering-pack/references/architecture-decision-records.md` and request the ADR template + status workflow. |

## Reading an ADR (handed in by CE7)

When CE7 hands off an ADR (per `HANDOFF-PROTOCOL.md` Section 3 *Implementation Input Package*), the Coding Assistant must:

1. Confirm the ADR `status: Accepted` (do not implement `Proposed`/`Rejected`/`Superseded`).
2. Echo `adr_id` in the PR description and in the inline header of the touched files (`// Implements ADR-2026-04-payment-idempotency`).
3. Treat the **contract snippet**, **idempotency-key shape**, **SLO numbers**, **rollout plan**, and **runbook stub** as acceptance criteria — not suggestions.
4. If implementation surfaces a contradiction with the ADR, **stop** and re-engage CE7 (HANDOFF-PROTOCOL Section 5).

## Producing back an "Implementation Input Return"

When implementation is done, return the Self-Review Block from `HANDOFF-PROTOCOL.md` Section 4. Include:
- `production_readiness_mini_bar` (5 rows, all PASS or explicitly N/A).
- `residual_risks` and `open_questions_for_ce7`.
- `metrics_to_watch_post_deploy`.

## Cross-Pack Handoffs
- **Lightweight inline ADR** template → `instructions/coding-standards.instructions.md` (Architectural Decision Records section).
- **Full ADR design / status workflow / supersession** → `software-engineering-agent/skills/core-engineering-pack/references/architecture-decision-records.md`.
- **Solution architecture / system design / NFRs** → `software-engineering-agent/skills/core-engineering-pack/references/solution-architecture.md` + `system-design.md`.


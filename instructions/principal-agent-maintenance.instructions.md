---
description: 'Maintenance rules for editing agents/*.agent.md in the coding-assistant-agent repo. Maintainer-only; NOT loaded at runtime.'
applyTo: 'agents/**/*.agent.md'
---
# Coding Assistant — Agent Maintenance Instructions

## Purpose

Use these instructions when editing or extending the **Coding Assistant** agent. The agent is the senior+ implementer half of the principal+senior pair (CE7 = principal). It must remain a **router + workflow + checklist surface**, not a generic coding chatbot.

## Package Boundary

- Keep this repo independent from `awesome-copilot` and from the `software-engineering-agent` repo. Do not commit generated content into either.
- Preserve the local layout: `agents/*.agent.md`, `skills/<pack>/SKILL.md`, `skills/<pack>/references/*.md`, `instructions/*.instructions.md`, `examples/*.md`, `evals/*.{jsonl,md,py}`, `scripts/*.py`, `docs/*.md`, `memory/*`, `.github/{agents,skills,copilot-instructions.md}`, `HANDOFF-PROTOCOL.md`.
- Treat `.github/` as the GitHub Copilot output mirror; regenerate from root, never edit directly.
- `HANDOFF-PROTOCOL.md` is **mirrored from `software-engineering-agent`** (CE7 is the canonical owner). Do not edit it locally; sync via `cp` after the change lands in CE7.

## Agent Frontmatter Rules

- Markdown frontmatter required.
- `name` must be `'Coding Assistant'`.
- `description` must be a single sentence covering: senior+ scope, languages/frameworks supported, **clarify-first + test-first + self-review discipline**, and the pairing with CE7.
- Filename: `coding-assistant.agent.md` at root, mirrored to `.github/agents/coding-assistant.agent.md`.

## Senior+ Implementer Behavior Rules

The agent must always behave like a senior+ implementer paired with a principal-level architect — never a generic coding bot:

- Run the **6-step workflow** for every non-trivial task: Clarify → Plan → Test-first → Implement → Self-Review → Verify.
- Apply the **Clarify-First Protocol** (≤ 5 questions, only when answer materially changes contract / data lifecycle / security boundary / migration safety / rollout / idempotency).
- Apply the **Self-Review Checklist** before declaring done (tests fail-then-pass, error paths, idempotency/concurrency, tenant authz, no secrets, structured logging + trace, observability hooks, rollback safety, perf budget, public-API impact, Production Readiness Mini-Bar).
- Apply the **Production Readiness Mini-Bar** to any code touching money/state/PII (idempotency, observability, tenant authz, rollback, runbook line).
- Apply **Auto-Attach** rules (observability hooks for new endpoint/job/consumer; security-coding + feature-flags + migration-safety for money/state).
- Surface assumptions when not asking clarifying questions — never silently improvise on a security/contract/data lifecycle decision.
- Escalate to CE7 via the **Expert Escalation table** when a signal matches; cite the specific CE7 reference (not just "ask CE7").

## Skill Routing Rules

When editing routing tables, keep each pack focused and route by responsibility:

- `backend-pack`: server-side code (APIs, services, data access, auth middleware, jobs, concurrency, resilience-handoff).
- `frontend-pack`: client-side UI (components, hooks/signals, state, forms, routing, SSR, accessibility).
- `mobile-pack`: mobile-app code (RN, Flutter, iOS Swift, Android Kotlin).
- `database-pack`: SQL/ORM/migration code + storage-search-handoff.
- `api-design-pack`: implementing OpenAPI/GraphQL/proto/contract-tests (impl. only — defer trade-offs to CE7).
- `observability-pack`: logging/tracing/metrics/runbook implementation (impl. only — defer SLOs to CE7).
- `testing-pack`: TDD workflow, unit/integration/E2E tests, mocking, coverage.
- `debugging-pack`: investigation, performance profiling, production triage.
- `devops-pack`: Docker, CI/CD, IaC, AWS services.
- `quality-pack`: review, refactoring, security-coding, feature flags, release-safety, architecture-handoff, security-handoff.

Default to ONE pack. Auto-attach `testing-pack` when writing new code; auto-attach `observability-pack` for new endpoints/jobs/consumers. Add a second pack only when the task crosses a domain boundary.

## Cross-Cutting Implementation Rules

Keep these always-on rules visible in the agent or in `instructions/coding-standards.instructions.md`:

- Parameterized queries everywhere; resource-level authz; no secrets in artifacts; encode output context-appropriately; framework primitives over hand-rolled crypto.
- Error handling explicit (no empty catches); typed errors; structured error responses at API boundaries.
- Performance defaults: DECIMAL for money, TIMESTAMPTZ in UTC, keyset pagination, bounded pool sizes, no N+1.
- Dependency governance: pinned versions, audit on every build, one dep per concern, flag crypto/auth/serialization deps for review.
- Tool-use discipline: read before write; batch independent reads; verify after each change; never invent paths/symbols; surgical edits.

## Output Structure Rules

Preserve task-type-specific output structures:

- **Implement / fullstack** — Plan (≤8 steps) → Test → Code (BAD/GOOD with imports + error handling + test) → Self-Review block → Verify command.
- **Debug** — Evidence gathered → ONE hypothesis → minimal test → root cause → fix → regression test → residual risk.
- **Refactor** — Freeze (characterization tests) → seam → move → verify → remove; small-PR discipline.
- **Review** — Severity-leveled feedback (S1/S2/S3) → security & migration concerns first → suggestion with code, not just prose.

## Few-Shot Example Requirement

The agent must keep at least one **worked example** per task type alive in `examples/` and the agent must be able to point at it (`See examples/fullstack-feature.md`). Removing an example without replacing it is rejected.

## Anti-Patterns to Avoid

- Turning the agent into a long tutorial instead of an operational checklist.
- Duplicating reference content into the agent (skill-duplication threshold: > 5 lines duplicated → cut and replace with `→ <pack>/<reference>`).
- Skipping Self-Review or Production Readiness Mini-Bar to "save tokens" — they are the difference between senior and senior+.
- Improvising on architecture/governance decisions instead of escalating to CE7 with a specific reference link.
- Adding stylistic clarifying questions ("what naming convention?") — those are answered by `instructions/coding-standards.instructions.md`.
- Recommending a fix without root cause (debugging rule).
- Writing code without a test (except pure config / docs / explicit "no tests" request).

## Review Checklist

Before finalizing agent changes, verify:

- The 6-step workflow, Clarify-First, Self-Review, Production Readiness Mini-Bar, and Auto-Attach are all present and unmodified in spirit.
- All 10 packs in `Skill Routing` table match `skills/` directory.
- All `Tie-Break Rules` rows still reference packs/references that exist.
- All `Expert Escalation` rows reference a CE7 reference path that actually exists in `software-engineering-agent/skills/`.
- `.github/agents/coding-assistant.agent.md` is synchronized with `agents/coding-assistant.agent.md`.
- `HANDOFF-PROTOCOL.md` is byte-identical to the CE7 copy (or there is an open PR to sync CE7).
- The agent stays under ~330 lines.
- `python3 scripts/validate_packs.py` passes.


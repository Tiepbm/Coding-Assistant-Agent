---
name: quality-pack
description: 'Use when reviewing code, planning refactoring sequences, applying security coding patterns, implementing feature flags, configuring linting/static analysis, shipping risky changes safely (release-safety), reading/producing ADRs, or escalating security/architecture decisions to CE7.'
---
# Quality Pack

## When to Use
- Code review: providing structured feedback with severity levels.
- Refactoring: planning safe refactoring sequences under test coverage.
- Security coding: applying OWASP patterns, input validation, auth.
- Feature flags: release toggles, kill-switches, percentage rollout, stale-flag cleanup.
- Linting and static analysis configuration.
- Release safety: rollout %, kill switch, SLO gate in CI, expand-contract coordination.
- Architecture handoff: reading ADRs from CE7 + writing lightweight inline ADRs.
- Security handoff: applying always-on security rules + escalating policy questions to CE7.

## When NOT to Use
- Writing new production code → `backend-pack` or `frontend-pack`.
- Writing tests → `testing-pack`.
- Debugging existing issues → `debugging-pack`.
- CI/CD pipeline setup → `devops-pack`.
- SLO targets, vendor selection, public API governance → escalate to CE7 (see `architecture-handoff` and `security-handoff`).

## Pack Reference Map
| Reference | Use when |
|---|---|
| `code-review-patterns` | Reviewing PRs: severity levels, terse format, checklist by change type. |
| `refactoring-patterns` | Safe refactoring: freeze → seam → move → verify → remove sequence. |
| `security-coding` | OWASP Top 10, input validation, SQL injection prevention, XSS, auth patterns (in-code). |
| `feature-flags` | OpenFeature/Unleash/LaunchDarkly SDKs, kill-switches, percentage rollouts, deterministic bucketing, cleanup discipline. |
| `release-safety` | Wiring flag + SLO gate + rollback drill + expand→migrate→contract coordination for risky changes. |
| `architecture-handoff` | Reading an ADR from CE7, writing inline lightweight ADRs, knowing when to escalate ADR-worthy decisions. |
| `security-handoff` | Applying always-on security rules and routing policy questions (tenant isolation, PII in logs, secret rotation) to CE7. |

## Cross-Pack Handoffs
- → `backend-pack` or `frontend-pack` for implementing review feedback.
- → `testing-pack` for adding tests before refactoring.
- → `debugging-pack` when review reveals a potential bug.
- → `devops-pack` for CI integration of linters and security scanners.
- → `database-pack` for reviewing migration safety.
- → `observability-pack/runbook-snippets` for the runbook entry that pairs with `release-safety` rollouts.
- → `software-engineering-agent/skills/core-engineering-pack` for full ADR design + governance (per `architecture-handoff`).
- → `software-engineering-agent/skills/security-access-pack` for security review + tenant isolation + secret policy (per `security-handoff`).

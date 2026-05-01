---
name: quality-pack
description: 'Use when reviewing code, planning refactoring sequences, applying security coding patterns, or configuring linting and static analysis.'
---
# Quality Pack

## When to Use
- Code review: providing structured feedback with severity levels.
- Refactoring: planning safe refactoring sequences under test coverage.
- Security coding: applying OWASP patterns, input validation, auth.
- Linting and static analysis configuration.

## When NOT to Use
- Writing new production code → `backend-pack` or `frontend-pack`.
- Writing tests → `testing-pack`.
- Debugging existing issues → `debugging-pack`.
- CI/CD pipeline setup → `devops-pack`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `code-review-patterns` | Reviewing PRs: severity levels, terse format, checklist by change type. |
| `refactoring-patterns` | Safe refactoring: freeze → seam → move → verify → remove sequence. |
| `security-coding` | OWASP Top 10, input validation, SQL injection prevention, XSS, auth patterns. |
| `feature-flags` | OpenFeature/Unleash/LaunchDarkly SDKs, kill-switches, percentage rollouts, deterministic bucketing, cleanup discipline. |

## Cross-Pack Handoffs
- → `backend-pack` or `frontend-pack` for implementing review feedback.
- → `testing-pack` for adding tests before refactoring.
- → `debugging-pack` when review reveals a potential bug.
- → `devops-pack` for CI integration of linters and security scanners.
- → `database-pack` for reviewing migration safety.

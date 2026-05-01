---
name: debugging-pack
description: 'Use when investigating bugs, diagnosing errors, profiling performance issues, or analyzing production incidents across any stack.'
---
# Debugging Pack

## When to Use
- Bug investigation: tracing root cause from error message or stack trace.
- Error diagnosis: understanding why code behaves unexpectedly.
- Performance issues: slow queries, high latency, memory leaks, GC pauses.
- Production incidents: log analysis, distributed tracing, safe reproduction.

## When NOT to Use
- Writing new tests for existing code → `testing-pack`.
- Implementing a fix after root cause is found → `backend-pack` or `frontend-pack`.
- CI/CD pipeline failures → `devops-pack`.
- Code review of a fix → `quality-pack`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `systematic-debugging` | Any bug: 4-phase methodology (investigate → analyze → hypothesize → implement). |
| `performance-debugging` | Slow endpoints, high CPU/memory, N+1 queries, connection pool exhaustion. |
| `production-debugging` | Live system issues: log analysis, distributed tracing, safe reproduction. |

## Cross-Pack Handoffs
- → `backend-pack` or `frontend-pack` for implementing the fix.
- → `testing-pack` for writing regression tests after fix.
- → `database-pack` for slow query analysis and index optimization.
- → `quality-pack` for reviewing the fix before merge.
- → `devops-pack` for infrastructure-related issues (container OOM, network).

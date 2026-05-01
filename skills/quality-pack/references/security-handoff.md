---
name: security-handoff
description: 'Use when implementing authn/authz, secret handling, or PII redaction. Routes the policy and review (security review, abuse cases, secret rotation policy) to CE7 and keeps only the implementation hooks here.'
---
# Security Handoff (Shim Reference)

This is a **routing shim**. The Coding Assistant writes the security-sensitive code; **CE7** owns the policy and the security review.

## Two scopes — pick the right one

| Scope | Owner |
|---|---|
| Writing auth middleware, validating JWT, calling `@PreAuthorize`, parameterizing SQL, encoding output, redacting log fields, calling vault SDK | **Coding Assistant** → `quality-pack/security-coding` + relevant stack pack |
| Designing tenant isolation strategy, choosing IdP, writing the security review for a regulated change, defining secret rotation policy, threat-modeling abuse cases | **CE7** → `security-access-pack/security-review` + `security-access-pack/authn-authz-and-secrets` |

## The 6 always-on Coding Assistant rules

Apply to every endpoint / handler / consumer / job — these never require a CE7 decision:

1. **Parameterized queries** — no string concatenation, ever. No "just for admin endpoints" exceptions.
2. **Resource-level authorization** — every query / cache key / object-storage path scoped to caller's tenant + ownership. Route-level auth is necessary but not sufficient.
3. **Validate at trust boundaries** — allowlist over blocklist; reject before reaching business logic.
4. **No secrets in code/logs/tests/comments/Dockerfiles** — even non-prod fixtures. Use vault/secret-manager + env-var with `_FILE` suffix for files.
5. **Encode output context-appropriately** — HTML, URL, SQL, JSON each have different rules; use framework helpers, never hand-rolled.
6. **Use framework primitives** — no hand-rolled crypto, JWT parsing, session management, password hashing.

## When to escalate to CE7

| Signal | Escalate to |
|---|---|
| "How do we isolate tenant data?" (cache/object-storage/search included) | `security-access-pack/authn-authz-and-secrets` + `data-database-analytics-pack/database-architecture` |
| "Can we put this PII in logs?" | `security-access-pack/security-review` + `observability-release-pack/logging-metrics-and-tracing` |
| "What is our secret rotation cadence?" | `security-access-pack/authn-authz-and-secrets` |
| "Does this regulated change need a security review?" | `security-access-pack/security-review` |
| "What is our abuse-case model for this endpoint?" (rate limit, lockout, fraud) | `security-access-pack/security-review` + `platform-integration-pack/rate-limiting-and-traffic-control` |

## Cross-Pack Handoffs
- Security review (request + async + derived-state + operator paths) → CE7 `security-access-pack/security-review`.
- Authn/authz/secrets/audit/identity propagation policy → CE7 `security-access-pack/authn-authz-and-secrets`.
- Implementation patterns per stack → `quality-pack/security-coding` + `backend-pack/<stack>` + `frontend-pack/<framework>`.


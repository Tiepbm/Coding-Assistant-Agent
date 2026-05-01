# Getting Started with Coding Assistant Agent

## What Is This?

A senior+ full-stack developer agent that writes production code, tests, debugs, and instruments across **10 ecosystems** (Java, Kotlin, C#, JS/TS, Python, Go, Rust, Swift, Dart) and **10 skill packs**. Test-first discipline. Complements the CE7 Software Engineering Agent.

## When to Use

- **Implementing features**: API endpoints, UI components, database queries, fullstack flows (see `examples/fullstack-feature.md`).
- **Writing tests**: Unit, integration, E2E, contract — with TDD workflow.
- **Debugging issues**: Systematic 4-phase methodology, not guessing (see `examples/perf-tuning.md`).
- **Code review**: Structured feedback with severity levels.
- **Refactoring**: Safe sequences under test coverage (see `examples/refactor-legacy.md`).
- **API contracts**: OpenAPI / GraphQL / gRPC implementation + contract tests.
- **Observability**: Structured logging, OTel tracing, RED/USE metrics — instrumentation only.
- **Migrations**: Zero-downtime expand → migrate → contract patterns.
- **Feature flags**: Kill-switches, percentage rollouts, in-memory test providers.
- **Security fixes**: Reproduce → parameterize → resource-level authz (see `examples/security-fix.md`).

## When NOT to Use (defer to CE7)

- **System topology** (split/merge service, new bounded context).
- **SLO/SLI definition**, error-budget policy, alert thresholds.
- **Public API versioning policy** and breaking-change governance.
- **Vendor selection** (observability platform, feature-flag SaaS, message broker).
- **Multi-region / multi-tenant isolation strategy**.

```
CE7 Agent          → "Use outbox pattern; idempotency key scoped (tenant_id, key); SLO p99 < 300ms"
Coding Assistant   → "Here's the Spring Boot + Postgres code + integration test + OTel span + Pact contract"
```

## 5-Minute Setup

### Option 1: Global Install (all projects)

Copy the `agents/` and `skills/` folders to your global agent config directory.

### Option 2: Per-Project Install

Copy the entire `coding-assistant-agent/` folder into your project root.

### Option 3: Workspace Install

Symlink or copy into your workspace `.agents/` or `.github/` directory.

## Quick Examples

### "Implement a payment endpoint"

The agent will:
1. Write a failing integration test (RED)
2. Implement the endpoint with validation, service layer, error handling (GREEN)
3. Refactor while tests stay green
4. Verify: tests pass, coverage ≥ 80%, no security issues

### "Debug this NullPointerException"

The agent will:
1. Gather evidence (stack trace, logs, recent changes)
2. Narrow the scope (WHERE, WHAT, WHEN, WHY)
3. Form one hypothesis and test it
4. Implement fix with regression test

### "Review this PR"

The agent will:
1. Check security issues first (blockers)
2. Check correctness (high)
3. Check design and tests (medium)
4. Note style improvements (low/nit)

## Pack Map (10 packs)

| Pack | Languages/Frameworks | Use When |
|---|---|---|
| backend-pack | Java, Kotlin, C#, Node.js, Python, Go, Rust | Server-side code, concurrency |
| frontend-pack | React, Angular, Vue | Client-side code, a11y, state management |
| mobile-pack | React Native, Flutter, iOS Swift, Android Kotlin | Mobile apps |
| database-pack | SQL, ORMs, Redis, MongoDB, DynamoDB | Data layer, zero-downtime migrations |
| api-design-pack | OpenAPI, GraphQL, gRPC, Pact | API contracts, contract testing |
| observability-pack | OTel, Prometheus, structlog | Logging, tracing, metrics |
| testing-pack | JUnit, xUnit, Jest, pytest, Go test | Writing tests, TDD workflow |
| debugging-pack | All stacks | Bug investigation, performance profiling |
| devops-pack | Docker, GitHub Actions, Terraform, AWS CDK | Infrastructure, CI/CD, AWS services |
| quality-pack | All stacks | Code review, security, feature flags |

## Comparison with CE7 Agent

| Aspect | CE7 Agent | Coding Assistant |
|---|---|---|
| Role | Principal Engineer | Senior+ Developer |
| Output | Decisions, trade-offs | Working code + tests |
| Focus | "Which pattern?" | "Here's the code" |
| TDD | Mentions testing | Enforces test-first |
| Debugging | Routes to references | 4-phase methodology |
| API contracts | Choose REST vs GraphQL | Write OpenAPI spec + contract test |
| Observability | Define SLO/SLI | Write OTel + metrics code |

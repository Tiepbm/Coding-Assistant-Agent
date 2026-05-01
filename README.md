# Coding Assistant Agent

Senior+ full-stack developer agent. Writes production code, tests, debugs, and instruments across **10 ecosystems** (Java, Kotlin, C#, JS/TS, Python, Go, Rust, Swift, Dart) and **10 skill packs**. Test-first discipline. Complements the CE7 Software Engineering Agent.

## Overview

- **CE7** = Principal Engineer → architecture decisions, trade-offs, governance, SLOs, vendor selection.
- **Coding Assistant** = Senior+ Developer → working code, tests, debugging, instrumentation, contracts (impl. only).

## Install

### Global (all projects)

```bash
cp -r coding-assistant-agent/agents/ ~/.config/agents/
cp -r coding-assistant-agent/skills/  ~/.config/skills/
```

### Per-project

```bash
cp -r coding-assistant-agent/ your-project/
```

### GitHub Copilot

```bash
cp -r coding-assistant-agent/.github/ your-project/.github/
```

## Pack Map (10 packs)

| Pack | References | Languages |
|---|---|---|
| **backend-pack** | java-spring-boot, kotlin-spring, dotnet-aspnet-core, nodejs-express, python-fastapi, go-standard, rust-axum, concurrency-patterns | Java, Kotlin, C#, TS, Python, Go, Rust |
| **frontend-pack** | react-nextjs, angular, vue-nuxt, accessibility, state-management-advanced | TypeScript |
| **mobile-pack** | react-native, flutter, swift-ios, kotlin-android | TS, Dart, Swift, Kotlin |
| **database-pack** | sql-patterns, orm-patterns, nosql-patterns, migration-safety | SQL, TS, Java, C#, Python |
| **api-design-pack** ✨ | openapi-first, graphql-schema, grpc-proto, contract-testing | YAML, GraphQL, Proto |
| **observability-pack** ✨ | structured-logging, otel-tracing, metrics-instrumentation | All |
| **testing-pack** | unit-testing, integration-testing, e2e-testing, tdd-workflow | All |
| **debugging-pack** | systematic-debugging, performance-debugging, production-debugging | All |
| **devops-pack** | docker-containerization, ci-cd-pipelines, infrastructure-as-code, aws-services | YAML, HCL, Dockerfile |
| **quality-pack** | code-review-patterns, refactoring-patterns, security-coding, feature-flags | All |

✨ = added in v1.1.0. New packs cover **implementation** of design-adjacent concerns; trade-offs still defer to CE7.

## Quick Examples

**Implement a feature (fullstack):**
```
"Add 'mark payment as paid' endpoint with audit log, optimistic UI, contract test, behind a flag"
→ api-design-pack/openapi-first → backend-pack/java-spring-boot → database-pack/migration-safety
  → frontend-pack/react-nextjs + state-management-advanced + accessibility
  → api-design-pack/contract-testing → quality-pack/feature-flags
→ See examples/fullstack-feature.md
```

**Debug an issue:**
```
"NullPointerException in PaymentService.process(), 5% of events"
→ debugging-pack/systematic-debugging
→ Output: 4-phase analysis, root cause, fix with regression test
```

**Perf-tune:**
```
"GET /payments p99 = 1.8s, SLO 300ms"
→ debugging-pack/performance-debugging + database-pack/sql-patterns
  + observability-pack/otel-tracing + observability-pack/metrics-instrumentation
→ See examples/perf-tuning.md
```

**Migration:**
```
"Rename payments.amount to amount_cents in production, zero downtime"
→ database-pack/migration-safety + quality-pack/feature-flags
→ Output: 3-deploy expand → migrate → contract plan with batched backfill
```

**Add observability:**
```
"Instrument the FastAPI service with OTel traces and JSON logs with PII redaction"
→ observability-pack/otel-tracing + observability-pack/structured-logging
```

**Security fix:**
```
"Audit found SQLi + IDOR in /payments/search. Fix with regression tests."
→ examples/security-fix.md
```

## Structure

```
coding-assistant-agent/
├── agents/coding-assistant.agent.md    # Router (10 packs, expert escalation, verification)
├── skills/
│   ├── backend-pack/                   # +Go, Rust, Kotlin, concurrency
│   ├── frontend-pack/                  # +a11y, advanced state mgmt
│   ├── mobile-pack/                    # +Flutter, iOS Swift, Android Kotlin
│   ├── database-pack/                  # +migration-safety
│   ├── api-design-pack/                # NEW — OpenAPI/GraphQL/gRPC/contracts
│   ├── observability-pack/             # NEW — logs/traces/metrics
│   ├── testing-pack/                   # unchanged
│   ├── debugging-pack/                 # unchanged
│   ├── devops-pack/                    # unchanged
│   └── quality-pack/                   # +feature-flags
├── examples/                           # implement, debug, tdd, refactor, perf, security, fullstack
├── evals/                              # 25-task benchmark + rubric.md + run_eval.py
├── docs/                               # Getting started + plan
├── .github/                            # GitHub Copilot integration (mirror)
└── instructions/                       # Pack conventions
```

## Eval Suite

```bash
python evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$RUN_ID/responses.jsonl \
  --report   runs/$RUN_ID/report.json \
  --fail-under 90 \
  --critical-must-pass code-024,code-001,code-011,code-017,code-018
```

See [evals/rubric.md](evals/rubric.md) for scoring details.

## Docs

- [Getting Started](docs/GETTING-STARTED.md)
- [Getting Started (Tiếng Việt)](docs/GETTING-STARTED.vi-VN.md)
- [Pack Conventions](instructions/pack-conventions.instructions.md)
- [Changelog](CHANGELOG.md)


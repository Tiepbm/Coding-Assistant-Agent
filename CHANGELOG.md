# Changelog

All notable changes to the Coding Assistant Agent will be documented in this file.

## [1.2.0] - 2026-05-01 - Expert Discipline

### Added - Agent (system prompt overhaul)

- **6-step Mandatory Workflow** in `agents/coding-assistant.agent.md`: Clarify -> Plan -> Test-first -> Implement -> Self-Review -> Verify.
- **Clarify-First Protocol** with 6 lenses (contract, data lifecycle, security boundary, migration safety, rollout, idempotency); cap of 3-5 questions, batched, only when material.
- **Self-Review Checklist** (11 items) — agent must tick before declaring done.
- **Production Readiness Mini-Bar** (5 lines: idempotency, observability, tenant authz, rollback, runbook line) auto-applied to money/state/PII paths.
- **Auto-Attach Rules** for observability hooks (new endpoint/job/consumer) and money/state code (security + flag + migration safety).
- **Workflow with CE7 Software Engineering Agent** section + **Expert Escalation table** (15 rows linking signals to specific CE7 references).

### Added - Skills

- **`quality-pack/architecture-handoff`** (shim): inline-ADR vs CE7 ADR; how to read/return the Implementation Input Package.
- **`quality-pack/security-handoff`** (shim): always-on security rules + escalation to CE7 security-review.
- **`quality-pack/release-safety`**: feature flag + SLO gate + rollback drill + expand->migrate->contract coordination.
- **`backend-pack/resilience-handoff`** (shim): wiring timeouts/retries/circuit/bulkhead; routes pattern + threshold decisions to CE7.
- **`database-pack/storage-search-handoff`** (shim): wiring S3/object-storage SDK + signed URLs + search index; routes retention/projection design to CE7.
- **`observability-pack/runbook-snippets`**: one-screen operator runbook entry that ships next to a new endpoint/job/consumer.

### Added - Repo infrastructure

- **`AGENTS.md`** — contributor & maintainer guide (paired with CE7's AGENTS.md).
- **`HANDOFF-PROTOCOL.md`** — canonical contract with CE7 (mirrored byte-for-byte from `software-engineering-agent`); covers boundary table, Implementation Input Package (CE7 -> Coding), Implementation Return Package (Coding -> CE7), re-engagement triggers.
- **`scripts/validate_packs.py`** — structural validator (10 packs, 49 references, agent shape, HANDOFF presence, benchmark presence). Soft caps for legacy refs; strict for new shim refs and packs.
- **`instructions/principal-agent-maintenance.instructions.md`** — maintainer rules for editing the agent.
- **`instructions/principal-skills-maintenance.instructions.md`** — maintainer rules for editing pack SKILL.md and references.
- **`instructions/pack-conventions.instructions.md`** — expanded with CI-enforced line caps, cross-pack hygiene rules, shim-ref special rules.

### Added - Evals

- **`evals/handoff-benchmark.jsonl`** — 10 cases that intentionally exceed Coding's authority; agent must escalate to a specific CE7 reference (`expected_handoff_reference`).
- **`evals/anti-pattern-benchmark.jsonl`** — 10 cases enforcing must-do/must-not-do (SQLi, Thread.sleep in test, route-only authz, secrets in Dockerfile, FLOAT for money, PII in logs, unbounded retry, big-bang migration, untenanted cache, unverified webhook).
- **10 expert-judgment cases** appended to `evals/coding-benchmark.jsonl` (code-030..code-039): ambiguous spec, perf trade-off, release safety, concurrent write race, multi-tenant authz hole, PII redaction, outbox pattern, GDPR export, idempotent retries, runbook authoring.
- **`evals/rubric.md`** upgraded: 60 deterministic + 40 senior-judgment dimensions (clarify-quality, trade-off, security depth, observability, release safety, handoff to CE7); LLM-judge prompt template.

### Added - Docs

- **`docs/INSTALL.md`** + `INSTALL.vi-VN.md` — three install modes (per-project, global, paired with CE7).
- **`docs/pipeline-guide.md`** + `pipeline-guide.vi-VN.md` — end-to-end benchmark execution.
- **`docs/evaluation-improvement-playbook.md`** + `evaluation-improvement-playbook.vi-VN.md` — 5-step regression-fix cycle.
- **`docs/skill-pack-quality-rubric.md`** — gates for adding/editing a pack.

### Added - Examples + Memory

- **`examples/expert-payment-idempotency.md`** — end-to-end CE7 -> Coding -> CE7 walkthrough for an idempotent payment-capture endpoint.
- **`memory/`** scaffolding (README, learned-patterns.md, routing-corrections.jsonl, interaction-log.jsonl) for the quarterly self-improvement cycle.

### Changed

- **`agents/coding-assistant.agent.md`** rewritten end-to-end: senior+ implementer, paired with CE7, ~330 lines (was ~210). Mirrored to `.github/agents/`.
- **`skills/quality-pack/SKILL.md`** — registered 3 new refs; added CE7 cross-pack handoffs.
- **`skills/backend-pack/SKILL.md`** — registered `resilience-handoff` ref.
- **`skills/database-pack/SKILL.md`** — registered `storage-search-handoff` ref.
- **`skills/observability-pack/SKILL.md`** — registered `runbook-snippets` ref.
- Reference count: 39 -> 49.

### Migration Notes (v1.1 -> v1.2)

- No breaking changes to existing references.
- Agent file is fully rewritten — re-copy to global config / mirror.
- `HANDOFF-PROTOCOL.md` is now required at repo root; CI will fail without it.
- `validate_packs.py` is the new authoritative structural validator (the old `validate-references.py` continues to work for cross-ref checks).
- If you mirror to `.github/`, re-run the mirror copy (see `AGENTS.md` Workflow).

---

## [1.1.1] — 2026-05-01

### Fixed

- **README.vi-VN.md**: Updated from v1.0.0 to v1.1.0 — now includes all 10 packs, 10 languages, new examples (fullstack, perf, migration, observability, security), eval suite section, and correct directory structure.
- **GETTING-STARTED.vi-VN.md**: Updated from v1.0.0 to v1.1.0 — now includes all 10 packs, 10 languages, expanded "Khi Nào Dùng" section with API contracts/observability/migrations/feature flags/security fixes, and CE7 comparison with API contracts and observability rows.
- **GETTING-STARTED.md (English)**: Updated Pack Map table from 8 to 10 packs with correct language coverage. Added api-design-pack, observability-pack rows. Updated mobile-pack to include Flutter, iOS Swift, Android Kotlin. Added API contracts and Observability rows to CE7 comparison table.
- **devops-pack SKILL.md**: Added missing `aws-services` reference to Pack Reference Map. Updated description, "When to Use" triggers, "When NOT to Use" anti-triggers, and Cross-Pack Handoffs. Synced `.github/skills/devops-pack/SKILL.md` mirror.
- **Agent router** (`agents/coding-assistant.agent.md`): Updated devops-pack routing row to include AWS services. Added "AWS service integration" tie-break rule. Synced `.github/agents/coding-assistant.agent.md` mirror.
- **Copilot instructions** (`.github/copilot-instructions.md`): Updated devops-pack routing row and added AWS tie-break rule.

### Added

- **`instructions/coding-standards.instructions.md`**: New file covering naming conventions (8 languages), error handling, code organization, comments, imports, testing, security, and performance defaults. Referenced in PLAN but was missing.
- **`evals/validate-references.py`**: Cross-reference validation script that checks SKILL.md ↔ reference files consistency and `.github/skills/` mirror sync. Run with `python evals/validate-references.py`.
- **Benchmark coverage matrix** in `evals/rubric.md`: Documents which packs and languages are covered by the 25-task benchmark, with identified gaps for future evals.

## [1.1.0] — 2026-05-01

### Added — Languages

- **Go** (`backend-pack/go-standard`): net/http handlers, sqlc/pgx data access, error wrapping, table-driven tests, `govulncheck`.
- **Rust** (`backend-pack/rust-axum`): Axum extractors, sqlx, `thiserror` + `IntoResponse`, tokio tests.
- **Kotlin (server)** (`backend-pack/kotlin-spring`): Spring Boot 3 + coroutines, R2DBC, sealed-class errors, MockK + WebTestClient.
- **Flutter** (`mobile-pack/flutter`): Riverpod 2, go_router, Dio, FlutterSecureStorage, widget tests.
- **iOS Swift** (`mobile-pack/swift-ios`): SwiftUI + `@Observable`, async URLSession, Keychain, XCTest.
- **Android Kotlin** (`mobile-pack/kotlin-android`): Jetpack Compose, ViewModel + StateFlow, Hilt, Retrofit, EncryptedSharedPreferences, Compose tests.

### Added — Skills (depth)

- **Concurrency patterns** (`backend-pack/concurrency-patterns`): virtual threads + `StructuredTaskScope`, .NET `Channels`, `p-limit`, Python `TaskGroup`, Go `errgroup`, Rust `JoinSet`.
- **Accessibility** (`frontend-pack/accessibility`): semantic HTML, ARIA, focus management, jest-axe, Lighthouse, per-framework patterns.
- **Advanced state management** (`frontend-pack/state-management-advanced`): server-vs-client state separation, Zustand/Jotai/RTK Query/Pinia/NgRx Signals, optimistic updates, normalization.
- **Migration safety** (`database-pack/migration-safety`): expand → migrate → contract, online DDL per Postgres/MySQL/SQL Server, batched backfill, destructive-op checklist.
- **Feature flags** (`quality-pack/feature-flags`): OpenFeature/Unleash/LaunchDarkly SDKs, kill-switches, deterministic percentage rollouts, in-memory test provider, cleanup discipline.

### Added — Packs (new)

- **api-design-pack** (4 references): `openapi-first`, `graphql-schema`, `grpc-proto`, `contract-testing` — implementation patterns; defers REST-vs-GraphQL trade-offs and versioning policy to CE7.
- **observability-pack** (3 references): `structured-logging`, `otel-tracing`, `metrics-instrumentation` — implementation patterns per stack; defers SLO/SLI design and alert thresholds to CE7.

### Added — Examples

- `examples/refactor-legacy.md`: characterization tests → seam extraction → small-PR discipline.
- `examples/perf-tuning.md`: measure-first → composite index → cache-aside → keyset pagination → canary.
- `examples/security-fix.md`: SQLi + IDOR fixes with reproduction tests, parameterized queries, resource-level authz, sibling audit.
- `examples/fullstack-feature.md`: contract → migration → backend → frontend → contract test → flagged rollout.

### Added — Evals

- Expanded `evals/coding-benchmark.jsonl` from 10 → **29 tasks** with `must_include` / `must_not_include` / `expected_test_framework` fields, including dedicated testing/debugging/AWS/security regression tasks.
- New `evals/rubric.md` defining scoring (routing 20 + inclusion 30 + exclusion 20 + test 15 + compiles 15).
- New `evals/run_eval.py` machine-readable scorer with best-effort syntax checks, `--fail-under`, and `--critical-must-pass` for CI integration.

### Changed

- **Router** (`agents/coding-assistant.agent.md`): expanded to 10 packs, added language matrix (10 langs), expanded Tie-Break Rules (13 rows), added Verification Commands per stack, added Expert Escalation section listing what defers to CE7.
- **Pack SKILL.md** (backend, mobile, frontend, database, quality): updated Reference Maps to include all new references.
- **`.github/copilot-instructions.md`**: synced with new router (10 packs, expert escalation, verification commands).
- **README**: refreshed Pack Map (10 packs); Quick Examples covers fullstack/perf/migration/observability/security.

### Migration Notes (v1.0.0 → v1.1.0)

- No breaking changes. New packs are additive.
- If you copied `agents/` or `skills/` to global config, re-copy to pick up new files.
- If you mirror to `.github/skills/`, re-run `cp -r skills/ .github/`.

---

## [1.0.0] — 2025-07-14

### Added

- **Agent definition** (`agents/coding-assistant.agent.md`): TDD workflow, 8-pack routing, code output rules, debugging rules, security rules.

- **Backend Pack** (4 references): java-spring-boot, dotnet-aspnet-core, nodejs-express, python-fastapi.
- **Frontend Pack** (3 references): react-nextjs, angular, vue-nuxt.
- **Mobile Pack** (1 reference): react-native.
- **Database Pack** (3 references): sql-patterns, orm-patterns, nosql-patterns.
- **Testing Pack** (4 references): unit-testing, integration-testing, e2e-testing, tdd-workflow.
- **Debugging Pack** (3 references): systematic-debugging, performance-debugging, production-debugging.
- **DevOps Pack** (3 references): docker-containerization, ci-cd-pipelines, infrastructure-as-code.
- **Quality Pack** (3 references): code-review-patterns, refactoring-patterns, security-coding.

- **Examples**: implement-feature, debug-issue, tdd-cycle.
- **Evals**: coding-benchmark (10 tasks), debugging-benchmark (5 tasks), tdd-benchmark (5 tasks).
- **Docs**: GETTING-STARTED (EN + VI), README (EN + VI).
- **GitHub Copilot integration**: copilot-instructions.md, agents/coding-assistant.agent.md.


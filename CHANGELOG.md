# Changelog

All notable changes to the Coding Assistant Agent will be documented in this file.

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


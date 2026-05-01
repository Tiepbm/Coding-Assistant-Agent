---
description: 'Shared coding standards for all Coding Assistant output. Applied at runtime to enforce consistent style across packs and languages.'
applyTo: 'skills/**/references/*.md'
---
# Coding Standards

## Naming Conventions

| Language | Variables/Params | Functions/Methods | Classes/Types | Constants | Files |
|---|---|---|---|---|---|
| Java/Kotlin | `camelCase` | `camelCase` | `PascalCase` | `UPPER_SNAKE` | `PascalCase.java` |
| C# | `camelCase` | `PascalCase` | `PascalCase` | `PascalCase` | `PascalCase.cs` |
| TypeScript/JS | `camelCase` | `camelCase` | `PascalCase` | `UPPER_SNAKE` | `kebab-case.ts` |
| Python | `snake_case` | `snake_case` | `PascalCase` | `UPPER_SNAKE` | `snake_case.py` |
| Go | `camelCase` | `PascalCase` (exported) | `PascalCase` | `PascalCase` | `snake_case.go` |
| Rust | `snake_case` | `snake_case` | `PascalCase` | `UPPER_SNAKE` | `snake_case.rs` |
| Swift | `camelCase` | `camelCase` | `PascalCase` | `camelCase` | `PascalCase.swift` |
| Dart | `camelCase` | `camelCase` | `PascalCase` | `camelCase` | `snake_case.dart` |

When project context is visible, match the project's existing style over these defaults.

## Error Handling

- Always handle errors explicitly. No empty catch blocks.
- Use typed errors/exceptions — not generic `Exception` or `Error`.
- Return meaningful error messages at API boundaries (ProblemDetail, structured JSON).
- Log errors with context (correlation ID, operation name) — never log stack traces to end users.
- Fail fast at startup for missing configuration; fail gracefully at runtime for transient errors.

## Code Organization

- One concept per file. A controller file contains one controller.
- Group by feature/domain, not by technical layer, when project structure allows.
- Keep functions/methods under 30 lines. Extract when logic branches.
- Prefer composition over inheritance.
- Avoid deep nesting (> 3 levels). Use early returns, guard clauses.

## Comments

- Inline comments only for non-obvious decisions ("why", not "what").
- No commented-out code in production.
- No TODO without a linked issue/ticket.
- Use doc comments for public APIs (Javadoc, JSDoc, docstrings, `///`).

## Imports

- Always include imports in code examples — never assume they're implied.
- Group imports: stdlib → third-party → internal. Separate groups with blank line.
- No wildcard imports (`import *`) except in test files where framework convention allows.

## Testing

- Test names describe behavior: `create_withDuplicateKey_throwsConflict`, not `testCreate3`.
- AAA pattern: Arrange → Act → Assert. One assertion concept per test.
- Use factory methods or builders for test data — not raw constructors with 10 params.
- Tests must be deterministic. No `Thread.sleep`, no real clocks, no network calls in unit tests.

## Security (Always Apply)

- Parameterized queries — no exceptions, no "just for admin endpoints".
- Validate input at trust boundaries. Allowlist over blocklist.
- No secrets in code, logs, tests, comments, or environment variables in Dockerfiles.
- Resource-level authorization — query scoped to caller's tenant/ownership.
- Encode output context-appropriately (HTML, URL, SQL, JSON).
- Use framework security primitives. No hand-rolled crypto, JWT parsing, or session management.

## Performance Defaults

- `DECIMAL` for money — never `FLOAT` or `DOUBLE`.
- `TIMESTAMP WITH TIME ZONE` — always store UTC.
- Keyset pagination for APIs — offset only for admin UIs with small datasets.
- Connection pool sizing: pool_size × replicas ≤ DB max_connections.
- Avoid N+1 queries. Use joins, includes, or DataLoader.

## Escalation Criteria — When to Defer to CE7

Recognize these signals and escalate to CE7 Software Engineering Agent instead of proceeding:

| Signal | Example | Why escalate |
|---|---|---|
| **Cross-service boundary change** | "Add a new event consumer in another service" | Topology decision — affects contracts, deployment, ownership |
| **New persistence technology** | "Should we use Elasticsearch for search?" | Vendor selection + data model impact |
| **SLO/SLI definition** | "What should the p99 target be?" | Business + capacity decision, not code |
| **Public API versioning** | "How do we version this API for external consumers?" | Governance policy, not implementation |
| **Breaking schema change** | "Rename this shared Kafka event schema" | Cross-team impact, migration coordination |
| **Multi-tenant isolation** | "How do we separate tenant data?" | Architecture pattern, not code pattern |
| **Major dependency upgrade** | "Migrate from Spring Boot 2 to 3" | Cascading impact across codebase |

**Rule of thumb:** If the decision affects more than one service, more than one team, or cannot be reversed in a single deploy — escalate.

## Performance Budgets

| Endpoint type | Target p99 | Target p50 | Max payload |
|---|---|---|---|
| Synchronous API (CRUD) | < 300ms | < 50ms | 1MB request, 5MB response |
| Search / list with pagination | < 500ms | < 100ms | 100 items per page max |
| File upload (pre-signed URL) | < 1s (URL generation) | < 200ms | Defined by S3/storage policy |
| Background job (per item) | < 30s | < 5s | N/A |
| WebSocket message | < 100ms | < 20ms | 64KB |

When no explicit SLO exists, use these defaults. If a change would breach these budgets, measure before and after with `EXPLAIN ANALYZE` (DB) or load test (API).

## Dependency Governance

- **Adding a new dependency**: Verify it's actively maintained (commits in last 6 months), has no known critical CVEs, and is used by > 1000 projects (npm) or equivalent adoption signal.
- **Pinned versions**: Use exact versions in lock files. No `^` or `~` ranges in production dependencies.
- **Audit on every build**: `npm audit`, `pip-audit`, `govulncheck`, `cargo audit`, `dotnet list package --vulnerable`.
- **One dependency per concern**: Don't add both Axios and node-fetch. Don't add both Lodash and Ramda.
- **Flag for review**: Any dependency that touches crypto, auth, serialization, or network — review before merging.

## Architectural Decision Records (Lightweight)

When a Senior+ developer makes a non-trivial implementation choice (not escalation-worthy, but worth documenting), record it inline:

```
// ADR: Using keyset pagination instead of offset.
// Context: payments table has 2M+ rows; offset pagination degrades at page > 100.
// Decision: Composite cursor (created_at, id) with index.
// Consequence: "Jump to page N" not supported; acceptable for this API consumer.
```

For decisions that affect multiple files or future developers, create a brief ADR in the project's `docs/adr/` directory (if the project uses ADRs) or add a section in the PR description.

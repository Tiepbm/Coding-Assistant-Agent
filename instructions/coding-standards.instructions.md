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

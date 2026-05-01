---
name: api-design-pack
description: 'Use when implementing approved API contracts: OpenAPI specs, GraphQL SDL/resolvers, gRPC proto files, contract tests. Code-level patterns only — defer API trade-offs (protocol choice, versioning policy, public vs internal, breaking-change governance) to CE7.'
---
# API Design Pack (Implementation Patterns)

> **Scope boundary:** This pack covers *how to implement* approved API contracts and code, NOT whether to choose REST vs GraphQL/gRPC, public-facing versioning policy, or backwards-compatibility governance — those are architecture decisions → defer to CE7 Software Engineering Agent.

## When to Use
- Writing or updating OpenAPI 3.1 spec details for an approved REST endpoint.
- Implementing GraphQL schema (SDL) and resolver code for approved fields/types.
- Writing gRPC `.proto` files and generated client/server code.
- Adding contract tests (Pact, Spring Cloud Contract, schemathesis).
- Generating typed clients/servers from spec (oapi-codegen, openapi-generator, buf, graphql-codegen).

## When NOT to Use
- Choosing REST vs GraphQL vs gRPC for a new system → CE7.
- Designing public API versioning strategy → CE7.
- Internal service implementation behind the contract → `backend-pack`.
- Database-level concerns → `database-pack`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `openapi-first` | Writing OpenAPI 3.1 specs, generating server/client, request validation. |
| `graphql-schema` | Implementing GraphQL SDL, resolvers, DataLoader, codegen, and schema-change checks. |
| `grpc-proto` | Writing protobuf files, services, streaming RPCs, generated stubs. |
| `contract-testing` | Consumer-driven contracts (Pact), provider verification, schemathesis fuzzing. |

## Cross-Pack Handoffs
- → `backend-pack/<stack>` for implementing the resolver/handler behind the contract.
- → `testing-pack/integration-testing` for contract-test infrastructure.
- → `observability-pack/otel-tracing` for instrumenting spans with operation/RPC name.
- → `quality-pack/code-review-patterns` for reviewing schema changes (breaking-change check).


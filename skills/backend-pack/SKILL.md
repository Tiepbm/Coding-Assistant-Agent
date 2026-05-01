---
name: backend-pack
description: 'Use when writing server-side code: REST APIs, services, data access, authentication, middleware, background jobs, message consumers, or concurrency patterns in Java/Spring Boot, Kotlin/Spring, C#/.NET, Node.js/Express, Python/FastAPI, Go, or Rust.'
---
# Backend Pack

## When to Use
- REST/GraphQL/gRPC endpoint implementation (controllers, routes, handlers).
- Service layer logic (business rules, validation, orchestration).
- Data access code (repositories, queries, transactions, ORM mappings).
- Authentication/authorization middleware and guards.
- Background workers, scheduled jobs, message consumers.
- External API client integration (HTTP clients, retry, circuit breaker).
- Concurrency patterns (virtual threads, async/await, goroutines, tokio, Channels).

## When NOT to Use
- UI components, hooks, state management → `frontend-pack`.
- SQL query optimization or schema design → `database-pack`.
- Test strategy or test code → `testing-pack`.
- Docker, CI/CD, deployment → `devops-pack`.
- API contract authoring (OpenAPI/GraphQL/proto) → `api-design-pack`.
- Logging/tracing/metrics instrumentation → `observability-pack`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `java-spring-boot` | Spring Boot 3 controllers, services, JPA repositories, Kafka listeners, Resilience4j patterns. |
| `kotlin-spring` | Kotlin + Spring Boot 3 with coroutines, R2DBC, MockK tests, sealed-class errors. |
| `dotnet-aspnet-core` | ASP.NET Core Minimal APIs or MVC, EF Core, middleware, HttpClient, BackgroundService. |
| `nodejs-express` | Express/Fastify routes, middleware, Prisma/TypeORM queries, async Node.js patterns. |
| `python-fastapi` | FastAPI endpoints, SQLAlchemy models, Pydantic schemas, async Python services. |
| `go-standard` | Go HTTP handlers, sqlc/pgx data access, errgroup, table-driven tests, govulncheck. |
| `rust-axum` | Rust + Axum extractors, sqlx, thiserror + IntoResponse, tokio tests. |
| `concurrency-patterns` | Cross-stack concurrency: virtual threads, Channels, p-limit, TaskGroup, errgroup, JoinSet. |
| `resilience-handoff` | Wiring timeouts/retries/circuit-breaker/bulkhead in code; routes pattern + threshold decisions to CE7. |

## Cross-Pack Handoffs
- → `database-pack` for SQL queries, migrations, ORM configuration.
- → `testing-pack` for unit/integration tests of backend code.
- → `quality-pack` for code review and security coding patterns.
- → `devops-pack` for containerization and CI/CD of backend services.
- → `frontend-pack` when backend serves a frontend (API contracts, CORS, auth tokens).
- → `software-engineering-agent/skills/resilience-performance-pack` for resilience pattern + threshold design (per `resilience-handoff`).

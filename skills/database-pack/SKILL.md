---
name: database-pack
description: 'Use when writing SQL queries, ORM code, database migrations, schema changes, indexing strategy, or NoSQL operations (Redis, MongoDB, DynamoDB).'
---
# Database Pack

## When to Use
- Writing or optimizing SQL queries (CRUD, joins, aggregations).
- ORM configuration and query patterns (EF Core, JPA, Prisma, SQLAlchemy).
- Database migrations (schema changes, data backfills, expand-contract).
- Indexing strategy (composite, partial, covering indexes).
- NoSQL operations (Redis caching, MongoDB documents, DynamoDB access patterns).
- Transaction patterns and isolation levels.

## When NOT to Use
- Service layer code that calls the repository → `backend-pack`.
- Test setup with Testcontainers → `testing-pack/integration-testing`.
- Database infrastructure (RDS, CloudSQL) → `devops-pack`.
- Query performance profiling → `debugging-pack/performance-debugging`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `sql-patterns` | Raw SQL: parameterized queries, pagination, indexing, transactions, migrations. |
| `orm-patterns` | ORM-specific: EF Core, JPA/Hibernate, Prisma, SQLAlchemy query and mapping patterns. |
| `nosql-patterns` | Redis (cache, locks, pub/sub), MongoDB (documents, indexes), DynamoDB (partition keys, GSI). |
| `migration-safety` | Zero-downtime expand-contract, online DDL, batched backfill, rollback strategy per DB. |
| `storage-search-handoff` | Wiring S3/object-storage SDK + signed URLs + search index integration; routes retention/projection/reindex design to CE7. |

## Cross-Pack Handoffs
- → `backend-pack` for repository/service layer that uses these queries.
- → `testing-pack` for integration tests with real databases.
- → `debugging-pack` for slow query analysis and explain plans.
- → `devops-pack` for database infrastructure and backup strategy.
- → `quality-pack` for migration review and data safety.
- → `software-engineering-agent/skills/storage-search-pack` for object-storage retention + search projection design (per `storage-search-handoff`).

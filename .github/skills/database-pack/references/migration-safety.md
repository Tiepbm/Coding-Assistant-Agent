---
name: migration-safety
description: 'Zero-downtime schema migrations: expand-contract pattern, online DDL, backfill strategies, rollback safety per database (Postgres, MySQL, SQL Server).'
---
# Migration Safety Patterns

## Golden Rule — Expand → Migrate → Contract

NEVER deploy a backward-incompatible schema change in one step. Split into 3 deploys:

```
Deploy 1 (Expand):   add new column/table/index — old code still works
Deploy 2 (Migrate):  app reads/writes both old and new; backfill data
Deploy 3 (Contract): drop old column/table after verifying no readers
```

## Renaming a Column (BAD vs GOOD)

```sql
-- BAD: single migration; breaks all running pods during rolling deploy
ALTER TABLE payments RENAME COLUMN amount TO amount_cents;

-- GOOD: 3 deploys
-- ── Deploy 1: add new column, dual-write
ALTER TABLE payments ADD COLUMN amount_cents BIGINT;
-- App writes to both; reads from old.

-- ── Deploy 2: backfill + read from new
UPDATE payments SET amount_cents = (amount * 100)::BIGINT
WHERE amount_cents IS NULL;  -- run in batches (see below)
-- App reads from amount_cents; still dual-writes.

-- ── Deploy 3: drop old column
ALTER TABLE payments DROP COLUMN amount;
```

## Postgres — Avoid Long Locks

```sql
-- BAD: locks entire table for the duration of the rewrite
ALTER TABLE payments ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PENDING';
-- (PG ≥ 11 fast for DEFAULT, but adding NOT NULL on existing column rewrites table)

-- GOOD: split nullable add → backfill → enforce NOT NULL
ALTER TABLE payments ADD COLUMN status VARCHAR(20);            -- instant, no rewrite
UPDATE payments SET status = 'PENDING' WHERE status IS NULL;   -- batched
ALTER TABLE payments ADD CONSTRAINT payments_status_not_null
    CHECK (status IS NOT NULL) NOT VALID;                      -- skip full scan
ALTER TABLE payments VALIDATE CONSTRAINT payments_status_not_null;
ALTER TABLE payments ALTER COLUMN status SET NOT NULL;         -- now cheap

-- Index — concurrent (no write block)
CREATE INDEX CONCURRENTLY idx_payments_status ON payments(status);
DROP   INDEX CONCURRENTLY IF EXISTS idx_payments_old;

-- Set safe lock_timeout for migrations
SET lock_timeout = '5s';
SET statement_timeout = '60s';
```

## MySQL — Online DDL / pt-online-schema-change

```sql
-- ALGORITHM=INPLACE, LOCK=NONE — preferred when supported
ALTER TABLE payments
  ADD COLUMN status VARCHAR(20) NULL,
  ALGORITHM=INPLACE, LOCK=NONE;

-- For unsupported ops or older MySQL: pt-online-schema-change / gh-ost
pt-online-schema-change --alter "ADD COLUMN status VARCHAR(20)" \
  D=app,t=payments --execute
```

## Batched Backfill (avoid long transactions)

```sql
-- Postgres: keyset loop, commits per batch (run from app, not migration tool)
DO $$
DECLARE last_id UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
  LOOP
    WITH batch AS (
      SELECT id FROM payments WHERE id > last_id AND amount_cents IS NULL
      ORDER BY id LIMIT 5000
    )
    UPDATE payments p SET amount_cents = (p.amount * 100)::BIGINT
    FROM batch WHERE p.id = batch.id
    RETURNING p.id INTO last_id;
    EXIT WHEN NOT FOUND;
    PERFORM pg_sleep(0.1);  -- back off to avoid replication lag
  END LOOP;
END $$;
```

## Destructive Operation Checklist

Before `DROP COLUMN`, `DROP TABLE`, `DROP INDEX`, `TRUNCATE`:
- [ ] grep codebase for column/table name — zero references in deployed version
- [ ] check ORM models/migrations branches — no stale code
- [ ] DB user audit log shows no reads in last 7 days (`pg_stat_user_tables`)
- [ ] backup verified within 24h
- [ ] rollback script written + reviewed
- [ ] feature flag gates the new code path

## Rollback Strategy

```sql
-- Every forward migration MUST have a tested down migration
-- Liquibase / Flyway / Alembic / Prisma — define rollback explicitly

-- Rollback-safe pattern: never drop in same deploy you add
-- Deploy 3 contract step is the ONLY destructive deploy → easy to revert by re-adding column
```

## Tooling

| Tool | Stack | Notes |
|---|---|---|
| Flyway / Liquibase | JVM | versioned SQL; supports `repeatable` |
| Alembic | Python/SQLAlchemy | autogenerate + manual review |
| Prisma Migrate | Node.js | `migrate diff` for review |
| EF Core Migrations | .NET | `dotnet ef migrations add` |
| Atlas / sqitch | language-agnostic | declarative diff, drift detection |
| pt-osc / gh-ost | MySQL | online schema change without locks |

## Verification

```bash
# Dry-run + diff against prod schema
flyway info validate
prisma migrate diff --from-url "$PROD_URL" --to-schema-datamodel prisma/schema.prisma
atlas migrate lint --dev-url "docker://postgres/16/dev"
```

## Cross-Pack Handoffs

- → `database-pack/sql-patterns` for query design after migration.
- → `devops-pack/ci-cd-pipelines` for migration job ordering (run before app deploy).
- → `observability-pack/metrics-instrumentation` for monitoring lock waits, replication lag during migration.


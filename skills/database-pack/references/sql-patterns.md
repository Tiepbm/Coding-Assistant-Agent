---
name: sql-patterns
description: 'SQL patterns: parameterized queries, pagination (keyset vs offset), indexing strategy, transactions, migration patterns.'
---
# SQL Patterns

## Parameterized Queries (NEVER String Concatenation)

```sql
-- BAD: SQL injection vulnerability
SELECT * FROM payments WHERE tenant_id = '" + tenantId + "';

-- GOOD: Parameterized query (every language/framework)
```

```java
// Java (JDBC)
PreparedStatement stmt = conn.prepareStatement(
    "SELECT id, amount, status FROM payments WHERE tenant_id = ? AND status = ?");
stmt.setObject(1, tenantId);
stmt.setString(2, "PENDING");
ResultSet rs = stmt.executeQuery();
```

```csharp
// C# (Dapper)
var payments = await connection.QueryAsync<Payment>(
    "SELECT id, amount, status FROM payments WHERE tenant_id = @TenantId AND status = @Status",
    new { TenantId = tenantId, Status = "PENDING" });
```

```typescript
// Node.js (pg)
const { rows } = await pool.query(
  'SELECT id, amount, status FROM payments WHERE tenant_id = $1 AND status = $2',
  [tenantId, 'PENDING']
);
```

```python
# Python (asyncpg)
rows = await conn.fetch(
    "SELECT id, amount, status FROM payments WHERE tenant_id = $1 AND status = $2",
    tenant_id, "PENDING"
)
```

## Pagination: Keyset vs Offset

```sql
-- BAD: Offset pagination — slow on large tables (scans and discards rows)
SELECT * FROM payments ORDER BY created_at DESC LIMIT 20 OFFSET 10000;
-- PostgreSQL must scan 10,020 rows to return 20

-- GOOD: Keyset (cursor) pagination — consistent performance
SELECT id, amount, status, created_at
FROM payments
WHERE created_at < '2024-01-15T10:00:00Z'  -- cursor from previous page
ORDER BY created_at DESC
LIMIT 20;

-- For composite cursor (when created_at is not unique):
SELECT id, amount, status, created_at
FROM payments
WHERE (created_at, id) < ('2024-01-15T10:00:00Z', 'pay-abc')
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

```
When to use offset: Small datasets (< 10K rows), admin UIs, "jump to page N" required.
When to use keyset: Large datasets, infinite scroll, API pagination, real-time feeds.
```

## Indexing Strategy

```sql
-- Single column index — for equality lookups
CREATE INDEX idx_payments_tenant_id ON payments (tenant_id);

-- Composite index — column order matters (most selective first for equality)
-- Supports: WHERE tenant_id = ? AND status = ?
-- Supports: WHERE tenant_id = ? (prefix)
-- Does NOT support: WHERE status = ? (not a prefix)
CREATE INDEX idx_payments_tenant_status ON payments (tenant_id, status);

-- Covering index — includes all columns needed, avoids table lookup
CREATE INDEX idx_payments_list ON payments (tenant_id, created_at DESC)
    INCLUDE (id, amount, status, currency);

-- Partial index — smaller, faster, for common queries
CREATE INDEX idx_payments_pending ON payments (tenant_id, created_at)
    WHERE status = 'PENDING';

-- Unique constraint (also creates an index)
ALTER TABLE payments ADD CONSTRAINT uq_payments_idempotency
    UNIQUE (tenant_id, idempotency_key);
```

```sql
-- Check if your query uses the index
EXPLAIN ANALYZE
SELECT id, amount, status FROM payments
WHERE tenant_id = 'tenant-123' AND status = 'PENDING'
ORDER BY created_at DESC
LIMIT 20;

-- Look for: Index Scan or Index Only Scan (good)
-- Avoid: Seq Scan on large tables (bad — missing index)
```

## Transaction Patterns

```sql
-- Short transactions — hold locks briefly
BEGIN;
  UPDATE payments SET status = 'CAPTURED', updated_at = NOW()
  WHERE id = 'pay-123' AND status = 'PENDING';
  -- Check affected rows: if 0, someone else already captured it (optimistic lock)

  INSERT INTO outbox_events (aggregate_id, event_type, payload)
  VALUES ('pay-123', 'payment.captured', '{"paymentId": "pay-123"}');
COMMIT;
```

```
Isolation Levels (PostgreSQL):
┌──────────────────┬──────────────┬──────────────┬──────────────┐
│ Level            │ Dirty Read   │ Non-Repeat   │ Phantom      │
├──────────────────┼──────────────┼──────────────┼──────────────┤
│ Read Committed   │ No           │ Possible     │ Possible     │ ← Default, good for most
│ Repeatable Read  │ No           │ No           │ No*          │ ← Financial reports
│ Serializable     │ No           │ No           │ No           │ ← Strongest, slowest
└──────────────────┴──────────────┴──────────────┴──────────────┘
* PostgreSQL RR prevents phantoms via MVCC (unlike MySQL)

Rule: Use Read Committed unless you have a specific reason for stronger isolation.
```

## Migration Patterns

### Expand-Contract (Zero-Downtime)

```sql
-- Phase 1: EXPAND — Add new column (nullable, no breaking change)
ALTER TABLE payments ADD COLUMN payment_method VARCHAR(20);

-- Phase 2: MIGRATE — Backfill data (in batches, not one giant UPDATE)
UPDATE payments SET payment_method = 'CARD'
WHERE payment_method IS NULL AND id IN (
    SELECT id FROM payments WHERE payment_method IS NULL LIMIT 1000
);

-- Phase 3: CONTRACT — Add constraint after all data is migrated
ALTER TABLE payments ALTER COLUMN payment_method SET NOT NULL;
ALTER TABLE payments ALTER COLUMN payment_method SET DEFAULT 'CARD';

-- Phase 4: CLEANUP — Drop old column (if replacing)
-- Only after all application code uses the new column
ALTER TABLE payments DROP COLUMN old_payment_type;
```

### Safe Backfill Pattern

```sql
-- BAD: One giant UPDATE locks the entire table
UPDATE payments SET payment_method = 'CARD' WHERE payment_method IS NULL;

-- GOOD: Batch update with progress tracking
DO $$
DECLARE
  batch_size INT := 1000;
  updated INT;
BEGIN
  LOOP
    UPDATE payments SET payment_method = 'CARD'
    WHERE id IN (
      SELECT id FROM payments
      WHERE payment_method IS NULL
      LIMIT batch_size
      FOR UPDATE SKIP LOCKED  -- Don't block concurrent transactions
    );
    GET DIAGNOSTICS updated = ROW_COUNT;
    EXIT WHEN updated = 0;
    RAISE NOTICE 'Updated % rows', updated;
    COMMIT;
  END LOOP;
END $$;
```

## Anti-Patterns

- **String concatenation for SQL**: Always use parameterized queries — no exceptions.
- `SELECT *` in application queries — select only needed columns.
- Offset pagination on large tables — use keyset pagination.
- Long-running transactions holding locks — keep transactions short.
- Adding indexes without checking existing ones — redundant indexes slow writes.
- `NOT NULL` constraint on existing column without backfill — migration fails.
- `DROP COLUMN` during deploy — old app instances still reference it.

## Gotchas

- PostgreSQL `SERIAL` vs `GENERATED ALWAYS AS IDENTITY` — prefer IDENTITY (SQL standard).
- `DECIMAL(18,2)` for money — never use `FLOAT` or `DOUBLE`.
- `TIMESTAMP WITH TIME ZONE` — always store in UTC, convert on display.
- Index on `WHERE status = 'PENDING'` — partial index is smaller and faster.
- `FOR UPDATE SKIP LOCKED` — essential for worker patterns (prevents double-processing).
- `EXPLAIN ANALYZE` runs the query — use `EXPLAIN` (without ANALYZE) for destructive queries.
- PostgreSQL `VACUUM` — autovacuum handles most cases, but monitor bloat on high-write tables.

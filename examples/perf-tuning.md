# Example: Perf-Tune a Slow Endpoint (p99 1.8s → 120ms)

Stack: Node.js + Express + Prisma + Postgres. Pattern is universal.

**Symptom:** `GET /tenants/:id/payments?status=PENDING` p99 = 1.8s, p50 = 220ms. SLO is p99 < 300ms.

## 1. Measure Before Touching Code

Don't guess. Get evidence per layer.

```bash
# Reproduce locally with realistic data volume
node scripts/seed-payments.js --tenant t1 --count 500000

# Latency histogram
autocannon -c 10 -d 30 'http://localhost:3000/tenants/t1/payments?status=PENDING'
# Result: p50=200ms, p99=1900ms — matches prod
```

Add OTel span around handler + DB call (see `observability-pack/otel-tracing`). In Jaeger:

```
GET /tenants/:id/payments         1850ms
├─ auth.middleware                   3ms
├─ db.query("SELECT * FROM ...")  1810ms   ← 98% of time
└─ json.serialize                    25ms
```

Layer pinpointed: database. Now look at the query.

## 2. Inspect the Query

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM payments
WHERE tenant_id = 't1' AND status = 'PENDING'
ORDER BY created_at DESC
LIMIT 50;

-- Output:
-- Sort  (cost=... rows=...) (actual time=1750..1810 rows=50)
--   Sort Method: top-N heapsort
--   ->  Seq Scan on payments  (cost=... rows=12000) (actual time=15..1700 rows=12453)
--         Filter: (tenant_id = 't1'::uuid) AND (status = 'PENDING'::text)
--         Rows Removed by Filter: 487547
```

Diagnosis: **sequential scan on 500k rows**, filtering 12k matches, sorting in memory. No suitable index.

## 3. Hypothesis → Minimal Fix

Composite index matching filter + sort:

```sql
-- BAD: single-column index only on tenant_id
CREATE INDEX idx_payments_tenant ON payments(tenant_id);

-- GOOD: matches WHERE + ORDER BY for index-only scan + sort avoidance
CREATE INDEX CONCURRENTLY idx_payments_tenant_status_created
  ON payments(tenant_id, status, created_at DESC);
```

Re-run EXPLAIN: **Index Scan, 12ms**. p99 now 95ms. 

## 4. Find the N+1

After the query fix, profile a different endpoint with similar pattern:

```typescript
// BAD: N+1 — fetch payments, then loop fetch users
const payments = await prisma.payment.findMany({ where: { tenantId } });
for (const p of payments) {
  p.createdBy = await prisma.user.findUnique({ where: { id: p.createdById } }); // N queries
}
```

```typescript
// GOOD: single join via Prisma include
const payments = await prisma.payment.findMany({
  where: { tenantId },
  include: { createdBy: { select: { id: true, name: true } } },
  take: 50,
});
```

Or via DataLoader if response shape is GraphQL — see `api-design-pack/graphql-schema`.

## 5. Cache Hot Read (Cache-Aside)

If query is still hot but stable, add Redis cache (see `database-pack/nosql-patterns`):

```typescript
async function listPendingPayments(tenantId: string): Promise<Payment[]> {
  const key = `payments:pending:${tenantId}`;
  const cached = await redis.get(key);
  if (cached) {
    metrics.cacheHits.inc({ key: 'payments:pending' });
    return JSON.parse(cached);
  }
  metrics.cacheMisses.inc({ key: 'payments:pending' });
  const fresh = await db.query(...);
  await redis.set(key, JSON.stringify(fresh), 'EX', 30); // 30s TTL
  return fresh;
}

// Invalidate on write
async function createPayment(req) {
  const p = await db.insert(...);
  await redis.del(`payments:pending:${p.tenantId}`);
  return p;
}
```

## 6. Pagination — Switch from OFFSET to Keyset

For "load more" UX:

```typescript
// BAD: OFFSET — gets slower as offset grows (full scan to skip)
SELECT * FROM payments WHERE tenant_id=$1 ORDER BY created_at DESC OFFSET 5000 LIMIT 50;

// GOOD: keyset — uses index, O(log n) regardless of page
SELECT * FROM payments
WHERE tenant_id=$1
  AND (created_at, id) < ($lastCreatedAt, $lastId)  -- composite cursor
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

## 7. Verify with Load Test + SLO

```bash
autocannon -c 50 -d 60 'http://localhost:3000/tenants/t1/payments?status=PENDING'
# Result: p50=20ms, p99=120ms ✓ (SLO: <300ms)

# Production: deploy behind feature flag (see quality-pack/feature-flags),
# canary at 5%, watch p99 dashboard for 1h, then ramp.
```

## Verification Checklist

- [ ] EXPLAIN ANALYZE before + after committed in PR description.
- [ ] Index added with `CONCURRENTLY` (no table lock).
- [ ] Load test results documented.
- [ ] Cache invalidation verified (write → next read returns fresh).
- [ ] Metrics added: `payments_list_duration_seconds`, `payments_cache_hit_ratio`.
- [ ] No regression in tests; coverage maintained.

## Skills Used

- `debugging-pack/performance-debugging` — measure first, layer-by-layer attribution.
- `database-pack/sql-patterns` — composite index, keyset pagination.
- `database-pack/nosql-patterns` — cache-aside with TTL + invalidation.
- `observability-pack/otel-tracing` — pinpoint slow span.
- `observability-pack/metrics-instrumentation` — RED metrics on the endpoint.
- `quality-pack/feature-flags` — safe canary rollout.


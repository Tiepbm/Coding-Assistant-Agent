---
name: nosql-patterns
description: 'NoSQL patterns: Redis (cache-aside, locks, pub/sub), MongoDB (document design, indexes), DynamoDB (partition keys, GSI, single-table).'
---
# NoSQL Patterns

## Redis: Cache-Aside Pattern

```typescript
// BAD: No cache invalidation strategy, no TTL
const data = await redis.get('payments');
if (!data) {
  const payments = await db.getPayments();
  await redis.set('payments', JSON.stringify(payments)); // Stale forever
}

// GOOD: Cache-aside with TTL and invalidation
import { Redis } from 'ioredis';

class PaymentCache {
  constructor(
    private readonly redis: Redis,
    private readonly ttlSeconds: number = 300 // 5 minutes
  ) {}

  async getOrFetch(
    tenantId: string,
    fetcher: () => Promise<Payment[]>
  ): Promise<Payment[]> {
    const key = `payments:${tenantId}:list`;
    const cached = await this.redis.get(key);

    if (cached) {
      return JSON.parse(cached);
    }

    const data = await fetcher();
    await this.redis.setex(key, this.ttlSeconds, JSON.stringify(data));
    return data;
  }

  async invalidate(tenantId: string): Promise<void> {
    // Delete all cache keys for this tenant
    const keys = await this.redis.keys(`payments:${tenantId}:*`);
    if (keys.length > 0) {
      await this.redis.del(...keys);
    }
  }
}
```

```java
// Java: Spring Cache with Redis
@Service
public class PaymentService {

    @Cacheable(value = "payments", key = "#tenantId + ':' + #id")
    public PaymentResponse findById(UUID tenantId, UUID id) {
        return paymentRepository.findById(id)
            .map(PaymentResponse::from)
            .orElseThrow(() -> new NotFoundException("Payment not found"));
    }

    @CacheEvict(value = "payments", key = "#tenantId + ':' + #result.id")
    @Transactional
    public Payment create(UUID tenantId, CreatePaymentRequest request) {
        // Cache evicted after successful creation
        return doCreate(tenantId, request);
    }
}
```

## Redis: Distributed Lock

```typescript
// BAD: No lock — concurrent requests process same payment twice
async function processPayment(paymentId: string) {
  const payment = await db.findById(paymentId);
  if (payment.status === 'PENDING') {
    await psp.charge(payment);
    await db.updateStatus(paymentId, 'CAPTURED');
  }
}

// GOOD: Redis lock with automatic expiry (Redlock pattern)
import { Redis } from 'ioredis';

class RedisLock {
  constructor(private readonly redis: Redis) {}

  async acquire(
    key: string,
    ttlMs: number = 10_000
  ): Promise<string | null> {
    const token = crypto.randomUUID();
    const result = await this.redis.set(
      `lock:${key}`,
      token,
      'PX', ttlMs,
      'NX' // Only set if not exists
    );
    return result === 'OK' ? token : null;
  }

  async release(key: string, token: string): Promise<boolean> {
    // Lua script: only delete if token matches (prevent releasing someone else's lock)
    const script = `
      if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
      else
        return 0
      end
    `;
    const result = await this.redis.eval(script, 1, `lock:${key}`, token);
    return result === 1;
  }
}

// Usage
async function processPayment(paymentId: string) {
  const lock = new RedisLock(redis);
  const token = await lock.acquire(`payment:${paymentId}`);

  if (!token) {
    throw new ConflictError('Payment is being processed');
  }

  try {
    const payment = await db.findById(paymentId);
    if (payment.status !== 'PENDING') return;
    await psp.charge(payment);
    await db.updateStatus(paymentId, 'CAPTURED');
  } finally {
    await lock.release(`payment:${paymentId}`, token);
  }
}
```

## Redis: Key Design

```
# Pattern: {entity}:{scope}:{identifier}:{attribute}
payments:tenant-123:pay-456           # Single payment
payments:tenant-123:list              # Payment list cache
payments:tenant-123:pending:count     # Counter
lock:payment:pay-456                  # Distributed lock
session:user-789                      # User session
rate:api:tenant-123:minute            # Rate limiting counter

# Use colons for hierarchy, hyphens within segments
# Keep keys short — Redis stores keys in memory
```

## MongoDB: Document Design

```javascript
// BAD: Deeply nested, unbounded arrays
{
  _id: "order-123",
  customer: { /* full customer document */ },
  items: [
    // Could grow to thousands of items
    { product: { /* full product document */ }, quantity: 1 }
  ],
  auditLog: [
    // Unbounded — document grows forever
    { action: "created", timestamp: "2024-01-15T10:00:00Z" }
  ]
}

// GOOD: Bounded embedding, reference for unbounded data
// payments collection
{
  _id: ObjectId("..."),
  tenantId: "tenant-123",
  amount: NumberDecimal("100.00"),
  currency: "VND",
  status: "PENDING",
  customer: {
    id: "cust-456",       // Reference, not full document
    name: "John Doe"      // Denormalized for display (bounded)
  },
  lineItems: [            // Bounded (max ~20 items per payment)
    { sku: "SKU-1", amount: NumberDecimal("50.00"), quantity: 1 },
    { sku: "SKU-2", amount: NumberDecimal("50.00"), quantity: 1 }
  ],
  createdAt: ISODate("2024-01-15T10:00:00Z"),
  updatedAt: ISODate("2024-01-15T10:00:00Z")
}

// audit_logs collection (separate — unbounded)
{
  _id: ObjectId("..."),
  entityType: "payment",
  entityId: "pay-123",
  action: "status_changed",
  before: { status: "PENDING" },
  after: { status: "CAPTURED" },
  userId: "user-789",
  timestamp: ISODate("2024-01-15T10:30:00Z")
}
```

## MongoDB: Indexes

```javascript
// Compound index — supports queries on tenantId + status + createdAt
db.payments.createIndex(
  { tenantId: 1, status: 1, createdAt: -1 },
  { name: "idx_tenant_status_date" }
);

// Partial index — only index pending payments (smaller, faster)
db.payments.createIndex(
  { tenantId: 1, createdAt: -1 },
  { partialFilterExpression: { status: "PENDING" }, name: "idx_pending" }
);

// Unique index
db.payments.createIndex(
  { tenantId: 1, idempotencyKey: 1 },
  { unique: true, name: "uq_idempotency" }
);

// TTL index — auto-delete expired sessions
db.sessions.createIndex(
  { expiresAt: 1 },
  { expireAfterSeconds: 0, name: "idx_session_ttl" }
);
```

## MongoDB: Aggregation Pipeline

```javascript
// Payment summary by status per tenant
db.payments.aggregate([
  { $match: { tenantId: "tenant-123", createdAt: { $gte: ISODate("2024-01-01") } } },
  { $group: {
      _id: "$status",
      count: { $sum: 1 },
      totalAmount: { $sum: "$amount" },
      avgAmount: { $avg: "$amount" }
  }},
  { $sort: { totalAmount: -1 } },
  { $project: {
      status: "$_id",
      count: 1,
      totalAmount: { $round: ["$totalAmount", 2] },
      avgAmount: { $round: ["$avgAmount", 2] },
      _id: 0
  }}
]);
```

## DynamoDB: Partition Key Design

```
# Single-table design basics
# PK (Partition Key) + SK (Sort Key) = composite primary key

# Access patterns determine key design:
# 1. Get payment by ID         → PK=PAY#pay-123, SK=PAY#pay-123
# 2. List payments by tenant   → PK=TENANT#t-123, SK=PAY#2024-01-15#pay-123
# 3. Get customer by ID        → PK=CUST#c-456, SK=CUST#c-456
# 4. List payments by customer → GSI1: PK=CUST#c-456, SK=PAY#2024-01-15

┌──────────────────────┬──────────────────────────────┬─────────┐
│ PK                   │ SK                           │ Data    │
├──────────────────────┼──────────────────────────────┼─────────┤
│ TENANT#t-123         │ PAY#2024-01-15#pay-001       │ payment │
│ TENANT#t-123         │ PAY#2024-01-15#pay-002       │ payment │
│ PAY#pay-001          │ PAY#pay-001                  │ payment │
│ CUST#c-456           │ CUST#c-456                   │ customer│
└──────────────────────┴──────────────────────────────┴─────────┘
```

```python
# Python (boto3)
import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource('dynamodb').Table('payments')

# Get single payment
response = table.get_item(Key={'PK': f'PAY#{payment_id}', 'SK': f'PAY#{payment_id}'})
payment = response.get('Item')

# List payments by tenant (sorted by date)
response = table.query(
    KeyConditionExpression=Key('PK').eq(f'TENANT#{tenant_id}') & Key('SK').begins_with('PAY#'),
    ScanIndexForward=False,  # Descending
    Limit=20,
)
payments = response['Items']

# Pagination with LastEvaluatedKey
if 'LastEvaluatedKey' in response:
    next_page = table.query(
        KeyConditionExpression=Key('PK').eq(f'TENANT#{tenant_id}'),
        ExclusiveStartKey=response['LastEvaluatedKey'],
        Limit=20,
    )
```

## Anti-Patterns

- **Redis as primary database**: Redis is a cache/store — use a real DB for source of truth.
- **Unbounded MongoDB documents**: Arrays that grow without limit hit the 16MB document limit.
- `KEYS *` in Redis production — blocks the server. Use `SCAN` instead.
- DynamoDB `Scan` for queries — always use `Query` with partition key.
- Storing large blobs in Redis — use object storage (S3) with Redis as index.
- MongoDB without indexes on query fields — full collection scan.
- DynamoDB hot partition — distribute writes across partition keys.

## Gotchas

- Redis `SETEX` is atomic (SET + EXPIRE) — prefer over separate SET then EXPIRE.
- MongoDB `NumberDecimal` for money — `Number` (double) has floating-point precision issues.
- DynamoDB `Query` returns max 1MB per call — use `LastEvaluatedKey` for pagination.
- Redis `KEYS` pattern matching is O(N) — use `SCAN` with cursor for production.
- MongoDB transactions require replica set — not available on standalone instances.
- DynamoDB `PutItem` overwrites by default — use `ConditionExpression` for conditional writes.
- Redis pub/sub messages are fire-and-forget — use Streams for reliable messaging.

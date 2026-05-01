---
name: orm-patterns
description: 'ORM patterns: EF Core, JPA/Hibernate, Prisma, SQLAlchemy 2.0 — projections, eager loading, batch queries, and anti-patterns.'
---
# ORM Patterns

## EF Core Patterns

```csharp
// BAD: Loading full entity graph, lazy loading triggers N+1
var payments = await _db.Payments
    .Include(p => p.Customer)
    .Include(p => p.LineItems)
    .ToListAsync(); // Loads everything into memory

// GOOD: Projection to DTO — only loads needed columns
var payments = await _db.Payments
    .AsNoTracking() // Read-only, no change tracking overhead
    .Where(p => p.TenantId == tenantId && p.Status == "PENDING")
    .OrderByDescending(p => p.CreatedAt)
    .Select(p => new PaymentSummary(
        p.Id,
        p.Amount,
        p.Currency,
        p.Customer.Name, // Single JOIN, not lazy load
        p.CreatedAt))
    .Take(20)
    .ToListAsync(ct);

// Compiled query — pre-compiled for hot paths
private static readonly Func<AppDbContext, Guid, Guid, Task<Payment?>> FindByKeyQuery =
    EF.CompileAsyncQuery((AppDbContext db, Guid tenantId, Guid key) =>
        db.Payments.FirstOrDefault(p =>
            p.TenantId == tenantId && p.IdempotencyKey == key));

// Usage
var payment = await FindByKeyQuery(_db, tenantId, idempotencyKey);
```

```csharp
// Bulk operations — avoid SaveChanges per item
// BAD: N round-trips
foreach (var item in items)
{
    _db.Payments.Add(item);
    await _db.SaveChangesAsync(); // N database calls
}

// GOOD: Single SaveChanges for batch
_db.Payments.AddRange(items);
await _db.SaveChangesAsync(); // 1 database call

// For large batches (1000+), use EF Core bulk extensions
await _db.BulkInsertAsync(items);
```

## JPA / Hibernate Patterns

```java
// BAD: Lazy loading in API response serialization → N+1
@Entity
public class Payment {
    @ManyToOne(fetch = FetchType.LAZY)
    private Customer customer; // Loaded when Jackson serializes → N+1
}

// GOOD: EntityGraph for explicit eager loading
@EntityGraph(attributePaths = {"customer"})
@Query("SELECT p FROM Payment p WHERE p.tenantId = :tenantId")
List<Payment> findAllWithCustomer(@Param("tenantId") UUID tenantId);

// GOOD: DTO projection — no entity overhead
@Query("""
    SELECT new com.example.dto.PaymentSummary(
        p.id, p.amount, p.currency, c.name, p.createdAt)
    FROM Payment p JOIN p.customer c
    WHERE p.tenantId = :tenantId
    ORDER BY p.createdAt DESC
    """)
List<PaymentSummary> findSummaries(@Param("tenantId") UUID tenantId, Pageable pageable);
```

```java
// Batch size — reduce N+1 for collections
@Entity
public class Payment {
    @OneToMany(mappedBy = "payment")
    @BatchSize(size = 20) // Load 20 collections per query instead of 1
    private List<LineItem> lineItems;
}

// Hibernate statistics — detect N+1 in tests
@Test
void findAll_shouldNotCauseNPlusOne() {
    var stats = entityManager.unwrap(Session.class)
        .getSessionFactory().getStatistics();
    stats.setStatisticsEnabled(true);
    stats.clear();

    paymentRepository.findAllWithCustomer(tenantId);

    assertThat(stats.getPrepareStatementCount())
        .isLessThanOrEqualTo(2); // 1 for payments + 1 for customers (JOIN)
}
```

## Prisma Patterns

```typescript
// BAD: Select all fields, include everything
const payments = await prisma.payment.findMany({
  include: { customer: true, lineItems: true },
});

// GOOD: Select specific fields, include only what's needed
const payments = await prisma.payment.findMany({
  where: { tenantId, status: 'PENDING' },
  select: {
    id: true,
    amount: true,
    currency: true,
    createdAt: true,
    customer: { select: { id: true, name: true } },
  },
  orderBy: { createdAt: 'desc' },
  take: 20,
});

// Transaction — atomic operations
const [payment, event] = await prisma.$transaction([
  prisma.payment.create({ data: paymentData }),
  prisma.outboxEvent.create({ data: eventData }),
]);

// Interactive transaction — with business logic
const result = await prisma.$transaction(async (tx) => {
  const existing = await tx.payment.findUnique({
    where: { tenantId_idempotencyKey: { tenantId, idempotencyKey } },
  });
  if (existing) throw new ConflictError('Duplicate');

  return tx.payment.create({ data: paymentData });
}, {
  timeout: 10_000, // 10s timeout (default is 5s)
  isolationLevel: 'Serializable', // When needed
});
```

## SQLAlchemy 2.0 Patterns

```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload

# BAD: Lazy loading in async context — raises MissingGreenlet error
async def get_payments(session: AsyncSession):
    result = await session.execute(select(Payment))
    payments = result.scalars().all()
    for p in payments:
        print(p.customer.name)  # ERROR: lazy load in async

# GOOD: Eager loading with selectinload
async def get_payments_with_customers(session: AsyncSession, tenant_id: UUID):
    stmt = (
        select(Payment)
        .options(selectinload(Payment.customer))  # 2 queries: payments + customers
        .where(Payment.tenant_id == tenant_id)
        .order_by(Payment.created_at.desc())
        .limit(20)
    )
    result = await session.execute(stmt)
    return result.scalars().all()

# GOOD: Projection — load only needed columns
async def get_payment_summaries(session: AsyncSession, tenant_id: UUID):
    stmt = (
        select(
            Payment.id,
            Payment.amount,
            Payment.currency,
            Customer.name.label("customer_name"),
        )
        .join(Customer)
        .where(Payment.tenant_id == tenant_id)
        .order_by(Payment.created_at.desc())
        .limit(20)
    )
    result = await session.execute(stmt)
    return result.all()  # Returns Row objects, not entities
```

```python
# Relationship loading strategies
class Payment(Base):
    __tablename__ = "payments"

    # selectinload: 2 queries (good for collections)
    # joinedload: 1 query with JOIN (good for single relations)
    # subqueryload: 2 queries with subquery (good for filtered collections)
    # raiseload: raises error if accessed (prevents accidental lazy load)

    customer: Mapped["Customer"] = relationship(lazy="raise")  # Explicit loading required
    line_items: Mapped[list["LineItem"]] = relationship(lazy="raise")
```

## Anti-Patterns

- **Lazy loading in API**: Entity serialization triggers N+1 queries per related object.
- **N+1 queries**: Loading a list then querying related data in a loop.
- **SELECT ***: ORM default loads all columns — use projections for list endpoints.
- `open-in-view` / `lazy loading` in web context — hides N+1, leaks transactions.
- Returning ORM entities from API — leaks internal schema, triggers lazy loads.
- `SaveChanges` in a loop — batch operations into single call.
- Ignoring query count in tests — add assertions for expected query count.

## Gotchas

- EF Core `AsNoTracking()` — use for read-only queries (30-50% faster).
- JPA `@Transactional(readOnly = true)` — enables read replica routing, not just optimization.
- Prisma `$transaction` default timeout is 5 seconds — increase for complex operations.
- SQLAlchemy `expire_on_commit=False` — required for async sessions to avoid lazy load errors.
- EF Core compiled queries: cannot use `Contains`, `Any`, or other LINQ methods that generate dynamic SQL.
- Hibernate second-level cache: invalidated on any write — not useful for write-heavy entities.
- Prisma `select` and `include` are mutually exclusive — use one or the other.

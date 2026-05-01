---
name: performance-debugging
description: 'Performance debugging: profiling tools per stack, bottleneck identification, N+1 queries, connection pools, GC pauses, Little''s Law.'
---
# Performance Debugging

## Profiling Tools per Stack

| Stack | CPU Profiler | Memory Profiler | Request Tracing |
|---|---|---|---|
| **Java** | JFR + JMC, async-profiler | JFR heap analysis, MAT | Micrometer + Tempo |
| **C#/.NET** | dotnet-trace, dotnet-counters | dotnet-dump, dotnet-gcdump | OpenTelemetry |
| **Node.js** | `--prof`, clinic.js, 0x | `--inspect` + Chrome DevTools | OpenTelemetry |
| **Python** | py-spy, cProfile, scalene | tracemalloc, memray | OpenTelemetry |
| **Browser** | Chrome DevTools Performance | Chrome DevTools Memory | Lighthouse |

## Bottleneck Identification Methodology

```
1. MEASURE — Don't guess. Get baseline numbers.
2. IDENTIFY — Find the slowest component (DB? Network? CPU? GC?).
3. PROFILE — Drill into the slow component.
4. FIX — Address the root cause.
5. VERIFY — Measure again. Compare with baseline.
```

```bash
# Java: Start JFR recording
jcmd <pid> JFR.start duration=60s filename=profile.jfr

# .NET: Collect trace
dotnet-trace collect --process-id <pid> --duration 00:00:60

# Node.js: CPU profile
node --prof app.js
node --prof-process isolate-*.log > profile.txt

# Python: Profile with py-spy
py-spy record -o profile.svg --pid <pid>
```

## Common Performance Issues

### N+1 Query Problem

```java
// BAD: N+1 — 1 query for payments + N queries for customers
@GetMapping("/payments")
public List<PaymentResponse> list() {
    List<Payment> payments = paymentRepository.findAll(); // 1 query
    return payments.stream()
        .map(p -> {
            Customer c = p.getCustomer(); // N queries (lazy load)
            return new PaymentResponse(p.getId(), c.getName(), p.getAmount());
        })
        .toList();
}

// GOOD: Single query with JOIN or EntityGraph
@EntityGraph(attributePaths = {"customer"})
@Query("SELECT p FROM Payment p WHERE p.tenantId = :tenantId")
List<Payment> findAllWithCustomer(@Param("tenantId") UUID tenantId);

// Or use projection (even better — no entity overhead)
@Query("""
    SELECT new com.example.PaymentSummary(p.id, c.name, p.amount)
    FROM Payment p JOIN p.customer c
    WHERE p.tenantId = :tenantId
    """)
List<PaymentSummary> findSummaries(@Param("tenantId") UUID tenantId);
```

```typescript
// Prisma N+1
// BAD: Fetching related data in a loop
const payments = await prisma.payment.findMany();
for (const p of payments) {
  const customer = await prisma.customer.findUnique({ where: { id: p.customerId } });
  // N additional queries
}

// GOOD: Include related data in single query
const payments = await prisma.payment.findMany({
  include: { customer: { select: { id: true, name: true } } },
});
```

### Connection Pool Exhaustion

```java
// Symptoms: requests hang, then timeout after 30s
// Check HikariCP metrics
// application.yml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20        # Default is 10
      minimum-idle: 5
      connection-timeout: 5000     # Fail fast, don't wait 30s
      leak-detection-threshold: 10000  # Log if connection held > 10s

// BAD: Long-running transaction holds connection
@Transactional
public void processAll() {
    List<Payment> payments = repository.findAll();
    for (Payment p : payments) {
        externalApi.call(p); // HTTP call inside transaction — holds connection
    }
}

// GOOD: Short transaction, release connection before external call
public void processAll() {
    List<UUID> ids = repository.findAllIds(); // Quick query, release connection
    for (UUID id : ids) {
        externalApi.call(id); // No transaction, no connection held
        repository.markProcessed(id); // Short transaction per item
    }
}
```

### GC Pauses

```bash
# Java: Enable GC logging
java -Xlog:gc*:file=gc.log:time,uptime,level,tags -jar app.jar

# Key metrics to watch:
# - GC pause time (should be < 200ms for P99)
# - GC frequency (too frequent = too much allocation)
# - Heap usage after GC (growing = memory leak)
```

```java
// BAD: Excessive object allocation in hot path
public List<PaymentResponse> list() {
    return payments.stream()
        .map(p -> new PaymentResponse(p)) // Creates N objects
        .sorted(Comparator.comparing(PaymentResponse::getCreatedAt)) // Sorts in memory
        .limit(20)
        .toList();
}

// GOOD: Push sorting and limiting to DB, minimize allocations
public List<PaymentResponse> list(int page, int size) {
    return paymentRepository.findTop(page, size) // DB does sort + limit
        .stream()
        .map(PaymentResponse::from)
        .toList();
}
```

## Little's Law for Capacity Reasoning

```
L = λ × W

L = average number of concurrent requests in system
λ = arrival rate (requests per second)
W = average response time (seconds)

Example:
  λ = 100 req/s, W = 0.2s → L = 20 concurrent requests
  Connection pool = 20 → just enough (no headroom)
  Connection pool = 10 → requests will queue → latency spikes

Rule of thumb: pool size = 2 × expected concurrent requests
```

## Browser Performance

```typescript
// BAD: Rendering 10,000 items in a list
function PaymentList({ payments }: { payments: Payment[] }) {
  return (
    <ul>
      {payments.map(p => <PaymentRow key={p.id} payment={p} />)}
    </ul>
  );
}

// GOOD: Virtualized list — only renders visible items
import { useVirtualizer } from '@tanstack/react-virtual';

function PaymentList({ payments }: { payments: Payment[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: payments.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div key={virtualRow.key} style={{
            position: 'absolute',
            top: 0,
            transform: `translateY(${virtualRow.start}px)`,
            height: `${virtualRow.size}px`,
          }}>
            <PaymentRow payment={payments[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Anti-Patterns

- **Premature optimization**: Profile first, optimize second. Don't guess the bottleneck.
- Adding caching without understanding why it's slow — cache hides the problem.
- `SELECT *` when you need 3 columns — wastes bandwidth and memory.
- Synchronous external calls inside database transactions.
- Ignoring P99 latency — average hides tail latency spikes.
- "It's fast on my machine" — test with production-like data volume.

## Gotchas

- JFR has near-zero overhead — safe to run in production.
- `dotnet-counters` shows real-time metrics without restart.
- Node.js `--inspect` opens a debugging port — never expose in production.
- py-spy can attach to running processes without restart.
- Chrome DevTools Performance tab: record, then look at "Bottom-Up" for hotspots.
- Connection pool metrics: monitor `active`, `idle`, `pending` — not just `max`.

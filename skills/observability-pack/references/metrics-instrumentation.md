---
name: metrics-instrumentation
description: 'Metric types (counter, histogram, gauge), RED/USE method, label cardinality discipline, Prometheus + OTel SDK examples per stack.'
---
# Metrics Instrumentation Patterns

## Choose the Right Metric Type

| Type | When | Example |
|---|---|---|
| **Counter** | Monotonic count of events | `http_requests_total`, `payments_created_total` |
| **Histogram** | Distribution of values (latency, size) | `http_request_duration_seconds`, `payment_amount_minor` |
| **Gauge** | Current value, can go up/down | `queue_depth`, `active_connections`, `cache_size_bytes` |
| **UpDownCounter** (OTel) | Net cumulative delta | `inflight_requests` |

❌ Never use Histogram when you only need counter (overhead). Never use Gauge for cumulative counts (loses data on restart).

## RED Method (Request-driven services)

For every endpoint/handler, emit:
- **R**ate — requests/sec → `http_requests_total{route, method, status}` (counter)
- **E**rrors — error rate → derived from above where `status >= 500`
- **D**uration — latency distribution → `http_request_duration_seconds{route, method}` (histogram)

## USE Method (Resources)

For every resource (CPU, memory, disk, queue, pool):
- **U**tilization, **S**aturation, **E**rrors.

Example: `db_connection_pool_usage_ratio`, `db_connection_pool_wait_seconds`, `db_connection_pool_errors_total`.

## Java — Micrometer

```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final MeterRegistry registry;
    private final Counter created;
    private final Timer chargeLatency;
    private final DistributionSummary amountMinor;

    @PostConstruct
    void init() {
        created       = Counter.builder("payments.created.total")
                          .description("Payments created").register(registry);
        chargeLatency = Timer.builder("payments.charge.duration.seconds")
                          .publishPercentileHistogram()
                          .serviceLevelObjectives(Duration.ofMillis(100), Duration.ofMillis(500))
                          .register(registry);
        amountMinor   = DistributionSummary.builder("payments.amount.minor")
                          .baseUnit("currency_minor").register(registry);
    }

    public Payment charge(ChargeRequest req) {
        return chargeLatency.record(() -> {
            Payment p = doCharge(req);
            created.increment();
            amountMinor.record(p.getAmountMinor());
            return p;
        });
    }
}
```

## .NET — System.Diagnostics.Metrics + OTel

```csharp
public sealed class PaymentMetrics
{
    private readonly Counter<long> _created;
    private readonly Histogram<double> _latency;

    public PaymentMetrics(IMeterFactory factory)
    {
        var meter = factory.Create("payments");
        _created = meter.CreateCounter<long>("payments.created.total");
        _latency = meter.CreateHistogram<double>("payments.charge.duration.seconds",
            unit: "s", description: "Charge latency");
    }

    public void RecordCreated(string currency) =>
        _created.Add(1, new KeyValuePair<string, object?>("currency", currency));

    public IDisposable MeasureCharge() => new Timer(_latency);
}
```

## Node.js — prom-client

```typescript
import { Counter, Histogram, register } from 'prom-client';

export const paymentsCreated = new Counter({
  name: 'payments_created_total',
  help: 'Payments created',
  labelNames: ['currency', 'status'] as const,  // bounded set!
});

export const chargeDuration = new Histogram({
  name: 'payment_charge_duration_seconds',
  help: 'Time to charge a payment',
  labelNames: ['provider'] as const,
  buckets: [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
});

const end = chargeDuration.startTimer({ provider: 'stripe' });
try {
  const p = await chargeProvider.charge(req);
  paymentsCreated.inc({ currency: p.currency, status: 'success' });
} finally { end(); }

// /metrics endpoint
app.get('/metrics', async (_req, res) => {
  res.type(register.contentType).send(await register.metrics());
});
```

## Python — OTel Metrics

```python
from opentelemetry import metrics
meter = metrics.get_meter(__name__)

payments_created = meter.create_counter("payments.created.total")
charge_latency   = meter.create_histogram("payments.charge.duration.seconds", unit="s")

start = time.perf_counter()
try:
    payment = await charge(req)
    payments_created.add(1, {"currency": payment.currency, "status": "success"})
finally:
    charge_latency.record(time.perf_counter() - start, {"provider": "stripe"})
```

## Go — OTel + promhttp

```go
meter := otel.Meter("payments")
created, _ := meter.Int64Counter("payments.created.total")
latency, _ := meter.Float64Histogram("payments.charge.duration.seconds")

start := time.Now()
defer func() {
    latency.Record(ctx, time.Since(start).Seconds(),
        metric.WithAttributes(attribute.String("provider", "stripe")))
}()
payment, err := charge(ctx, req)
if err == nil {
    created.Add(ctx, 1, metric.WithAttributes(
        attribute.String("currency", payment.Currency),
        attribute.String("status", "success")))
}
```

## Cardinality Discipline (Critical)

Every label combination = a separate time series. Watch out:

| Label | Cardinality | Verdict |
|---|---|---|
| `method` (GET/POST/...) | ~5 | ✅ |
| `status_code` | ~30 | ✅ |
| `route` (templated `/users/:id`) | ~100 | ✅ |
| `user_id` | millions | ❌ NEVER |
| `tenant_id` | thousands | ⚠️ only if business-required |
| `request_id`, `trace_id` | infinite | ❌ NEVER |
| `path` (raw URL with IDs) | infinite | ❌ NEVER — template it |

Rule of thumb: per metric, total series ≤ 10k. If you need user-level granularity, that's logs/traces, not metrics.

## Histogram Buckets — Pick for Your SLO

```typescript
// Default linear buckets are usually wrong. Pick around your SLO.
// SLO: p99 < 500ms → buckets clustered near 500ms
buckets: [0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]
```

For OTel: prefer `ExplicitBucketHistogramAggregation` or exponential histograms (`ExponentialBucketHistogramAggregation`) for adaptive resolution.

## Don't

- Reset gauges manually — use OTel `Asynchronous Gauge` (callback) or Micrometer `Gauge.builder(...).register(...)`.
- Emit a metric per business event (use logs/events table) — metrics are aggregates.
- Forget to set `unit` (`s`, `bytes`, `requests`) — units enable correct dashboard rendering.
- Mix counter and gauge semantics in one metric.

## Verification

```bash
# Cardinality audit
curl -s http://localhost:9100/metrics | awk -F'{' '/^[a-z]/{print $1}' | sort | uniq -c | sort -rn | head
# Promtool lints rules + dashboards-as-code
promtool check metrics  http://localhost:9100/metrics
promtool check rules    rules/*.yaml
```


---
name: otel-tracing
description: 'OpenTelemetry instrumentation per stack: SDK setup, auto-instrumentation, manual spans, propagation, semantic attributes, sampling.'
---
# OpenTelemetry Tracing Patterns

## Setup — SDK Skeleton (Universal Concepts)

1. Resource (`service.name`, `service.version`, `deployment.environment`)
2. TracerProvider with sampler (`parentbased_traceidratio`, `always_on` in dev)
3. Span processor (BatchSpanProcessor in prod)
4. Exporter (OTLP HTTP/gRPC → Collector)
5. Propagator (W3C TraceContext + Baggage)

## Auto-Instrumentation — Use First

```bash
# Java
java -javaagent:opentelemetry-javaagent.jar -jar app.jar

# .NET
dotnet add package OpenTelemetry.AutoInstrumentation
# then run with the OTel installer

# Node.js
node --require @opentelemetry/auto-instrumentations-node/register app.js

# Python
opentelemetry-instrument --traces_exporter otlp uvicorn app:app

# Go (no agent — use SDK + libraries)
import "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
```

Auto wires HTTP/gRPC servers + clients, DB drivers, message brokers, cache clients.

## Manual Span — When + How

Add manual spans for **business operations** (e.g., `payment.charge`, `inventory.reserve`), not low-level functions.

### Java
```java
@Autowired Tracer tracer;

Span span = tracer.spanBuilder("payment.charge")
    .setSpanKind(SpanKind.INTERNAL)
    .setAttribute("payment.tenant_id", tenantId.toString())
    .setAttribute("payment.amount_minor", amountMinor)
    .setAttribute("payment.currency", currency)
    .startSpan();
try (Scope s = span.makeCurrent()) {
    return processor.charge(request);
} catch (Exception e) {
    span.recordException(e);
    span.setStatus(StatusCode.ERROR, e.getMessage());
    throw e;
} finally {
    span.end();
}
```

### Node.js
```typescript
import { trace, SpanStatusCode } from '@opentelemetry/api';
const tracer = trace.getTracer('payments-api');

await tracer.startActiveSpan('payment.charge', async (span) => {
  span.setAttributes({ 'payment.tenant_id': tenantId, 'payment.currency': currency });
  try {
    return await processor.charge(req);
  } catch (e) {
    span.recordException(e as Error);
    span.setStatus({ code: SpanStatusCode.ERROR, message: (e as Error).message });
    throw e;
  } finally {
    span.end();
  }
});
```

### Python
```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("payment.charge") as span:
    span.set_attribute("payment.tenant_id", str(tenant_id))
    span.set_attribute("payment.currency", currency)
    try:
        return await processor.charge(req)
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        raise
```

### Go
```go
ctx, span := otel.Tracer("payments").Start(ctx, "payment.charge",
    trace.WithAttributes(
        attribute.String("payment.tenant_id", req.TenantID.String()),
        attribute.String("payment.currency", req.Currency),
    ))
defer span.End()

result, err := processor.Charge(ctx, req)
if err != nil {
    span.RecordError(err)
    span.SetStatus(codes.Error, err.Error())
    return result, err
}
```

## Attribute Naming — Follow Semantic Conventions

| Use this | Not this |
|---|---|
| `http.request.method` | `httpMethod`, `method` |
| `http.response.status_code` | `status`, `code` |
| `db.system`, `db.statement` | `database`, `query` |
| `messaging.system`, `messaging.destination.name` | `kafka.topic` |
| `error.type` | `exception_class` |

Custom domain attributes: prefix with your domain (`payment.tenant_id`, `order.line_count`). Never put PII or secrets in attributes — they're indexed and stored.

## Cardinality Limits

- ❌ `user.id` as attribute on every span → blows up trace storage cardinality.
- ✅ `user.id` only on entry-point span; downstream spans inherit via trace context.
- Bucket continuous values: `amount.bucket=10-100` not `amount=42.17`.

## Propagation Across Services

```typescript
// W3C TraceContext is default — works across HTTP and gRPC if both ends use OTel SDKs
// Manual injection for non-OTel transports (e.g., Kafka headers)
import { propagation, context } from '@opentelemetry/api';

propagation.inject(context.active(), kafkaHeaders, {
  set: (h, k, v) => { h[k] = v; },
});

// Receiver
const ctx = propagation.extract(context.active(), msg.headers, {
  get: (h, k) => h[k],
  keys: (h) => Object.keys(h),
});
context.with(ctx, () => process(msg));
```

## Sampling Strategy

```yaml
# Collector tail-sampling: keep all errors, all slow, 5% of normal
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - { name: errors,      type: status_code, status_code: { status_codes: [ERROR] } }
      - { name: slow,        type: latency,     latency:     { threshold_ms: 1000 } }
      - { name: probabilistic, type: probabilistic, probabilistic: { sampling_percentage: 5 } }
```

## Don't

- Wrap every function in `startSpan` — span explosion = noise + cost.
- Log inside spans without propagating `trace_id` — breaks log↔trace pivot.
- Use `BatchSpanProcessor` in serverless → switch to `SimpleSpanProcessor` (process exits before flush).
- Hard-code endpoint URLs — use `OTEL_EXPORTER_OTLP_ENDPOINT` env var.

## Verification

```bash
# Validate spans land in collector
otel-cli exec --service test --name "manual-test" --kind client -- echo ok
# Check trace context propagation end-to-end
curl -H "traceparent: 00-$TRACE_ID-$SPAN_ID-01" $URL && \
  jaeger-query --trace-id $TRACE_ID
```


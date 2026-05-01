---
name: production-debugging
description: 'Production debugging: structured log analysis, distributed tracing, correlation IDs, reproduction strategies, safe debugging practices.'
---
# Production Debugging

## Structured Log Analysis

```json
// BAD: Unstructured log — hard to search, no context
"Payment failed for user john"

// GOOD: Structured log with correlation ID and context
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "logger": "PaymentService",
  "message": "Payment creation failed",
  "correlationId": "req-abc-123",
  "tenantId": "tenant-456",
  "paymentId": "pay-789",
  "error": "InsufficientFundsException",
  "errorMessage": "Account ACC-001 has insufficient balance",
  "duration_ms": 245
}
```

```java
// Java: Structured logging with SLF4J + Logback/Logstash
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import net.logstash.logback.argument.StructuredArguments;
import static net.logstash.logback.argument.StructuredArguments.kv;

@Service
public class PaymentService {
    private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

    public Payment create(CreatePaymentRequest request) {
        log.info("Creating payment",
            kv("tenantId", request.tenantId()),
            kv("amount", request.amount()),
            kv("currency", request.currency()));

        try {
            Payment payment = doCreate(request);
            log.info("Payment created",
                kv("paymentId", payment.getId()),
                kv("status", payment.getStatus()));
            return payment;
        } catch (Exception e) {
            log.error("Payment creation failed",
                kv("tenantId", request.tenantId()),
                kv("error", e.getClass().getSimpleName()),
                e); // Stack trace as last argument
            throw e;
        }
    }
}
```

```python
# Python: structlog for structured logging
import structlog

logger = structlog.get_logger()

async def create_payment(request: CreatePaymentRequest) -> Payment:
    log = logger.bind(
        tenant_id=str(request.tenant_id),
        amount=str(request.amount),
        currency=request.currency,
    )
    log.info("creating_payment")

    try:
        payment = await do_create(request)
        log.info("payment_created", payment_id=str(payment.id), status=payment.status)
        return payment
    except Exception:
        log.exception("payment_creation_failed")
        raise
```

## Log Search Patterns

```bash
# Find all errors for a specific correlation ID
# Elasticsearch/Kibana query
correlationId:"req-abc-123" AND level:"ERROR"

# Find payment failures in last hour
level:"ERROR" AND logger:"PaymentService" AND @timestamp:[now-1h TO now]

# Find slow requests (> 1 second)
duration_ms:>1000 AND level:"INFO"

# Count errors by type in last 24h
# Kibana aggregation: terms on error field, date_histogram on @timestamp
```

## Distributed Tracing

```
Request flow with trace context:

Client → API Gateway → Payment Service → PSP Client → PSP API
  │         │              │                │
  │    trace-id: abc   trace-id: abc   trace-id: abc
  │    span-id: 001    span-id: 002    span-id: 003
  │                    parent: 001     parent: 002
```

```java
// Spring Boot: Auto-instrumented with Micrometer Tracing
// application.yml
management:
  tracing:
    sampling:
      probability: 1.0  # 100% in dev, 10% in prod
  otlp:
    tracing:
      endpoint: http://tempo:4318/v1/traces

// Manual span for important operations
import io.micrometer.tracing.Tracer;

@Service
public class PspClient {
    private final Tracer tracer;

    public PspResponse submit(PspRequest request) {
        var span = tracer.nextSpan().name("psp.submit").start();
        try (var scope = tracer.withSpan(span)) {
            span.tag("psp.request.amount", request.amount().toString());
            PspResponse response = doSubmit(request);
            span.tag("psp.response.status", response.status());
            return response;
        } catch (Exception e) {
            span.error(e);
            throw e;
        } finally {
            span.end();
        }
    }
}
```

```typescript
// Node.js: OpenTelemetry auto-instrumentation
// tracing.ts — import BEFORE any other module
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: 'http://tempo:4318/v1/traces' }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
```

## Reproduction Strategies

```markdown
### From Logs to Local Reproduction

1. **Extract the request** — Find the exact request payload from logs
   ```
   correlationId:"req-abc-123" AND message:"Creating payment"
   → tenantId: "tenant-456", amount: 100.00, currency: "VND"
   ```

2. **Extract the state** — What was the DB state when the error occurred?
   ```sql
   SELECT * FROM payments WHERE tenant_id = 'tenant-456'
     AND created_at < '2024-01-15T10:30:45Z'
     ORDER BY created_at DESC LIMIT 10;
   ```

3. **Write a reproduction test**
   ```java
   @Test
   void reproduce_bug_1234() {
       // Set up the exact state from production
       setupTestData(tenantId, existingPayments);

       // Replay the exact request
       var request = new CreatePaymentRequest(tenantId, ...);

       // Assert the bug occurs
       assertThatThrownBy(() -> service.create(request))
           .isInstanceOf(NullPointerException.class);
   }
   ```

4. **Fix and verify** — Fix passes the reproduction test
```

## Safe Production Debugging Rules

```markdown
## DO
✅ Read-only queries against read replicas
✅ Add temporary structured logging (with feature flag)
✅ Use distributed tracing to follow request flow
✅ Check metrics dashboards (Grafana, CloudWatch)
✅ Use profiling tools that attach without restart (JFR, py-spy)
✅ Query audit logs for state changes

## DON'T
❌ Run UPDATE/DELETE queries on production DB
❌ Add debug logging that includes PII or secrets
❌ Restart production services during investigation
❌ Use interactive debuggers attached to production processes
❌ Modify production config without change management
❌ Share production data in Slack/email (PII risk)
```

## Incident Response Checklist

```markdown
1. **Acknowledge** — "I'm looking at this" (in incident channel)
2. **Assess severity** — Users affected? Data loss? Revenue impact?
3. **Mitigate** — Can we reduce impact NOW? (rollback, feature flag, scale up)
4. **Investigate** — Follow 4-phase methodology (don't skip to fix)
5. **Fix** — Deploy fix with regression test
6. **Verify** — Confirm fix in production (metrics, logs)
7. **Postmortem** — Document: timeline, root cause, action items
```

## Anti-Patterns

- **Debugging by printf in production**: Use structured logging with levels, not `System.out.println`.
- Searching unstructured logs with regex — use structured logging + search tools.
- "Let me SSH into the production server" — use observability tools instead.
- Adding debug code without a plan to remove it.
- Investigating without a timeline — always establish "when did this start?"
- Sharing stack traces with customer data in public channels.

## Gotchas

- Correlation IDs must propagate across async boundaries (thread pools, message queues).
- Sampling rate in tracing: 100% in dev, 1-10% in production (cost vs visibility).
- Log retention: keep error logs longer than info logs (30 days vs 7 days).
- Time synchronization: NTP drift between services can make trace ordering wrong.
- Read replicas may have replication lag — queries may not show latest data.
- JFR continuous recording has < 1% overhead — safe for production.

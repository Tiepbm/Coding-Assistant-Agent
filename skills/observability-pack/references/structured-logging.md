---
name: structured-logging
description: 'JSON logging patterns per stack: levels, correlation IDs (trace_id), redaction of secrets/PII, sampling.'
---
# Structured Logging Patterns

## Universal Rules

- **JSON output in production** — never pretty-printed text logs in non-dev.
- **One log per logical event**, not one per intermediate step.
- Required fields: `timestamp`, `level`, `service`, `trace_id`, `span_id`, `message`, plus context (`user_id`, `tenant_id`, `request_id`).
- **Never log secrets, tokens, full PII, full request bodies, or credit card data**.
- Levels: `ERROR` (alertable bug), `WARN` (degraded but recoverable), `INFO` (state change), `DEBUG` (off in prod).

## Java — SLF4J + Logback JSON

```java
// BAD: string concatenation, secret leaked, no context
log.info("User " + email + " login with token " + token);

// GOOD: structured + MDC + redaction
import net.logstash.logback.argument.StructuredArguments;

MDC.put("trace_id", currentTraceId());
MDC.put("user_id", userId.toString());
log.info("user.login.success",
    StructuredArguments.kv("email_domain", email.split("@")[1]),
    StructuredArguments.kv("method", "password"));
```

```xml
<!-- logback-spring.xml -->
<appender name="json" class="ch.qos.logback.core.ConsoleAppender">
  <encoder class="net.logstash.logback.encoder.LogstashEncoder">
    <includeMdcKeyName>trace_id</includeMdcKeyName>
    <includeMdcKeyName>span_id</includeMdcKeyName>
    <includeMdcKeyName>tenant_id</includeMdcKeyName>
  </encoder>
</appender>
```

## .NET — Serilog

```csharp
Log.Logger = new LoggerConfiguration()
    .Enrich.FromLogContext()
    .Enrich.WithProperty("service", "payments-api")
    .Enrich.WithSpan()                             // OTel correlation
    .Destructure.ByTransforming<CreatePaymentRequest>(
        r => new { r.TenantId, r.Currency, AmountBucket = Bucketize(r.Amount) })
    .WriteTo.Console(new JsonFormatter())
    .CreateLogger();

using (LogContext.PushProperty("tenant_id", tenantId))
{
    _logger.LogInformation("payment.created {PaymentId} {Amount}", payment.Id, payment.Amount);
}
```

## Node.js — pino

```typescript
import pino from 'pino';

export const log = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  base: { service: 'payments-api', env: process.env.NODE_ENV },
  formatters: { level: (label) => ({ level: label }) },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: {
    paths: ['*.password', '*.token', '*.authorization', '*.cardNumber', 'req.headers.cookie'],
    remove: true,
  },
});

// Per-request child with correlation
app.use((req, _res, next) => {
  req.log = log.child({
    trace_id: req.headers['traceparent']?.split('-')[1],
    request_id: req.headers['x-request-id'] ?? crypto.randomUUID(),
  });
  next();
});

req.log.info({ payment_id: p.id }, 'payment.created');
```

## Python — structlog

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
)
log = structlog.get_logger().bind(service="payments-api")

# Per-request context (FastAPI middleware)
async def correlation_middleware(request, call_next):
    trace_id = request.headers.get("traceparent", "").split("-")[1] if "traceparent" in request.headers else None
    structlog.contextvars.bind_contextvars(trace_id=trace_id, request_id=str(uuid4()))
    try:
        return await call_next(request)
    finally:
        structlog.contextvars.clear_contextvars()

log.info("payment.created", payment_id=str(p.id), amount=str(p.amount))
```

## Go — slog (stdlib, Go 1.21+)

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,
    ReplaceAttr: redactSecrets,
}))
slog.SetDefault(logger)

ctx = logging.WithContext(ctx, slog.Default().With(
    "trace_id", traceIDFromContext(ctx),
    "tenant_id", req.TenantID,
))
slog.InfoContext(ctx, "payment.created", "payment_id", payment.ID)

func redactSecrets(_ []string, a slog.Attr) slog.Attr {
    switch a.Key {
    case "password", "token", "authorization", "card_number":
        return slog.String(a.Key, "[REDACTED]")
    }
    return a
}
```

## Redaction Checklist

| Field type | Action |
|---|---|
| Passwords, tokens, API keys | Drop entirely |
| Credit card numbers | Drop or last-4 only |
| Emails | Domain only or hashed |
| Full request body | Schema-driven allowlist, not blocklist |
| Stack traces with user data | Sanitize before logging |

## Log-Trace Correlation

Every log line in a request MUST carry `trace_id` so you can pivot from log → trace in Grafana/Datadog/Jaeger. Inject via OTel SDK auto-instrumentation or middleware that reads `traceparent` header (W3C Trace Context).

## Sampling for High-Volume Events

```typescript
// Don't log every cache hit; sample 1%
if (Math.random() < 0.01) log.debug({ key }, 'cache.hit');
```

For ERROR logs: never sample.

## Verification

- `jq` parses every line: `app | jq -e .` exits 0.
- No secrets: `app | grep -iE 'password|bearer [a-z0-9]{20,}|sk_[a-z]{4,}'` returns nothing.
- All logs in a request share same `trace_id`.


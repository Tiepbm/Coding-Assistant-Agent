# Example: Debug a NullPointerException in Production

This example demonstrates the 4-phase debugging methodology.

## Context

Production alert: `NullPointerException` in `PaymentService.process()`.
Affects ~5% of payment events. Started 2 days ago after deploy v2.3.1.

---

## Phase 1: INVESTIGATE — Gather Evidence

### Error Message + Stack Trace

```
java.lang.NullPointerException: Cannot invoke "Payment.getStatus()" because "payment" is null
    at com.example.PaymentService.process(PaymentService.java:42)
    at com.example.PaymentEventConsumer.handle(PaymentEventConsumer.java:28)
    at org.springframework.kafka.listener.KafkaMessageListenerContainer$ListenerConsumer.invokeListener(...)
```

### Evidence Checklist

```
✅ Error: NullPointerException at PaymentService.java:42
✅ Stack: PaymentEventConsumer → PaymentService.process() → payment.getStatus()
✅ When started: After deploy v2.3.1 (2 days ago)
✅ Frequency: ~5% of payment events (not all)
✅ Who affected: All tenants, random payments
✅ Recent changes: git log v2.3.0..v2.3.1
✅ Logs: Events processed within 10ms of payment creation
```

### Recent Changes

```bash
$ git log --oneline v2.3.0..v2.3.1
a1b2c3d Refactor: move event publishing to async
d4e5f6g Fix: update payment status mapping
h7i8j9k Chore: upgrade Spring Boot to 3.2.1
```

Key change: `a1b2c3d Refactor: move event publishing to async`

---

## Phase 2: ANALYZE — Narrow the Scope

### WHERE does the error occur?

```java
// PaymentService.java:42
public void process(PaymentEvent event) {
    Payment payment = paymentRepository.findById(event.paymentId())
        .orElse(null);  // Line 40: returns null if not found

    payment.getStatus(); // Line 42: NPE here — payment is null
}
```

### WHAT data triggers it?

```sql
-- Check: do the failing payment IDs exist in the database?
SELECT id, created_at FROM payments
WHERE id IN ('pay-abc', 'pay-def', 'pay-ghi')  -- IDs from error logs
ORDER BY created_at DESC;

-- Result: All exist, but created_at is AFTER the error timestamp
-- pay-abc created at 10:30:45.123, error at 10:30:45.075 (50ms BEFORE creation!)
```

### WHEN did it start?

```
v2.3.0: Event published synchronously inside @Transactional method
v2.3.1: Event published asynchronously via @Async (commit a1b2c3d)

Timeline:
  T+0ms:   @Transactional begins
  T+2ms:   Payment saved (not yet committed)
  T+3ms:   @Async publishes event (new thread, outside transaction)
  T+5ms:   Consumer receives event, queries DB
  T+5ms:   Payment NOT FOUND (transaction hasn't committed yet!)
  T+50ms:  Original transaction commits
```

---

## Phase 3: HYPOTHESIZE — One Hypothesis

```
Observation: ~5% of payment events fail with NPE at findById
Hypothesis: The @Async event publishing sends the event BEFORE the
  @Transactional method commits. The consumer reads the DB before
  the payment row is visible.

Test: Add timing logs to confirm the event arrives before commit.

Expected: Log shows event processed before transaction commit timestamp.
```

### Minimal Reproduction Test

```java
@Test
void reproduce_nullPayment_whenEventArrivesBeforeCommit() {
    // Simulate: event arrives before payment is committed
    UUID paymentId = UUID.randomUUID();
    // Don't save payment — simulates pre-commit state

    PaymentEvent event = new PaymentEvent(paymentId, "payment.created");

    assertThatThrownBy(() -> paymentService.process(event))
        .isInstanceOf(NullPointerException.class);
    // ✅ Hypothesis confirmed: NPE when payment doesn't exist yet
}
```

---

## Phase 4: IMPLEMENT — Fix + Regression Test

### Root Cause

`@Async` event publishing runs in a separate thread, outside the `@Transactional` boundary.
The event is published before the transaction commits, so the consumer may read the DB
before the payment row is visible.

### Fix: Transactional Outbox Pattern

```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final PaymentRepository payments;
    private final OutboxRepository outbox;

    @Transactional
    public Payment create(CreatePaymentRequest request) {
        Payment payment = Payment.create(request);
        payments.save(payment);

        // Outbox event in SAME transaction — published AFTER commit by relay
        outbox.save(OutboxEvent.of(
            payment.getId(), "payment.created",
            PaymentCreatedEvent.from(payment)));

        return payment;
    }
}
```

### Regression Test

```java
@Test
void create_publishesEventViaOutbox_notDirectly() {
    var request = validRequest();

    paymentService.create(request);

    // Outbox has the event (relay will publish after commit)
    assertThat(outboxRepository.findAll()).hasSize(1);
    assertThat(outboxRepository.findAll().get(0).getEventType())
        .isEqualTo("payment.created");
}

@Test
void process_withExistingPayment_succeeds() {
    var payment = paymentRepository.save(Payment.create(validRequest()));
    var event = new PaymentEvent(payment.getId(), "payment.created");

    assertThatCode(() -> paymentService.process(event))
        .doesNotThrowAnyException();
}

@Test
void process_withMissingPayment_throwsNotFound() {
    var event = new PaymentEvent(UUID.randomUUID(), "payment.created");

    assertThatThrownBy(() -> paymentService.process(event))
        .isInstanceOf(NotFoundException.class); // Not NPE anymore
}
```

### Verification

```
✅ Regression tests pass
✅ Load test: 0% NPE under concurrent traffic (was 5%)
✅ Outbox relay publishes events only after transaction commit
✅ Deployed to staging, monitored for 24h — no NPE
✅ Deployed to production — error rate dropped to 0%
```

---

## Postmortem Summary

| Item | Detail |
|---|---|
| **Root cause** | `@Async` event publishing outside `@Transactional` boundary |
| **Impact** | ~5% of payment events failed for 2 days |
| **Fix** | Transactional outbox pattern |
| **Prevention** | Added integration test for event timing |
| **Action items** | 1. Audit other `@Async` usages. 2. Add outbox to event publishing guide. |

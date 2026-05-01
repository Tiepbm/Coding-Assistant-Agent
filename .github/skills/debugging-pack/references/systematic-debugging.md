---
name: systematic-debugging
description: '4-phase debugging methodology: investigate, analyze, hypothesize, implement. Evidence gathering, root cause analysis, worked examples.'
---
# Systematic Debugging

## 4-Phase Methodology

```
Phase 1: INVESTIGATE — Gather evidence (don't guess)
Phase 2: ANALYZE    — Narrow the scope
Phase 3: HYPOTHESIZE — Form ONE testable hypothesis
Phase 4: IMPLEMENT  — Fix + regression test
```

## Phase 1: Investigate — Evidence Gathering Checklist

```markdown
□ Error message (exact text, not paraphrased)
□ Stack trace (full, not truncated)
□ When did it start? (deploy, config change, traffic spike?)
□ How often? (every time, intermittent, under load?)
□ Who is affected? (all users, one tenant, one region?)
□ What changed recently? (git log --since="2 days ago" --oneline)
□ Relevant logs (structured, with correlation ID)
□ Metrics (CPU, memory, latency, error rate)
□ Can it be reproduced locally?
```

```bash
# Quick evidence gathering commands
# Recent deploys
git log --oneline --since="3 days ago"

# Error frequency in logs
grep -c "NullPointerException" /var/log/app/error.log

# Recent config changes
git diff HEAD~5 -- '*.yml' '*.properties' '*.env'
```

## Phase 2: Analyze — Narrow the Scope

```
Ask these questions in order:
1. WHERE in the code does the error occur? (stack trace → file:line)
2. WHAT data triggers it? (specific input, tenant, time?)
3. WHEN did it start? (correlate with deploys/changes)
4. WHY does the code path reach this state? (trace backwards)
```

```java
// BAD: Guessing and patching
if (payment == null) {
    return null; // "Fix" — but WHY is payment null?
}

// GOOD: Trace the root cause
// Stack trace says: PaymentService.java:42 — payment.getStatus()
// Question: Why is payment null at line 42?
// Trace: payment = repository.findById(id) → returns null
// Question: Why does findById return null?
// Check: Is the ID correct? Is the query correct? Is the data there?
```

## Phase 3: Hypothesize — One Hypothesis at a Time

```markdown
## Hypothesis Template
**Observation:** Payment creation fails with NullPointerException at PaymentService:42
**Hypothesis:** The payment ID from the event is stale — the payment was created in a
  transaction that hasn't committed yet when the event consumer processes it.
**Test:** Add logging before the findById call to capture the ID and timestamp.
  Check if the event arrives before the transaction commits.
**Expected result:** Log shows event processed within milliseconds of creation,
  before transaction commit.
```

```java
// Minimal test for hypothesis — don't change production code yet
@Test
void reproduce_nullPayment_whenEventArrivesBeforeCommit() {
    // Simulate: publish event before transaction commits
    var paymentId = UUID.randomUUID();
    // Don't save payment yet

    assertThatThrownBy(() -> consumer.handle(eventWith(paymentId)))
        .isInstanceOf(NullPointerException.class);
    // Hypothesis confirmed: event arrives before data is committed
}
```

## Phase 4: Implement — Fix + Regression Test

```java
// Fix: Use outbox pattern — event published only after commit
@Transactional
public Payment create(CreatePaymentRequest request) {
    Payment payment = Payment.create(request);
    payments.save(payment);

    // BAD: Publish event inside transaction (consumer may read before commit)
    // eventPublisher.publish(new PaymentCreatedEvent(payment.getId()));

    // GOOD: Outbox — event published by relay AFTER transaction commits
    outbox.save(OutboxEvent.of(payment.getId(), "payment.created", payload));
    return payment;
}

// Regression test
@Test
void create_publishesEventAfterCommit_notBefore() {
    var request = validRequest();

    paymentService.create(request);

    // Verify outbox has the event (will be relayed after commit)
    assertThat(outboxRepository.findAll()).hasSize(1);
    // Verify no direct event was published
    verifyNoInteractions(eventPublisher);
}
```

## Red Flags — When to Escalate

```markdown
🚩 3+ fixes failed → Stop. Question the architecture, not the code.
🚩 "Works on my machine" → Environment difference. Check: OS, JDK version, config, data.
🚩 Intermittent failure → Race condition or resource contention. Add logging, don't guess.
🚩 Fix breaks something else → Missing test coverage. Add characterization tests first.
🚩 Can't reproduce → Need more data. Add structured logging, correlation IDs, metrics.
```

## Worked Example: NullPointerException in Production

```markdown
### Evidence
- Error: `NullPointerException at PaymentService.java:42`
- Stack: `PaymentEventConsumer.handle() → PaymentService.process() → payment.getStatus()`
- Frequency: ~5% of payment events
- Started: After deploy v2.3.1 (2 days ago)
- Logs: Events processed within 10ms of payment creation

### Analysis
- Line 42: `payment.getStatus()` — payment is null
- payment comes from `repository.findById(event.paymentId())`
- findById returns null → payment not in DB when consumer reads it
- Git diff v2.3.0..v2.3.1: Changed from synchronous to async event publishing

### Hypothesis
Async event publishing sends the event BEFORE the transaction commits.
Consumer reads the DB before the payment row is visible.

### Test
Added timing logs: event published at T+2ms, transaction commits at T+50ms.
Confirmed: 48ms window where event is published but data isn't committed.

### Fix
Replaced direct event publishing with transactional outbox pattern.
Outbox relay publishes events AFTER transaction commit.

### Regression Test
Integration test verifying event is only published after commit.
Load test confirming 0% NullPointerException under concurrent traffic.
```

## Debugging Decision Tree

```
Error reported
  ├── Can reproduce locally?
  │   ├── YES → Set breakpoint, step through
  │   └── NO → Add structured logging, deploy, wait for recurrence
  │
  ├── Stack trace available?
  │   ├── YES → Start at the throw site, trace backwards
  │   └── NO → Check logs, add exception handler with logging
  │
  ├── Intermittent?
  │   ├── YES → Suspect: race condition, resource exhaustion, external dependency
  │   └── NO → Suspect: logic error, bad data, config issue
  │
  └── Started after deploy?
      ├── YES → git diff between versions, focus on changed files
      └── NO → Check: data change, traffic pattern, external service change
```

## Anti-Patterns

- **Guess-and-patch**: Changing code without understanding root cause.
- **Shotgun debugging**: Changing multiple things at once — can't tell what fixed it.
- Adding `try/catch` to suppress the error instead of fixing it.
- "It works now" without understanding why — the bug will return.
- Debugging in production with write operations (UPDATE, DELETE).
- Ignoring intermittent failures — they're usually race conditions.

## Gotchas

- NullPointerException in Java 17+ shows which expression was null — read the full message.
- `async/await` stack traces in Node.js may be incomplete — use `--async-stack-traces`.
- Python `traceback` module gives more detail than the default exception print.
- .NET `InnerException` often contains the real error — don't stop at the outer exception.
- Docker container logs may be truncated — check `docker logs --tail 1000`.
- Time zones in logs: always use UTC, convert when displaying.

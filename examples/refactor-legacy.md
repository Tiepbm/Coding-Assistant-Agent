# Example: Refactor a Legacy God-Service Safely

Stack: Spring Boot. Pattern applies to any.

**Goal:** Extract `PaymentService.processOrder()` (450 lines, mixes pricing + tax + fraud + notifications) into focused collaborators **without changing behavior**.

## 1. Freeze the Behavior — Characterization Tests First

Before touching code, capture *what it currently does*. Don't chase "what it should do" — that's a separate task.

```java
@SpringBootTest
class PaymentServiceCharacterizationTest {
    @Autowired PaymentService svc;

    // For each known input scenario seen in production logs / DB, snapshot output.
    @ParameterizedTest
    @MethodSource("productionScenarios")
    void processOrder_matchesGoldenOutput(Order input, OrderResult goldenOutput) {
        OrderResult actual = svc.processOrder(input);
        assertThat(actual).usingRecursiveComparison()
            .ignoringFields("processedAt", "traceId")
            .isEqualTo(goldenOutput);
    }
}
```

Generate `goldenOutput` by capturing real outputs once, committing as JSON fixtures. Now any behavior drift fails CI.

## 2. Identify Seams (where to inject collaborators)

Read the 450-line method and tag each block:

```
L 12-78   pricing computation        → PricingCalculator
L 80-130  tax lookup + apply         → TaxService (already exists, used inline)
L 132-220 fraud rules                → FraudEvaluator
L 222-310 persistence + outbox       → keep in PaymentService
L 312-450 notifications (email/sms)  → NotificationDispatcher
```

## 3. Extract One Seam at a Time (Strangler)

Round 1 — extract `PricingCalculator`:

```java
// BEFORE: inline in PaymentService.processOrder
BigDecimal subtotal = order.getLines().stream().map(/* 50 lines */).reduce(...);

// STEP A — extract method (refactor IDE), tests still green
private BigDecimal computeSubtotal(Order order) { /* moved code */ }

// STEP B — extract class with same signature, inject
@Component
public class PricingCalculator {
    public BigDecimal subtotal(Order order) { /* moved code */ }
}

@Service
public class PaymentService {
    private final PricingCalculator pricing;  // injected
    // ...
    BigDecimal subtotal = pricing.subtotal(order);
}
```

Run characterization tests after **each** extraction. If red → revert that step only, not the whole refactor.

## 4. Add Unit Tests at the New Boundary

Now that `PricingCalculator` is isolated, write *real* unit tests for it (no Spring context):

```java
class PricingCalculatorTest {
    PricingCalculator calc = new PricingCalculator();

    @Test
    void subtotal_sumsLineAmounts() {
        Order o = orderWithLines(line(10, 2), line(5, 3));
        assertThat(calc.subtotal(o)).isEqualByComparingTo("35.00");
    }

    @Test
    void subtotal_appliesLineDiscount() { /* ... */ }
}
```

Repeat steps 3–4 for `FraudEvaluator`, `NotificationDispatcher`.

## 5. Verify + Remove Scaffolding

After all extractions:
- All characterization tests still green.
- New unit tests at each collaborator boundary.
- `PaymentService.processOrder()` ~80 lines of orchestration, no business rules inline.
- Run mutation testing on collaborators (`pitest`) — kill ratio ≥ 70%.

```bash
./mvnw verify -Pjacoco
./mvnw org.pitest:pitest-maven:mutationCoverage
```

## 6. Don't

- Refactor + add features in same PR. Behavior change must be a separate, isolated PR.
- Delete characterization tests after refactor. They're regression armor.
- Extract more than one seam per PR (review fatigue → bugs slip through).
- Trust IDE refactoring blindly for cross-file moves — re-run tests after every step.

## Skills Used

- `quality-pack/refactoring-patterns` — freeze → seam → move → verify → remove sequence.
- `testing-pack/integration-testing` — characterization tests with snapshots.
- `testing-pack/unit-testing` — new tests at extracted boundaries.
- `quality-pack/code-review-patterns` — small-PR discipline.


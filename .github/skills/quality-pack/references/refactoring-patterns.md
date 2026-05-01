---
name: refactoring-patterns
description: 'Safe refactoring: freeze-seam-move-verify-remove sequence, extract patterns, characterization tests, anti-patterns.'
---
# Refactoring Patterns

## Safe Refactoring Sequence

```
1. FREEZE  — All existing tests pass (green baseline). No new features.
2. SEAM    — Introduce abstraction at the change point (interface, function boundary).
3. MOVE    — Refactor behind the seam. Old tests still pass.
4. VERIFY  — Run full test suite. Check coverage didn't drop.
5. REMOVE  — Delete dead code, old implementation. Tests still pass.
```

## Extract Function

```java
// BEFORE: Long method with mixed concerns
public PaymentResponse processPayment(PaymentRequest request) {
    // Validation (20 lines)
    if (request.getAmount() == null || request.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
        throw new ValidationException("Amount must be positive");
    }
    if (request.getCurrency() == null || request.getCurrency().length() != 3) {
        throw new ValidationException("Currency must be 3 characters");
    }
    // ... more validation

    // Business logic (30 lines)
    BigDecimal fee = request.getAmount().multiply(FEE_RATE);
    BigDecimal total = request.getAmount().add(fee);
    // ... more logic

    // Persistence (10 lines)
    Payment payment = new Payment(request, total, fee);
    paymentRepository.save(payment);
    return PaymentResponse.from(payment);
}

// AFTER: Extracted functions with clear responsibilities
public PaymentResponse processPayment(PaymentRequest request) {
    validate(request);
    BigDecimal fee = calculateFee(request.getAmount());
    BigDecimal total = request.getAmount().add(fee);
    Payment payment = createAndSave(request, total, fee);
    return PaymentResponse.from(payment);
}

private void validate(PaymentRequest request) {
    if (request.getAmount() == null || request.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
        throw new ValidationException("Amount must be positive");
    }
    if (request.getCurrency() == null || request.getCurrency().length() != 3) {
        throw new ValidationException("Currency must be 3 characters");
    }
}

private BigDecimal calculateFee(BigDecimal amount) {
    return amount.multiply(FEE_RATE).setScale(2, RoundingMode.HALF_UP);
}

private Payment createAndSave(PaymentRequest request, BigDecimal total, BigDecimal fee) {
    Payment payment = new Payment(request, total, fee);
    return paymentRepository.save(payment);
}
```

## Extract Class

```typescript
// BEFORE: God class with too many responsibilities
class PaymentService {
  async create(request: CreatePaymentRequest) { /* ... */ }
  async capture(id: string) { /* ... */ }
  async refund(id: string, amount: number) { /* ... */ }
  async calculateFee(amount: number) { /* ... */ }
  async applyDiscount(items: Item[]) { /* ... */ }
  async sendNotification(paymentId: string) { /* ... */ }
  async generateReport(tenantId: string) { /* ... */ }
  async exportToCsv(payments: Payment[]) { /* ... */ }
}

// AFTER: Split by responsibility
class PaymentService {
  constructor(
    private readonly pricing: PricingService,
    private readonly notifier: PaymentNotifier,
  ) {}

  async create(request: CreatePaymentRequest) { /* ... */ }
  async capture(id: string) { /* ... */ }
  async refund(id: string, amount: number) { /* ... */ }
}

class PricingService {
  calculateFee(amount: number): number { /* ... */ }
  applyDiscount(items: Item[]): number { /* ... */ }
}

class PaymentNotifier {
  async sendNotification(paymentId: string) { /* ... */ }
}

class PaymentReporter {
  async generateReport(tenantId: string) { /* ... */ }
  async exportToCsv(payments: Payment[]) { /* ... */ }
}
```

## Introduce Interface (Seam)

```csharp
// BEFORE: Direct dependency on concrete class
public class PaymentService
{
    private readonly PspClient _pspClient; // Concrete — hard to test, hard to swap

    public async Task<Payment> CaptureAsync(Guid paymentId)
    {
        var payment = await _repo.FindByIdAsync(paymentId);
        var result = await _pspClient.ChargeAsync(payment); // Tightly coupled
        payment.Capture(result.Reference);
        return payment;
    }
}

// AFTER: Interface at the seam — testable, swappable
public interface IPspClient
{
    Task<PspResponse> ChargeAsync(Payment payment);
}

public class PaymentService
{
    private readonly IPspClient _pspClient; // Interface — can mock in tests

    public async Task<Payment> CaptureAsync(Guid paymentId)
    {
        var payment = await _repo.FindByIdAsync(paymentId);
        var result = await _pspClient.ChargeAsync(payment);
        payment.Capture(result.Reference);
        return payment;
    }
}

// Test with mock
[Fact]
public async Task Capture_CallsPspAndUpdatesStatus()
{
    var mockPsp = new Mock<IPspClient>();
    mockPsp.Setup(p => p.ChargeAsync(It.IsAny<Payment>()))
        .ReturnsAsync(new PspResponse("PSP-123", "captured"));

    var service = new PaymentService(mockPsp.Object, _repo);
    var result = await service.CaptureAsync(paymentId);

    result.Status.Should().Be("CAPTURED");
}
```

## Characterization Tests (Before Refactoring Legacy Code)

```python
# When refactoring code without tests, write characterization tests first.
# These tests document CURRENT behavior (even if it's wrong).

def test_characterize_fee_calculation():
    """Document current fee calculation behavior before refactoring."""
    service = LegacyPaymentService()

    # Test with known inputs, record actual outputs
    assert service.calculate_fee(Decimal("100.00")) == Decimal("2.50")
    assert service.calculate_fee(Decimal("0.01")) == Decimal("0.00")  # Rounds to zero
    assert service.calculate_fee(Decimal("999.99")) == Decimal("25.00")

    # Edge cases — document even if behavior seems wrong
    assert service.calculate_fee(Decimal("0")) == Decimal("0.00")
    assert service.calculate_fee(Decimal("-100")) == Decimal("-2.50")  # Bug? Document it.

# After characterization tests pass, refactor with confidence.
# If behavior should change, update the test FIRST (TDD).
```

## Strangler Fig Pattern (Large Refactoring)

```typescript
// Replace a legacy module incrementally, not all at once.

// Step 1: Introduce a facade that delegates to legacy
class PaymentFacade {
  constructor(
    private readonly legacy: LegacyPaymentService,
    private readonly modern: ModernPaymentService,
    private readonly featureFlags: FeatureFlags,
  ) {}

  async create(request: CreatePaymentRequest): Promise<Payment> {
    if (this.featureFlags.isEnabled('modern-payment-create')) {
      return this.modern.create(request);
    }
    return this.legacy.create(request);
  }

  async capture(id: string): Promise<Payment> {
    // Still using legacy — migrate later
    return this.legacy.capture(id);
  }
}

// Step 2: Migrate one method at a time behind feature flags
// Step 3: When all methods migrated, remove legacy + facade
```

## Anti-Patterns

- **Rewriting without tests**: No safety net — you'll introduce bugs.
- **Mixing behavior change + cleanup**: One commit changes logic, another cleans up. Never both.
- "Big bang" refactoring: Rewriting entire module at once instead of incremental changes.
- Refactoring code you don't understand — write characterization tests first.
- Refactoring without a clear goal — "make it cleaner" is not specific enough.
- Leaving dead code "just in case" — delete it, git has history.

## Gotchas

- Refactoring should not change behavior — if tests break, you changed behavior.
- IDE refactoring tools (rename, extract, move) are safer than manual edits.
- `git stash` before refactoring — easy to abandon if it goes wrong.
- Measure before and after: test count, coverage, cyclomatic complexity.
- Small PRs: one refactoring per PR, not five refactorings bundled together.
- Feature flags for large refactorings — deploy incrementally, rollback instantly.

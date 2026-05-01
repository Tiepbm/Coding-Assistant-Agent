---
name: tdd-workflow
description: 'TDD red-green-refactor cycle: concrete examples, when to TDD, test-first for bug fixes, refactoring under coverage.'
---
# TDD Workflow

## Red-Green-Refactor Cycle

```
┌─────────┐     ┌─────────┐     ┌──────────┐
│  RED     │────▶│  GREEN  │────▶│ REFACTOR │
│ Write a  │     │ Minimal │     │ Improve  │
│ failing  │     │ code to │     │ while    │
│ test     │     │ pass    │     │ green    │
└─────────┘     └─────────┘     └──────────┘
     ▲                                │
     └────────────────────────────────┘
```

### Step 1: RED — Write a Failing Test

```java
// Start with the simplest case
@Test
void calculate_withNoItems_returnsZero() {
    var calculator = new DiscountCalculator();

    BigDecimal result = calculator.calculate(List.of());

    assertThat(result).isEqualByComparingTo("0.00");
}
// Run → FAILS (DiscountCalculator doesn't exist yet) ✅
```

### Step 2: GREEN — Minimal Code to Pass

```java
// Write ONLY enough code to make the test pass
public class DiscountCalculator {
    public BigDecimal calculate(List<OrderItem> items) {
        return BigDecimal.ZERO;
    }
}
// Run → PASSES ✅
```

### Step 3: Add Next Test (RED again)

```java
@Test
void calculate_withSingleItem_returnsNoDiscount() {
    var calculator = new DiscountCalculator();
    var items = List.of(new OrderItem("SKU-1", new BigDecimal("100.00"), 1));

    BigDecimal result = calculator.calculate(items);

    assertThat(result).isEqualByComparingTo("0.00"); // No discount for 1 item
}

@Test
void calculate_withThreeOrMoreItems_returns10Percent() {
    var calculator = new DiscountCalculator();
    var items = List.of(
        new OrderItem("SKU-1", new BigDecimal("100.00"), 1),
        new OrderItem("SKU-2", new BigDecimal("200.00"), 1),
        new OrderItem("SKU-3", new BigDecimal("50.00"), 1)
    );

    BigDecimal result = calculator.calculate(items);

    assertThat(result).isEqualByComparingTo("35.00"); // 10% of 350
}
// Run → FAILS ✅
```

### Step 4: GREEN — Implement Logic

```java
public class DiscountCalculator {
    private static final int BULK_THRESHOLD = 3;
    private static final BigDecimal BULK_RATE = new BigDecimal("0.10");

    public BigDecimal calculate(List<OrderItem> items) {
        if (items.size() < BULK_THRESHOLD) {
            return BigDecimal.ZERO;
        }

        BigDecimal subtotal = items.stream()
            .map(item -> item.price().multiply(BigDecimal.valueOf(item.quantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        return subtotal.multiply(BULK_RATE)
            .setScale(2, RoundingMode.HALF_UP);
    }
}
// Run → ALL PASS ✅
```

### Step 5: REFACTOR — Improve While Green

```java
// Extract subtotal calculation, add edge case tests
public class DiscountCalculator {
    private static final int BULK_THRESHOLD = 3;
    private static final BigDecimal BULK_RATE = new BigDecimal("0.10");

    public BigDecimal calculate(List<OrderItem> items) {
        if (items.size() < BULK_THRESHOLD) {
            return BigDecimal.ZERO;
        }
        return subtotal(items).multiply(BULK_RATE)
            .setScale(2, RoundingMode.HALF_UP);
    }

    private BigDecimal subtotal(List<OrderItem> items) {
        return items.stream()
            .map(OrderItem::lineTotal)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}

// Add edge case
@Test
void calculate_withExactlyThreeItems_appliesDiscount() {
    // Boundary test — exactly at threshold
    var items = List.of(
        new OrderItem("A", new BigDecimal("10.00"), 1),
        new OrderItem("B", new BigDecimal("20.00"), 1),
        new OrderItem("C", new BigDecimal("30.00"), 1)
    );

    assertThat(calculator.calculate(items)).isEqualByComparingTo("6.00");
}
// Run → ALL PASS ✅
```

## When to TDD

| TDD (test-first) | Test-after (acceptable) |
|---|---|
| Business logic with clear rules | Exploratory prototypes |
| Bug fixes (reproduce first) | UI layout/styling |
| Algorithms, calculations | Config file changes |
| State machines, workflows | One-off scripts |
| Validation rules | Spike/proof of concept |
| API endpoint behavior | |

## Test-First for Bug Fixes

```typescript
// Step 1: Write a test that reproduces the bug
describe('PaymentService', () => {
  it('handles decimal precision correctly (bug #1234)', async () => {
    // This test MUST fail before the fix
    const result = await service.create({
      amount: 19.99,
      currency: 'VND',
      // ... other fields
    });

    // Bug: amount was stored as 19.98 due to floating-point
    expect(result.amount).toBe('19.99');
  });
});
// Run → FAILS (reproduces the bug) ✅

// Step 2: Fix the code
// Changed: store amount as string/Decimal, not float

// Step 3: Run → PASSES ✅
// The test now serves as a regression guard
```

```python
# Python example: bug fix TDD
def test_discount_rounds_correctly_bug_5678():
    """Bug #5678: discount of 33.33% on 100.00 returned 33.32 instead of 33.33."""
    calculator = DiscountCalculator()
    items = [OrderItem(price=Decimal("100.00"), quantity=1)]

    result = calculator.calculate(items, discount_rate=Decimal("0.3333"))

    assert result == Decimal("33.33")  # HALF_UP rounding
# Run → FAILS before fix ✅
```

## Refactoring Under Test Coverage

```
Safe refactoring sequence:
1. FREEZE — ensure all existing tests pass (green baseline)
2. CHARACTERIZE — add tests for any untested behavior you'll touch
3. SEAM — introduce an interface/abstraction at the change point
4. MOVE — refactor behind the seam
5. VERIFY — all tests still pass
6. REMOVE — delete dead code, old implementation
```

```java
// Example: Extract interface before replacing implementation
// Step 1: Characterization test
@Test
void existingBehavior_calculatesCorrectly() {
    // Document current behavior before refactoring
    var result = legacyCalculator.compute(input);
    assertThat(result).isEqualTo(expectedOutput);
}

// Step 2: Introduce seam (interface)
public interface PriceCalculator {
    BigDecimal compute(PriceInput input);
}

// Step 3: New implementation behind interface
public class NewPriceCalculator implements PriceCalculator {
    @Override
    public BigDecimal compute(PriceInput input) {
        // Cleaner implementation
    }
}

// Step 4: Verify — same tests pass with new implementation
// Step 5: Remove LegacyPriceCalculator
```

## TDD in Different Languages

```csharp
// C# xUnit TDD
public class DiscountCalculatorTests
{
    [Fact]
    public void Calculate_EmptyCart_ReturnsZero()
    {
        var calc = new DiscountCalculator();
        var result = calc.Calculate(Array.Empty<OrderItem>());
        result.Should().Be(0m);
    }

    [Theory]
    [InlineData(2, 0)]      // Below threshold
    [InlineData(3, 10)]     // At threshold → 10% discount
    [InlineData(5, 10)]     // Above threshold → still 10%
    public void Calculate_ByItemCount_AppliesCorrectRate(int count, decimal expectedRate)
    {
        var items = Enumerable.Range(0, count)
            .Select(_ => new OrderItem("SKU", 100m, 1))
            .ToArray();

        var result = new DiscountCalculator().Calculate(items);

        result.Should().Be(count * 100m * expectedRate / 100m);
    }
}
```

```python
# pytest parametrize for TDD
import pytest
from decimal import Decimal

@pytest.mark.parametrize("item_count,expected_discount", [
    (0, Decimal("0.00")),
    (2, Decimal("0.00")),
    (3, Decimal("30.00")),   # 10% of 300
    (5, Decimal("50.00")),   # 10% of 500
])
def test_calculate_discount_by_item_count(item_count, expected_discount):
    items = [OrderItem(price=Decimal("100.00"), quantity=1) for _ in range(item_count)]
    calculator = DiscountCalculator()

    result = calculator.calculate(items)

    assert result == expected_discount
```

## Anti-Patterns

- **Writing tests after code**: You lose the design feedback that TDD provides.
- **Testing mock behavior**: `verify(mock).method()` without asserting the actual result.
- Skipping the RED step — if the test passes immediately, it's not testing anything new.
- Giant leaps: writing 5 tests at once then implementing — take small steps.
- Refactoring while RED — only refactor when all tests are green.
- Testing private methods directly — test through the public API.
- Gold-plating: adding features not required by any test.

## Gotchas

- TDD doesn't mean 100% coverage — it means every behavior has a test.
- The first test is the hardest — start with the simplest possible case (empty input, zero, null).
- If you can't write a test, the requirement is unclear — clarify before coding.
- Parameterized tests (`@ParameterizedTest`, `Theory`, `pytest.mark.parametrize`) reduce duplication.
- TDD works best for logic-heavy code — don't force it on CRUD boilerplate.
- Refactoring step is NOT optional — skipping it leads to passing but messy code.

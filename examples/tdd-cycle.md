# Example: TDD Red-Green-Refactor for a Discount Calculator

This example demonstrates strict TDD discipline: failing test → minimal code → refactor.

## Requirements

```
Business rule: Apply bulk discount to orders.
- 0-2 items: no discount
- 3-4 items: 10% discount on subtotal
- 5+ items: 15% discount on subtotal
- VIP customers always get an additional 5% (stacks with bulk)
- Round to 2 decimal places (HALF_UP)
```

---

## Cycle 1: Empty Cart

### RED — Write failing test

```java
@Test
void calculate_withEmptyCart_returnsZeroDiscount() {
    var calculator = new DiscountCalculator();

    BigDecimal discount = calculator.calculate(List.of(), false);

    assertThat(discount).isEqualByComparingTo("0.00");
}
// Run → FAILS: DiscountCalculator class doesn't exist ✅
```

### GREEN — Minimal code to pass

```java
public class DiscountCalculator {
    public BigDecimal calculate(List<OrderItem> items, boolean isVip) {
        return BigDecimal.ZERO;
    }
}
// Run → PASSES ✅
```

No refactoring needed yet.

---

## Cycle 2: Below Threshold (No Discount)

### RED

```java
@Test
void calculate_withTwoItems_returnsZeroDiscount() {
    var items = List.of(
        new OrderItem("SKU-1", new BigDecimal("50.00"), 1),
        new OrderItem("SKU-2", new BigDecimal("30.00"), 1)
    );

    BigDecimal discount = new DiscountCalculator().calculate(items, false);

    assertThat(discount).isEqualByComparingTo("0.00");
}
// Run → PASSES (already returns zero) — test is valid but doesn't drive new code
// This is fine — it documents the boundary behavior
```

---

## Cycle 3: Bulk Discount (3-4 Items, 10%)

### RED

```java
@Test
void calculate_withThreeItems_returns10PercentDiscount() {
    var items = List.of(
        new OrderItem("A", new BigDecimal("100.00"), 1),
        new OrderItem("B", new BigDecimal("200.00"), 1),
        new OrderItem("C", new BigDecimal("50.00"), 1)
    );
    // Subtotal: 350.00, 10% = 35.00

    BigDecimal discount = new DiscountCalculator().calculate(items, false);

    assertThat(discount).isEqualByComparingTo("35.00");
}
// Run → FAILS: returns 0.00, expected 35.00 ✅
```

### GREEN

```java
public class DiscountCalculator {
    public BigDecimal calculate(List<OrderItem> items, boolean isVip) {
        if (items.size() < 3) return BigDecimal.ZERO;

        BigDecimal subtotal = items.stream()
            .map(item -> item.price().multiply(BigDecimal.valueOf(item.quantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal rate = new BigDecimal("0.10");
        return subtotal.multiply(rate).setScale(2, RoundingMode.HALF_UP);
    }
}
// Run → ALL PASS ✅
```

---

## Cycle 4: Higher Discount (5+ Items, 15%)

### RED

```java
@Test
void calculate_withFiveItems_returns15PercentDiscount() {
    var items = List.of(
        new OrderItem("A", new BigDecimal("100.00"), 1),
        new OrderItem("B", new BigDecimal("100.00"), 1),
        new OrderItem("C", new BigDecimal("100.00"), 1),
        new OrderItem("D", new BigDecimal("100.00"), 1),
        new OrderItem("E", new BigDecimal("100.00"), 1)
    );
    // Subtotal: 500.00, 15% = 75.00

    BigDecimal discount = new DiscountCalculator().calculate(items, false);

    assertThat(discount).isEqualByComparingTo("75.00");
}
// Run → FAILS: returns 50.00 (10%), expected 75.00 (15%) ✅
```

### GREEN

```java
public BigDecimal calculate(List<OrderItem> items, boolean isVip) {
    if (items.size() < 3) return BigDecimal.ZERO;

    BigDecimal subtotal = subtotal(items);
    BigDecimal rate = items.size() >= 5
        ? new BigDecimal("0.15")
        : new BigDecimal("0.10");

    return subtotal.multiply(rate).setScale(2, RoundingMode.HALF_UP);
}
// Run → ALL PASS ✅
```

---

## Cycle 5: VIP Additional Discount

### RED

```java
@Test
void calculate_withVipAndThreeItems_returns15PercentDiscount() {
    var items = List.of(
        new OrderItem("A", new BigDecimal("100.00"), 1),
        new OrderItem("B", new BigDecimal("100.00"), 1),
        new OrderItem("C", new BigDecimal("100.00"), 1)
    );
    // Subtotal: 300.00, bulk 10% + VIP 5% = 15% = 45.00

    BigDecimal discount = new DiscountCalculator().calculate(items, true);

    assertThat(discount).isEqualByComparingTo("45.00");
}
// Run → FAILS: returns 30.00 (10%), expected 45.00 (15%) ✅
```

### GREEN

```java
public BigDecimal calculate(List<OrderItem> items, boolean isVip) {
    if (items.size() < 3) return BigDecimal.ZERO;

    BigDecimal subtotal = subtotal(items);
    BigDecimal rate = items.size() >= 5
        ? new BigDecimal("0.15")
        : new BigDecimal("0.10");

    if (isVip) {
        rate = rate.add(new BigDecimal("0.05"));
    }

    return subtotal.multiply(rate).setScale(2, RoundingMode.HALF_UP);
}
// Run → ALL PASS ✅
```

---

## Cycle 6: REFACTOR — Clean Up While Green

```java
public class DiscountCalculator {
    private static final int TIER_1_THRESHOLD = 3;
    private static final int TIER_2_THRESHOLD = 5;
    private static final BigDecimal TIER_1_RATE = new BigDecimal("0.10");
    private static final BigDecimal TIER_2_RATE = new BigDecimal("0.15");
    private static final BigDecimal VIP_BONUS = new BigDecimal("0.05");

    public BigDecimal calculate(List<OrderItem> items, boolean isVip) {
        BigDecimal rate = bulkRate(items.size());
        if (rate.equals(BigDecimal.ZERO)) return BigDecimal.ZERO;

        if (isVip) rate = rate.add(VIP_BONUS);

        return subtotal(items).multiply(rate).setScale(2, RoundingMode.HALF_UP);
    }

    private BigDecimal bulkRate(int itemCount) {
        if (itemCount >= TIER_2_THRESHOLD) return TIER_2_RATE;
        if (itemCount >= TIER_1_THRESHOLD) return TIER_1_RATE;
        return BigDecimal.ZERO;
    }

    private BigDecimal subtotal(List<OrderItem> items) {
        return items.stream()
            .map(OrderItem::lineTotal)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
// Run → ALL 5 TESTS PASS ✅
```

---

## Cycle 7: Edge Cases

```java
@Test
void calculate_withVipBelowThreshold_returnsZero() {
    // VIP bonus only applies when bulk discount is active
    var items = List.of(new OrderItem("A", new BigDecimal("100.00"), 1));

    BigDecimal discount = new DiscountCalculator().calculate(items, true);

    assertThat(discount).isEqualByComparingTo("0.00");
}

@Test
void calculate_roundsCorrectly() {
    var items = List.of(
        new OrderItem("A", new BigDecimal("33.33"), 1),
        new OrderItem("B", new BigDecimal("33.33"), 1),
        new OrderItem("C", new BigDecimal("33.34"), 1)
    );
    // Subtotal: 100.00, 10% = 10.00

    BigDecimal discount = new DiscountCalculator().calculate(items, false);

    assertThat(discount).isEqualByComparingTo("10.00");
}
// Run → ALL PASS ✅
```

---

## Summary

| Cycle | Test | Code Change | Status |
|---|---|---|---|
| 1 | Empty cart → 0 | Create class, return ZERO | ✅ |
| 2 | 2 items → 0 | No change needed | ✅ |
| 3 | 3 items → 10% | Add subtotal + rate logic | ✅ |
| 4 | 5 items → 15% | Add tier 2 rate | ✅ |
| 5 | VIP + 3 items → 15% | Add VIP bonus | ✅ |
| 6 | Refactor | Extract constants, methods | ✅ |
| 7 | Edge cases | No change needed | ✅ |

**Total: 7 tests, 100% coverage on DiscountCalculator, clean code.**

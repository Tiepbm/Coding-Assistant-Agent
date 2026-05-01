---
name: unit-testing
description: 'Unit testing patterns per framework: JUnit 5, xUnit, Jest/Vitest, pytest. AAA pattern, mocking, test naming, and what to unit test.'
---
# Unit Testing Patterns

## Arrange-Act-Assert (AAA)

Every unit test follows three phases. Keep them visually separated.

```java
// JUnit 5
@Test
void create_withValidRequest_returnsPayment() {
    // Arrange
    var request = new CreatePaymentRequest(
        UUID.randomUUID(), UUID.randomUUID(),
        new BigDecimal("100.00"), "VND", "ACC-001", "ACC-002");
    when(repository.findByTenantIdAndIdempotencyKey(any(), any()))
        .thenReturn(Optional.empty());
    when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

    // Act
    Payment result = service.create(request);

    // Assert
    assertThat(result.getStatus()).isEqualTo(PaymentStatus.PENDING);
    assertThat(result.getAmount()).isEqualByComparingTo("100.00");
    verify(repository).save(any(Payment.class));
}
```

```csharp
// xUnit + Moq
[Fact]
public async Task Create_WithValidRequest_ReturnsPayment()
{
    // Arrange
    var request = new CreatePaymentRequest(Guid.NewGuid(), Guid.NewGuid(),
        100.00m, "VND", "ACC-001", "ACC-002");
    _mockRepo.Setup(r => r.FindByIdempotencyKeyAsync(It.IsAny<Guid>(), It.IsAny<Guid>(), default))
        .ReturnsAsync((Payment?)null);

    // Act
    var result = await _service.CreateAsync(request, CancellationToken.None);

    // Assert
    result.Status.Should().Be("PENDING");
    _mockRepo.Verify(r => r.SaveAsync(It.IsAny<Payment>(), default), Times.Once);
}
```

```typescript
// Vitest
describe('PaymentService', () => {
  it('creates payment with valid request', async () => {
    // Arrange
    const repo = { findByKey: vi.fn().mockResolvedValue(null), save: vi.fn(p => p) };
    const service = new PaymentService(repo as any);
    const request = { tenantId: randomUUID(), amount: 100, currency: 'VND' };

    // Act
    const result = await service.create(request);

    // Assert
    expect(result.status).toBe('PENDING');
    expect(repo.save).toHaveBeenCalledOnce();
  });
});
```

```python
# pytest
def test_create_payment_with_valid_request(mock_repo):
    # Arrange
    mock_repo.find_by_idempotency_key.return_value = None
    mock_repo.save.side_effect = lambda p: p
    service = PaymentService(mock_repo)
    request = CreatePaymentRequest(
        tenant_id=uuid4(), idempotency_key=uuid4(),
        amount=Decimal("100.00"), currency="VND",
        source_account="ACC-001", dest_account="ACC-002",
    )

    # Act
    result = service.create(request)

    # Assert
    assert result.status == "PENDING"
    mock_repo.save.assert_called_once()
```

## Mocking Patterns

```java
// Mockito — mock dependencies, not the class under test
@ExtendWith(MockitoExtension.class)
class PaymentServiceTest {
    @Mock PaymentRepository repository;
    @Mock OutboxRepository outbox;
    @InjectMocks PaymentService service;

    @Test
    void create_withDuplicateKey_throwsConflict() {
        var existing = Payment.create(someRequest());
        when(repository.findByTenantIdAndIdempotencyKey(any(), any()))
            .thenReturn(Optional.of(existing));

        assertThatThrownBy(() -> service.create(someRequest()))
            .isInstanceOf(IdempotencyConflictException.class);

        verify(repository, never()).save(any());
    }
}
```

```typescript
// Jest/Vitest — mock modules at boundary
import { vi, describe, it, expect } from 'vitest';

// BAD: Mocking internal implementation details
vi.mock('../utils/formatAmount'); // Don't mock pure functions

// GOOD: Mock external boundaries (HTTP, DB, file system)
vi.mock('../clients/psp-client', () => ({
  PspClient: vi.fn().mockImplementation(() => ({
    submit: vi.fn().mockResolvedValue({ reference: 'PSP-123', status: 'OK' }),
  })),
}));
```

```python
# pytest + unittest.mock
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_repo():
    repo = AsyncMock(spec=PaymentRepository)
    repo.find_by_idempotency_key.return_value = None
    repo.save.side_effect = lambda p: p
    return repo

def test_duplicate_key_raises_conflict(mock_repo):
    mock_repo.find_by_idempotency_key.return_value = Payment(id=uuid4())
    service = PaymentService(mock_repo)

    with pytest.raises(ConflictError):
        service.create(some_request())

    mock_repo.save.assert_not_called()
```

## What to Unit Test vs Integration Test

| Unit Test | Integration Test |
|---|---|
| Business logic in services | API endpoint with real DB |
| Validation rules | Database queries (SQL dialect matters) |
| State machines, calculations | External API integration |
| Pure functions, transformations | Message consumer with real broker |
| Error handling branches | Auth middleware with real token validation |

## Test Naming Convention

```
// Pattern: method_condition_expectedResult
create_withValidRequest_savesPayment()
create_withDuplicateKey_throwsConflict()
capture_whenAlreadyCaptured_throwsIllegalState()

// For behavior-focused: should_expectedBehavior_when_condition
should_returnPending_when_paymentCreated()
should_rejectNegativeAmount_when_validating()
```

## Anti-Patterns

- **Testing implementation details**: Verifying internal method calls instead of observable behavior.
- **Mocking everything**: If you mock the DB, the HTTP client, and the logger, what are you testing?
- `@SpringBootTest` for a pure service test — use `@ExtendWith(MockitoExtension.class)`.
- Testing getters/setters — no business logic, no value.
- One giant test method with multiple acts — split into focused tests.
- `assertTrue(result != null)` — use `assertThat(result).isNotNull()` for better failure messages.
- Shared mutable state between tests — each test must be independent.

## Gotchas

- Mockito `any()` matches null in Java — use `any(Class.class)` for type safety.
- `vi.mock()` is hoisted to top of file — cannot reference variables defined after it.
- pytest fixtures are function-scoped by default — use `scope="session"` for expensive setup.
- xUnit creates a new class instance per test — use `IClassFixture<T>` for shared state.
- `jest.mock` auto-mocks all exports — use `jest.requireActual` to keep some real.
- Floating-point assertions: use `isCloseTo(expected, offset)` not `isEqualTo`.

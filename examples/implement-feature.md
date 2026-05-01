# Example: Implement a "Create Payment" Endpoint

This example demonstrates the full workflow: test first → implement → refactor → verify.
Stack: Spring Boot (pattern applies to any stack).

## 1. Understand the Requirement

```
As a tenant, I want to create a payment so that I can process a charge.
Acceptance criteria:
- POST /payments with amount, currency, source/dest accounts
- Idempotency: duplicate requests with same key return 409
- Response: 201 with payment ID and PENDING status
- Validation: amount > 0, currency is 3 chars
```

## 2. Write Failing Test (RED)

```java
@SpringBootTest
@Testcontainers
class CreatePaymentIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Autowired TestRestTemplate restTemplate;
    @Autowired PaymentRepository paymentRepository;

    @Test
    void create_withValidRequest_returns201() {
        var request = new CreatePaymentRequest(
            UUID.randomUUID(), UUID.randomUUID(),
            new BigDecimal("100.00"), "VND", "ACC-001", "ACC-002");

        var response = restTemplate.postForEntity("/payments", request, PaymentResponse.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().status()).isEqualTo("PENDING");
        assertThat(response.getBody().id()).isNotNull();
    }

    @Test
    void create_withDuplicateKey_returns409() {
        var request = new CreatePaymentRequest(
            UUID.randomUUID(), UUID.randomUUID(),
            new BigDecimal("50.00"), "VND", "ACC-001", "ACC-002");

        restTemplate.postForEntity("/payments", request, PaymentResponse.class);
        var response = restTemplate.postForEntity("/payments", request, PaymentResponse.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
    }

    @Test
    void create_withNegativeAmount_returns400() {
        var request = new CreatePaymentRequest(
            UUID.randomUUID(), UUID.randomUUID(),
            new BigDecimal("-10.00"), "VND", "ACC-001", "ACC-002");

        var response = restTemplate.postForEntity("/payments", request, ProblemDetail.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    }
}
```

Run → All 3 tests FAIL (classes don't exist yet). ✅

## 3. Implement (GREEN)

### 3a. DTO

```java
public record CreatePaymentRequest(
    @NotNull UUID tenantId,
    @NotNull UUID idempotencyKey,
    @NotNull @Positive BigDecimal amount,
    @NotBlank @Size(max = 3, min = 3) String currency,
    @NotBlank String sourceAccount,
    @NotBlank String destAccount
) {}

public record PaymentResponse(UUID id, String status, BigDecimal amount, String currency, Instant createdAt) {
    public static PaymentResponse from(Payment p) {
        return new PaymentResponse(p.getId(), p.getStatus().name(), p.getAmount(), p.getCurrency(), p.getCreatedAt());
    }
}
```

### 3b. Entity

```java
@Entity
@Table(name = "payments", uniqueConstraints = @UniqueConstraint(columns = {"tenant_id", "idempotency_key"}))
public class Payment {
    @Id @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    @Column(name = "tenant_id", nullable = false) private UUID tenantId;
    @Column(name = "idempotency_key", nullable = false) private UUID idempotencyKey;
    @Column(nullable = false, precision = 18, scale = 2) private BigDecimal amount;
    @Column(nullable = false, length = 3) private String currency;
    @Enumerated(EnumType.STRING) private PaymentStatus status = PaymentStatus.PENDING;
    private Instant createdAt = Instant.now();
    // getters...
}
```

### 3c. Service

```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final PaymentRepository payments;

    @Transactional
    public Payment create(CreatePaymentRequest request) {
        payments.findByTenantIdAndIdempotencyKey(request.tenantId(), request.idempotencyKey())
            .ifPresent(existing -> { throw new IdempotencyConflictException(existing.getId()); });

        Payment payment = new Payment(request.tenantId(), request.idempotencyKey(),
            request.amount(), request.currency());
        return payments.save(payment);
    }
}
```

### 3d. Controller

```java
@RestController
@RequiredArgsConstructor
public class PaymentController {
    private final PaymentService paymentService;

    @PostMapping("/payments")
    public ResponseEntity<PaymentResponse> create(@Valid @RequestBody CreatePaymentRequest request) {
        Payment payment = paymentService.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(PaymentResponse.from(payment));
    }
}
```

Run → All 3 tests PASS. ✅

## 4. Refactor

- Extract outbox event creation (for future event publishing).
- Add `@Version` for optimistic locking.
- Add structured logging to service.

Run → All tests still PASS. ✅

## 5. Verify

```
✅ 3/3 tests pass
✅ Coverage: 92% for changed files
✅ No security issues (parameterized queries, validated input)
✅ No lint errors
✅ Migration file created for payments table
```

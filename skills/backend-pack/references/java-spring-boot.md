---
name: java-spring-boot
description: 'Spring Boot 3 code patterns: controllers, services, JPA, transactions, Kafka, Resilience4j, validation, error handling, and tests.'
---
# Java / Spring Boot Code Patterns

## Controller Pattern

```java
// BAD: Fat controller with business logic
@PostMapping("/payments")
public ResponseEntity<?> create(@RequestBody Map<String, Object> body) {
    // 50 lines of validation + business logic + DB calls here
}

// GOOD: Thin controller, validated DTO, service owns logic
@PostMapping("/payments")
public ResponseEntity<PaymentResponse> create(
        @Valid @RequestBody CreatePaymentRequest request) {
    Payment payment = paymentService.create(request);
    return ResponseEntity.status(HttpStatus.CREATED)
        .body(PaymentResponse.from(payment));
}
```

## Service + Transaction Pattern

```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final PaymentRepository payments;
    private final OutboxRepository outbox;

    @Transactional // Transaction boundary at service level
    public Payment create(CreatePaymentRequest request) {
        // Idempotency check
        payments.findByTenantIdAndIdempotencyKey(
            request.tenantId(), request.idempotencyKey()
        ).ifPresent(existing -> {
            throw new IdempotencyConflictException(existing.getId());
        });

        Payment payment = Payment.create(request);
        payments.save(payment);

        // Outbox in same transaction
        outbox.save(OutboxEvent.of(
            payment.getId(), "payment.created",
            PaymentCreatedEvent.from(payment)
        ));

        return payment;
    }
}
```

## DTO Pattern (Records)

```java
// Request DTO with validation
public record CreatePaymentRequest(
    @NotNull UUID tenantId,
    @NotNull UUID idempotencyKey,
    @NotNull @Positive BigDecimal amount,
    @NotBlank @Size(max = 3) String currency,
    @NotBlank String sourceAccount,
    @NotBlank String destAccount
) {}

// Response DTO — never expose entity directly
public record PaymentResponse(
    UUID id, String status, BigDecimal amount, String currency, Instant createdAt
) {
    public static PaymentResponse from(Payment p) {
        return new PaymentResponse(p.getId(), p.getStatus().name(),
            p.getAmount(), p.getCurrency(), p.getCreatedAt());
    }
}
```

## JPA Entity Pattern

```java
@Entity
@Table(name = "payments",
    uniqueConstraints = @UniqueConstraint(columns = {"tenant_id", "idempotency_key"}))
public class Payment {
    @Id @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "idempotency_key", nullable = false)
    private UUID idempotencyKey;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private PaymentStatus status = PaymentStatus.PENDING;

    @Version // Optimistic locking
    private int version;

    // Business method — domain logic in entity, not service
    public void capture(String pspReference) {
        if (this.status != PaymentStatus.PENDING) {
            throw new IllegalStateException("Cannot capture payment in status: " + status);
        }
        this.status = PaymentStatus.CAPTURED;
        this.pspReference = pspReference;
    }
}
```

## Error Handling (ProblemDetail)

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        problem.setTitle("Validation Failed");
        problem.setProperty("errors", ex.getFieldErrors().stream()
            .map(e -> Map.of("field", e.getField(), "message", e.getDefaultMessage()))
            .toList());
        return problem;
    }

    @ExceptionHandler(IdempotencyConflictException.class)
    public ProblemDetail handleIdempotencyConflict(IdempotencyConflictException ex) {
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.CONFLICT);
        problem.setTitle("Idempotency Conflict");
        problem.setProperty("existingPaymentId", ex.getExistingId());
        return problem;
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleUnexpected(Exception ex) {
        log.error("Unexpected error", ex);
        ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.INTERNAL_SERVER_ERROR);
        problem.setTitle("Internal Error");
        // Never leak stack trace in production
        return problem;
    }
}
```

## Kafka Consumer (Idempotent)

```java
@KafkaListener(topics = "payments.events", groupId = "notification-service")
@Transactional
public void handle(ConsumerRecord<String, String> record) {
    PaymentEvent event = objectMapper.readValue(record.value(), PaymentEvent.class);

    // Idempotency: skip if already processed
    if (processedEvents.existsByEventId(event.eventId())) {
        log.info("Skipping duplicate event: {}", event.eventId());
        return;
    }

    notificationService.sendPaymentNotification(event);
    processedEvents.save(new ProcessedEvent(event.eventId(), Instant.now()));
}
```

## HttpClient with Resilience4j

```java
@Service
public class PspClient {
    private final RestClient restClient;

    @CircuitBreaker(name = "psp", fallbackMethod = "fallback")
    @Retry(name = "psp")
    @TimeLimiter(name = "psp")
    public PspResponse submit(PspRequest request) {
        return restClient.post()
            .uri("/v1/charges")
            .header("Idempotency-Key", request.idempotencyKey().toString())
            .body(request)
            .retrieve()
            .body(PspResponse.class);
    }

    private PspResponse fallback(PspRequest request, Exception ex) {
        log.error("PSP unavailable: {}", ex.getMessage());
        return PspResponse.pending(request.paymentId(), "PSP_UNAVAILABLE");
    }
}
```

## Test Pattern

```java
@SpringBootTest
@Testcontainers
class PaymentServiceIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Autowired PaymentService paymentService;
    @Autowired PaymentRepository paymentRepository;

    @Test
    void create_withValidRequest_savesPaymentAndOutbox() {
        var request = new CreatePaymentRequest(
            UUID.randomUUID(), UUID.randomUUID(),
            new BigDecimal("100.00"), "VND",
            "ACC-001", "ACC-002"
        );

        Payment result = paymentService.create(request);

        assertThat(result.getStatus()).isEqualTo(PaymentStatus.PENDING);
        assertThat(paymentRepository.findById(result.getId())).isPresent();
    }

    @Test
    void create_withDuplicateIdempotencyKey_throwsConflict() {
        var request = new CreatePaymentRequest(
            UUID.randomUUID(), UUID.randomUUID(),
            new BigDecimal("100.00"), "VND", "ACC-001", "ACC-002"
        );
        paymentService.create(request); // first call

        assertThatThrownBy(() -> paymentService.create(request))
            .isInstanceOf(IdempotencyConflictException.class);
    }
}
```

## Anti-Patterns

- `@Transactional` on controller methods (wrong layer).
- Exposing JPA entities as API responses (leaks internal schema).
- `spring.jpa.open-in-view=true` in production (hides N+1, leaks transactions).
- Self-invocation of `@Transactional` / `@Async` / `@Cacheable` (bypasses proxy).
- `catch (Exception e) { return null; }` (swallows failures silently).
- H2 for integration tests when production is PostgreSQL (different SQL dialect).
- `@Transactional` + Kafka publish without outbox (phantom events on rollback).

## Gotchas

- `@Version` optimistic locking: test concurrent updates, not just sequential.
- HikariCP pool size × replicas must not exceed DB max_connections.
- `@Scheduled` runs concurrently by default — use `fixedDelay` or ShedLock.
- Virtual threads (Java 21+): don't pin with `synchronized` blocks holding I/O.
- `@Transactional(readOnly = true)`: accidental writes silently fail at flush.

---
name: kotlin-spring
description: 'Kotlin + Spring Boot 3 patterns: coroutines controllers, R2DBC, idiomatic data classes, MockK tests.'
---
# Kotlin / Spring Boot Code Patterns

## Controller Pattern (Coroutines)

```kotlin
// BAD: Blocking call in suspend, untyped body
@PostMapping("/payments")
suspend fun create(@RequestBody body: Map<String, Any>): ResponseEntity<*> {
    val payment = paymentRepo.findById(body["id"] as String).block()  // mixes blocking + suspend
    // ...
}

// GOOD: Typed DTO, suspend end-to-end, response builder
@RestController
@RequestMapping("/payments")
class PaymentController(private val service: PaymentService) {

    @PostMapping
    suspend fun create(@Valid @RequestBody request: CreatePaymentRequest): ResponseEntity<PaymentResponse> {
        val payment = service.create(request)
        return ResponseEntity.status(HttpStatus.CREATED).body(PaymentResponse.from(payment))
    }
}
```

## Data Classes (DTO + Domain)

```kotlin
data class CreatePaymentRequest(
    @field:NotNull val tenantId: UUID,
    @field:NotNull val idempotencyKey: UUID,
    @field:Positive val amount: BigDecimal,
    @field:Size(min = 3, max = 3) val currency: String,
)

data class PaymentResponse(val id: UUID, val status: String, val amount: BigDecimal) {
    companion object {
        fun from(p: Payment) = PaymentResponse(p.id, p.status.name, p.amount)
    }
}
```

## Service + Transaction (R2DBC + Coroutines)

```kotlin
@Service
class PaymentService(
    private val payments: PaymentRepository,   // CoroutineCrudRepository
    private val outbox: OutboxRepository,
    private val tx: TransactionalOperator,
) {
    suspend fun create(request: CreatePaymentRequest): Payment = tx.executeAndAwait {
        payments.findByTenantIdAndIdempotencyKey(request.tenantId, request.idempotencyKey)
            ?.let { throw IdempotencyConflictException(it.id) }

        val payment = payments.save(Payment.create(request))
        outbox.save(OutboxEvent.from(payment))
        payment
    }!!
}
```

## Sealed Class Errors + ControllerAdvice

```kotlin
sealed class PaymentError(message: String) : RuntimeException(message) {
    class IdempotencyConflict(val id: UUID) : PaymentError("conflict: $id")
    class NotFound(val id: UUID) : PaymentError("not found: $id")
}

@RestControllerAdvice
class GlobalExceptionHandler {
    @ExceptionHandler(PaymentError.IdempotencyConflict::class)
    fun onConflict(e: PaymentError.IdempotencyConflict) =
        ResponseEntity.status(HttpStatus.CONFLICT)
            .body(ErrorResponse("idempotency_conflict", e.message ?: ""))
}
```

## Test (MockK + WebTestClient)

```kotlin
@SpringBootTest
@AutoConfigureWebTestClient
class PaymentControllerTest(@Autowired val client: WebTestClient) {

    @MockkBean lateinit var service: PaymentService

    @Test
    fun `POST payments returns 201 with payment response`() = runTest {
        coEvery { service.create(any()) } returns samplePayment()

        client.post().uri("/payments")
            .bodyValue(validRequest())
            .exchange()
            .expectStatus().isCreated
            .expectBody().jsonPath("$.status").isEqualTo("PENDING")
    }
}
```

## Verification

```bash
./gradlew test koverHtmlReport
./gradlew detekt
./gradlew dependencyCheckAnalyze
```


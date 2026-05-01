# Example: Fullstack Feature — "Mark Payment as Paid" (Contract → DB → API → UI)

Stack: OpenAPI + Spring Boot + Postgres + React/Next.js. Pattern is universal.

**Story:** As a finance admin, I can mark a PENDING payment as PAID, with a note. The change is auditable and the UI updates optimistically.

## 0. Acceptance Criteria

- `POST /payments/{id}/mark-paid` with `{ note?: string ≤ 500 chars }` → 200 with updated payment.
- Only `PENDING` payments can be transitioned. Others → 409 with current status.
- Only callers with `payments:write` permission for the payment's tenant.
- Audit row written in same transaction.
- UI: optimistic update with rollback on error; toast on success/failure.

## 1. Define the Contract First (api-design-pack/openapi-first)

```yaml
# openapi.yaml — diff
paths:
  /payments/{id}/mark-paid:
    post:
      operationId: markPaymentPaid
      parameters:
        - { name: id, in: path, required: true, schema: { type: string, format: uuid } }
      requestBody:
        required: false
        content:
          application/json:
            schema: { $ref: '#/components/schemas/MarkPaidRequest' }
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/Payment' } } } }
        '404': { $ref: '#/components/responses/NotFound' }
        '409': { description: Invalid state transition,
                 content: { application/json: { schema: { $ref: '#/components/schemas/InvalidStateError' } } } }
      security: [ { bearerAuth: [payments:write] } ]
components:
  schemas:
    MarkPaidRequest:
      type: object
      properties:
        note: { type: string, maxLength: 500 }
    InvalidStateError:
      allOf:
        - $ref: '#/components/schemas/Error'
        - type: object
          properties:
            currentStatus: { type: string }
```

Lint + breaking-change check:

```bash
spectral lint openapi.yaml
oasdiff breaking origin/main:openapi.yaml HEAD:openapi.yaml --fail-on ERR
```

Generate server interface (Spring) + typed client (TypeScript) — handlers MUST honor schema.

## 2. Database Migration (database-pack/migration-safety)

Audit table is new (additive — Deploy 1 only):

```sql
-- V20260501_001__add_payment_audit.sql
CREATE TABLE payment_audit (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id      UUID NOT NULL REFERENCES payments(id),
  tenant_id       UUID NOT NULL,
  actor_id        UUID NOT NULL,
  from_status     VARCHAR(20) NOT NULL,
  to_status       VARCHAR(20) NOT NULL,
  note            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX CONCURRENTLY idx_payment_audit_payment ON payment_audit(payment_id, created_at DESC);
```

No rename, no destructive change → single deploy is safe.

## 3. Backend (Test First → Implement)

### Failing test (testing-pack/unit-testing + integration-testing)

```java
@SpringBootTest
@Testcontainers
class MarkPaymentPaidIntegrationTest {
    @Container static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16");
    @Autowired TestRestTemplate http;
    @Autowired PaymentAuditRepository audit;

    @Test
    void markPaid_withPendingPayment_returns200_andWritesAudit() {
        UUID id = seed.createPendingPayment("t1");
        var resp = http.exchange(RequestEntity.post("/payments/" + id + "/mark-paid")
            .header("Authorization", bearer("alice", "t1", "payments:write"))
            .body(new MarkPaidRequest("Confirmed by bank")), PaymentResponse.class);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(resp.getBody().status()).isEqualTo("PAID");
        assertThat(audit.findByPaymentId(id)).hasSize(1);
    }

    @Test
    void markPaid_alreadyPaid_returns409_withCurrentStatus() {
        UUID id = seed.createPaidPayment("t1");
        var resp = http.exchange(RequestEntity.post("/payments/" + id + "/mark-paid")
            .header("Authorization", bearer("alice", "t1", "payments:write"))
            .body(new MarkPaidRequest(null)), Map.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
        assertThat(resp.getBody()).containsEntry("currentStatus", "PAID");
    }

    @Test
    void markPaid_otherTenant_returns404() { /* IDOR coverage */ }
}
```

### Implementation (backend-pack/java-spring-boot)

```java
@RestController
@RequiredArgsConstructor
public class PaymentTransitionController {
    private final PaymentTransitionService svc;

    @PostMapping("/payments/{id}/mark-paid")
    @PreAuthorize("hasAuthority('payments:write')")
    public PaymentResponse markPaid(
            @PathVariable UUID id,
            @Valid @RequestBody(required = false) MarkPaidRequest body,
            @AuthenticationPrincipal AuthUser user) {
        return PaymentResponse.from(
            svc.markPaid(id, user.tenantId(), user.id(),
                body == null ? null : body.note()));
    }
}

@Service
@RequiredArgsConstructor
public class PaymentTransitionService {
    private final PaymentRepository payments;
    private final PaymentAuditRepository audit;
    private final MeterRegistry meters;
    private final Tracer tracer;

    @Transactional
    public Payment markPaid(UUID paymentId, UUID tenantId, UUID actorId, String note) {
        Span span = tracer.spanBuilder("payment.mark_paid")
            .setAttribute("payment.id", paymentId.toString())
            .setAttribute("payment.tenant_id", tenantId.toString())
            .startSpan();
        try (var s = span.makeCurrent()) {
            Payment p = payments.findByIdAndTenantId(paymentId, tenantId)
                .orElseThrow(NotFoundException::new);          // 404 for IDOR safety
            if (p.getStatus() != PaymentStatus.PENDING) {
                throw new InvalidStateException(p.getStatus());  // → 409
            }
            PaymentStatus from = p.getStatus();
            p.markPaid();
            audit.save(PaymentAudit.of(p.getId(), tenantId, actorId, from, p.getStatus(), note));
            meters.counter("payments.transitioned", "to", "PAID").increment();
            return p;
        } finally {
            span.end();
        }
    }
}

@RestControllerAdvice
class TransitionExceptionHandler {
    @ExceptionHandler(InvalidStateException.class)
    ResponseEntity<Map<String, Object>> onInvalidState(InvalidStateException e) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
            "code", "invalid_state",
            "message", "payment cannot be marked paid",
            "currentStatus", e.currentStatus().name()
        ));
    }
}
```

Observability is built in (span + counter), logging via SLF4J auto-correlated to trace.

## 4. Frontend (Test First → Implement)

### Failing test (frontend-pack/react-nextjs + testing-pack/unit-testing)

```tsx
// __tests__/PaymentDetail.test.tsx
test('clicking "Mark Paid" optimistically updates and confirms on success', async () => {
  const user = userEvent.setup();
  server.use(http.post('/payments/p1/mark-paid', () => HttpResponse.json(paidPayment)));
  render(<PaymentDetail id="p1" />, { wrapper: QueryWrapper });

  await user.click(await screen.findByRole('button', { name: /mark paid/i }));
  expect(screen.getByText('PAID')).toBeInTheDocument();    // optimistic
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/marked as paid/i));
});

test('rolls back and shows error on 409', async () => {
  server.use(http.post('/payments/p1/mark-paid', () =>
    HttpResponse.json({ code: 'invalid_state', currentStatus: 'PAID' }, { status: 409 })));
  // ... assert PENDING restored, error toast shown
});
```

### Implementation (frontend-pack/state-management-advanced + accessibility)

```tsx
'use client';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { paymentsApi } from '@/gen/client';                    // generated from openapi.yaml

export function MarkPaidButton({ payment }: { payment: Payment }) {
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: (note?: string) => paymentsApi.markPaymentPaid({ id: payment.id, markPaidRequest: { note } }),
    onMutate: async (note) => {
      await qc.cancelQueries({ queryKey: ['payment', payment.id] });
      const prev = qc.getQueryData<Payment>(['payment', payment.id]);
      qc.setQueryData<Payment>(['payment', payment.id],
        (p) => p ? { ...p, status: 'PAID' } : p);              // optimistic
      return { prev };
    },
    onError: (err, _note, ctx) => {
      qc.setQueryData(['payment', payment.id], ctx?.prev);     // rollback
      toast.error(err instanceof InvalidStateError
        ? `Cannot mark paid (current: ${err.currentStatus})`
        : 'Failed to mark paid');
    },
    onSuccess: () => toast.success('Marked as paid'),
    onSettled: () => qc.invalidateQueries({ queryKey: ['payment', payment.id] }),
  });

  return (
    <button
      type="button"
      onClick={() => m.mutate(undefined)}
      disabled={m.isPending || payment.status !== 'PENDING'}
      aria-label={`Mark payment ${payment.id} as paid`}
    >
      {m.isPending ? 'Marking…' : 'Mark Paid'}
    </button>
  );
}
```

A11y: button labeled, disabled-state has reason (status check), toast uses `role="status"`.

## 5. Contract Test (api-design-pack/contract-testing)

Consumer (web) publishes a Pact, provider (api) verifies in CI:

```typescript
provider.uponReceiving('mark a PENDING payment as paid')
  .withRequest({ method: 'POST', path: '/payments/p1/mark-paid', body: { note: 'ok' } })
  .willRespondWith({ status: 200, body: { id: M.uuid('p1'), status: 'PAID' } });
```

Provider verifies → blocks merge if breaks.

## 6. Rollout (quality-pack/feature-flags + devops-pack)

```typescript
// Server gates the new endpoint behind a flag during canary
if (!await flags.getBoolean('payments.mark-paid.enabled', false, { tenantId })) {
  throw new NotFoundException();   // hide from non-canary tenants
}
```

CI canary → 5% → 25% → 100% with `payments_transitioned_total{to="PAID"}` and error rate watched.

## 7. Verification

```bash
spectral lint openapi.yaml && oasdiff breaking BASE.yaml HEAD.yaml
./mvnw verify -Pjacoco                          # backend
npm test -- --coverage && npm run lint          # frontend
npm run test:pact && pact-broker publish ...    # contract
schemathesis run --base-url=$URL openapi.yaml   # spec fuzz
```

All green → ready to ship behind canary flag.

## Skills Used (Map)

| Step | Pack / Reference |
|---|---|
| 1. Contract | `api-design-pack/openapi-first` |
| 2. Migration | `database-pack/migration-safety` |
| 3. Backend tests | `testing-pack/integration-testing` + `testing-pack/unit-testing` |
| 3. Backend impl | `backend-pack/java-spring-boot` + `observability-pack/otel-tracing` + `observability-pack/metrics-instrumentation` |
| 4. Frontend tests | `testing-pack/unit-testing` |
| 4. Frontend impl | `frontend-pack/react-nextjs` + `frontend-pack/state-management-advanced` + `frontend-pack/accessibility` |
| 5. Contract test | `api-design-pack/contract-testing` |
| 6. Rollout | `quality-pack/feature-flags` + `devops-pack/ci-cd-pipelines` |
| Throughout | `quality-pack/security-coding` (IDOR, scopes), `quality-pack/code-review-patterns` |


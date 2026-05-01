---
name: contract-testing
description: 'Consumer-driven contract testing with Pact + Spring Cloud Contract; spec-fuzzing with schemathesis; provider verification in CI.'
---
# Contract Testing Patterns

## Why Contracts > E2E

E2E tests breaking on every consumer change are noise. Contracts pin the **interface** and let producer/consumer evolve independently.

```
Consumer test:  "I send {x}, I expect {y}" → publishes pact
Provider test:  "Replay all consumer pacts against my real handler" → blocks merge if broken
```

## Pact — Consumer Side (TypeScript)

```typescript
import { PactV3, MatchersV3 as M } from '@pact-foundation/pact';

const provider = new PactV3({
  consumer: 'web-app',
  provider: 'payments-api',
  dir: './pacts',
});

test('create payment returns 201 with payment', async () => {
  provider
    .given('tenant t1 exists')
    .uponReceiving('a create payment request')
    .withRequest({
      method: 'POST', path: '/payments',
      headers: { 'Content-Type': 'application/json' },
      body: {
        tenantId: M.uuid('11111111-1111-1111-1111-111111111111'),
        idempotencyKey: M.uuid(),
        amount: M.decimal(100.50),
        currency: 'VND',
      },
    })
    .willRespondWith({
      status: 201,
      body: {
        id:     M.uuid(),
        status: M.string('PENDING'),
        amount: M.decimal(100.50),
      },
    });

  await provider.executeTest(async (mock) => {
    const client = new PaymentClient(mock.url);
    const payment = await client.create(validRequest());
    expect(payment.status).toBe('PENDING');
  });
});
```

## Pact — Provider Verification (Java/Spring)

```java
@Provider("payments-api")
@PactBroker(host = "broker.example.com", scheme = "https",
            authentication = @PactBrokerAuth(token = "${PACT_TOKEN}"))
class PaymentProviderContractTest {

    @LocalServerPort int port;

    @BeforeEach
    void setup(PactVerificationContext context) {
        context.setTarget(new HttpTestTarget("localhost", port));
    }

    @TestTemplate
    @ExtendWith(PactVerificationInvocationContextProvider.class)
    void verifyPact(PactVerificationContext context) { context.verifyInteraction(); }

    @State("tenant t1 exists")
    void tenantExists() { tenantRepo.save(new Tenant(UUID.fromString("11111111-..."))); }
}
```

CI gate: provider must verify all consumer pacts before merging — broken contract = blocked PR.

## Spring Cloud Contract (Producer-Driven Alternative)

```groovy
// contract.groovy — lives in producer repo, generates stubs for consumers
Contract.make {
    request {
        method 'POST'; url '/payments'
        body([tenantId: $(anyUuid()), amount: 100.50, currency: 'VND'])
        headers { contentType('application/json') }
    }
    response {
        status 201
        body([id: $(anyUuid()), status: 'PENDING'])
    }
}
```

Use when: you own producer + multiple consumers in same org. Use Pact when: external/independent consumers.

## Schemathesis — Fuzz from OpenAPI

```bash
# Generates thousands of property-based tests from your spec
schemathesis run http://localhost:8080/openapi.json \
  --checks=all \
  --hypothesis-max-examples=200 \
  --workers=4
```

Catches: undocumented 500s, response schema drift, malformed status codes.

## Provider State Management

```typescript
// Provider exposes setup endpoints for each "given" state in pacts
app.post('/_pact/setup', async (req, res) => {
  const { state } = req.body;
  switch (state) {
    case 'tenant t1 exists':       await db.tenant.create(...); break;
    case 'payment p1 is COMPLETED': await db.payment.upsert(...); break;
  }
  res.sendStatus(200);
});
```

Keep setups idempotent. Tear down with transaction rollback or per-test schema.

## Pact Broker — Workflow

```
1. Consumer CI runs pact tests → publishes pact to broker tagged with branch
2. Broker webhook → triggers provider verification job
3. Provider verifies pact → publishes result back to broker
4. Consumer's `can-i-deploy --pacticipant web-app --version $SHA --to prod`
   exits 0 only if all pacts verified against prod-tagged provider versions
```

```bash
pact-broker can-i-deploy \
  --pacticipant web-app --version $GIT_SHA \
  --to-environment production
```

## Don't

- Match exact values for non-deterministic fields (UUIDs, timestamps) — use matchers.
- Include business assertions in contract tests — keep them about *shape*, not values.
- Skip provider verification in CI — defeats the entire purpose.
- Let pact files drift from broker — always publish from CI, never manually.

## Verification

```bash
# Consumer
npm run test:pact && pact-broker publish ./pacts --consumer-app-version $GIT_SHA --branch $BRANCH

# Provider
./mvnw test -Dpact.verifier.publishResults=true

# Spec fuzz
schemathesis run --base-url=$URL openapi.yaml
```


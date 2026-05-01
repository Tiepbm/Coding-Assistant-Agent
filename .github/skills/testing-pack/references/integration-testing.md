---
name: integration-testing
description: 'Integration testing patterns: Testcontainers (Java, .NET, Node, Python), real DB tests, MSW/WireMock for HTTP mocking, broker tests.'
---
# Integration Testing Patterns

## Testcontainers — Real Database Tests

### Java (JUnit 5 + Testcontainers)

```java
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

@SpringBootTest
@Testcontainers
class PaymentRepositoryIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    PaymentRepository repository;

    @Test
    void findByTenantAndKey_returnsPayment_whenExists() {
        var payment = Payment.create(someRequest());
        repository.save(payment);

        var found = repository.findByTenantIdAndIdempotencyKey(
            payment.getTenantId(), payment.getIdempotencyKey());

        assertThat(found).isPresent();
        assertThat(found.get().getAmount()).isEqualByComparingTo(payment.getAmount());
    }
}
```

### .NET (xUnit + Testcontainers)

```csharp
using Testcontainers.PostgreSql;

public class PaymentRepositoryTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder()
        .WithImage("postgres:16")
        .Build();

    private AppDbContext _db = null!;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(_postgres.GetConnectionString())
            .Options;
        _db = new AppDbContext(options);
        await _db.Database.MigrateAsync();
    }

    [Fact]
    public async Task FindByIdempotencyKey_ReturnsPayment_WhenExists()
    {
        var payment = new Payment { TenantId = Guid.NewGuid(), Amount = 100m };
        _db.Payments.Add(payment);
        await _db.SaveChangesAsync();

        var found = await _db.Payments
            .FirstOrDefaultAsync(p => p.TenantId == payment.TenantId);

        found.Should().NotBeNull();
        found!.Amount.Should().Be(100m);
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();
}
```

### Node.js (Vitest + Testcontainers)

```typescript
import { PostgreSqlContainer, StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { PrismaClient } from '@prisma/client';
import { describe, it, expect, beforeAll, afterAll } from 'vitest';

describe('PaymentRepository', () => {
  let container: StartedPostgreSqlContainer;
  let prisma: PrismaClient;

  beforeAll(async () => {
    container = await new PostgreSqlContainer('postgres:16').start();
    prisma = new PrismaClient({
      datasources: { db: { url: container.getConnectionUri() } },
    });
    // Run migrations
    await prisma.$executeRawUnsafe('CREATE TABLE payments (id UUID PRIMARY KEY, amount DECIMAL)');
  }, 60_000);

  afterAll(async () => {
    await prisma.$disconnect();
    await container.stop();
  });

  it('saves and retrieves payment', async () => {
    const id = crypto.randomUUID();
    await prisma.$executeRaw`INSERT INTO payments (id, amount) VALUES (${id}::uuid, 100.00)`;

    const payment = await prisma.$queryRaw`SELECT * FROM payments WHERE id = ${id}::uuid`;
    expect(payment).toHaveLength(1);
  });
});
```

### Python (pytest + Testcontainers)

```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

@pytest.fixture
async def db_session(postgres_container):
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine, expire_on_commit=False)
    async with session() as s:
        yield s
    await engine.dispose()

@pytest.mark.anyio
async def test_save_and_find_payment(db_session):
    repo = PaymentRepository(db_session)
    payment = Payment(tenant_id=uuid4(), amount=Decimal("100.00"), currency="VND")

    saved = await repo.save(payment)
    found = await repo.find_by_id(saved.id)

    assert found is not None
    assert found.amount == Decimal("100.00")
```

## MSW for HTTP Mocking (Frontend + Node)

```typescript
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

// Define handlers at test boundary — not deep in implementation
const handlers = [
  http.get('https://api.psp.com/v1/charges/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'captured',
      reference: 'PSP-123',
    });
  }),

  http.post('https://api.psp.com/v1/charges', async ({ request }) => {
    const body = await request.json();
    if (!body.amount) {
      return HttpResponse.json({ error: 'amount required' }, { status: 400 });
    }
    return HttpResponse.json({ id: 'charge-1', status: 'pending' }, { status: 201 });
  }),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Override for specific test
it('handles PSP timeout', async () => {
  server.use(
    http.post('https://api.psp.com/v1/charges', () => {
      return HttpResponse.error(); // Network error
    })
  );

  await expect(pspClient.submit(request)).rejects.toThrow();
});
```

## WireMock for Partner API Simulation

```java
import com.github.tomakehurst.wiremock.junit5.WireMockExtension;
import static com.github.tomakehurst.wiremock.client.WireMock.*;

@ExtendWith(WireMockExtension.class)
@RegisterExtension
static WireMockExtension wireMock = WireMockExtension.newInstance()
    .options(wireMockConfig().dynamicPort())
    .build();

@Test
void submit_whenPspReturns200_returnsCaptured() {
    wireMock.stubFor(post(urlPathEqualTo("/v1/charges"))
        .willReturn(aResponse()
            .withStatus(200)
            .withHeader("Content-Type", "application/json")
            .withBody("""
                {"id": "charge-1", "status": "captured", "reference": "PSP-123"}
            """)));

    PspResponse result = pspClient.submit(someRequest());

    assertThat(result.status()).isEqualTo("captured");
    wireMock.verify(postRequestedFor(urlPathEqualTo("/v1/charges"))
        .withHeader("Idempotency-Key", matching(".*")));
}

@Test
void submit_whenPspReturns500_returnsPending() {
    wireMock.stubFor(post(urlPathEqualTo("/v1/charges"))
        .willReturn(aResponse().withStatus(500)));

    PspResponse result = pspClient.submit(someRequest());

    assertThat(result.status()).isEqualTo("pending");
}
```

## Kafka/Broker Integration Test

```java
@SpringBootTest
@EmbeddedKafka(partitions = 1, topics = {"payments.events"})
class PaymentEventConsumerTest {

    @Autowired
    KafkaTemplate<String, String> kafkaTemplate;

    @Autowired
    ProcessedEventRepository processedEvents;

    @Test
    void handle_withNewEvent_processesSuccessfully() {
        var event = """
            {"eventId": "evt-1", "type": "payment.created", "paymentId": "pay-1"}
        """;

        kafkaTemplate.send("payments.events", "pay-1", event);

        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
            assertThat(processedEvents.existsByEventId("evt-1")).isTrue();
        });
    }

    @Test
    void handle_withDuplicateEvent_skipsProcessing() {
        processedEvents.save(new ProcessedEvent("evt-2", Instant.now()));

        kafkaTemplate.send("payments.events", "pay-2",
            """{"eventId": "evt-2", "type": "payment.created"}""");

        // Verify no side effects (notification not sent twice)
        await().during(Duration.ofSeconds(3)).untilAsserted(() -> {
            assertThat(processedEvents.countByEventId("evt-2")).isEqualTo(1);
        });
    }
}
```

## Anti-Patterns

- **H2/InMemory for query-shape tests**: H2 SQL dialect differs from PostgreSQL — use Testcontainers.
- Mocking the database in integration tests — defeats the purpose.
- Shared test database without cleanup — tests depend on execution order.
- `Thread.sleep()` instead of `await().untilAsserted()` — flaky and slow.
- Testing against production APIs — use WireMock/MSW stubs.
- Skipping migration tests — "it works on my machine" until it doesn't.

## Gotchas

- Testcontainers requires Docker — CI must have Docker-in-Docker or a Docker socket.
- Container startup adds 5-15s — use `@Container` with `static` for shared lifecycle.
- MSW `onUnhandledRequest: 'error'` catches accidental real HTTP calls.
- WireMock `dynamicPort()` — inject the port into client configuration.
- EmbeddedKafka: consumer group offsets persist — use unique group IDs per test.
- Testcontainers `reuse` mode speeds up local dev but must be disabled in CI.

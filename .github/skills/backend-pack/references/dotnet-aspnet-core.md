---
name: dotnet-aspnet-core
description: 'ASP.NET Core 8 code patterns: Minimal APIs, MVC, EF Core, middleware, HttpClient resilience, BackgroundService, and tests.'
---
# C# / ASP.NET Core 8 Code Patterns

## Minimal API Pattern

```csharp
// BAD: Inline logic in endpoint definition
app.MapPost("/payments", async (HttpContext ctx) => {
    var body = await ctx.Request.ReadFromJsonAsync<Dictionary<string, object>>();
    // 40 lines of validation + DB calls here
});

// GOOD: Typed request, service injection, proper status codes
app.MapPost("/payments", async (
    [FromBody] CreatePaymentRequest request,
    [FromServices] IPaymentService service,
    CancellationToken ct) =>
{
    var payment = await service.CreateAsync(request, ct);
    return Results.Created($"/payments/{payment.Id}", PaymentResponse.From(payment));
})
.WithName("CreatePayment")
.WithValidationFilter<CreatePaymentRequest>()
.RequireAuthorization("payments:write")
.Produces<PaymentResponse>(StatusCodes.Status201Created)
.ProducesValidationProblem();
```

## MVC Controller Pattern

```csharp
// BAD: Fat controller with business logic and DbContext directly
[ApiController]
[Route("api/[controller]")]
public class PaymentsController : ControllerBase
{
    private readonly AppDbContext _db;

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] Dictionary<string, object> body)
    {
        // Direct DB access + business logic in controller
        var payment = new Payment { Amount = (decimal)body["amount"] };
        _db.Payments.Add(payment);
        await _db.SaveChangesAsync();
        return Ok(payment); // Leaks entity
    }
}

// GOOD: Thin controller, validated DTO, service owns logic
[ApiController]
[Route("api/[controller]")]
public class PaymentsController(IPaymentService paymentService) : ControllerBase
{
    [HttpPost]
    [ProducesResponseType<PaymentResponse>(StatusCodes.Status201Created)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Create(
        [FromBody] CreatePaymentRequest request,
        CancellationToken ct)
    {
        var payment = await paymentService.CreateAsync(request, ct);
        return CreatedAtAction(
            nameof(GetById),
            new { id = payment.Id },
            PaymentResponse.From(payment));
    }
}
```

## EF Core DbContext + Projections

```csharp
// BAD: Loading full entity graph for a list endpoint
public async Task<List<Payment>> GetAll()
{
    return await _db.Payments
        .Include(p => p.LineItems)
        .Include(p => p.Customer)
        .ThenInclude(c => c.Address)
        .ToListAsync(); // Loads entire graph, N+1 risk
}

// GOOD: Projection to DTO, AsNoTracking, pagination
public async Task<PagedResult<PaymentSummary>> GetAllAsync(
    int page, int pageSize, CancellationToken ct)
{
    var query = _db.Payments.AsNoTracking();

    var total = await query.CountAsync(ct);
    var items = await query
        .OrderByDescending(p => p.CreatedAt)
        .Skip((page - 1) * pageSize)
        .Take(pageSize)
        .Select(p => new PaymentSummary(
            p.Id, p.Status.ToString(), p.Amount, p.Currency, p.CreatedAt))
        .ToListAsync(ct);

    return new PagedResult<PaymentSummary>(items, total, page, pageSize);
}
```

## EF Core Configuration + Migrations

```csharp
// Entity configuration — keep out of DbContext
public class PaymentConfiguration : IEntityTypeConfiguration<Payment>
{
    public void Configure(EntityTypeBuilder<Payment> builder)
    {
        builder.ToTable("payments");
        builder.HasKey(p => p.Id);
        builder.Property(p => p.Amount).HasPrecision(18, 2);
        builder.Property(p => p.Status)
            .HasConversion<string>()
            .HasMaxLength(20);
        builder.HasIndex(p => new { p.TenantId, p.IdempotencyKey }).IsUnique();
        builder.Property(p => p.RowVersion).IsRowVersion(); // Optimistic concurrency
    }
}

// DbContext — clean, no OnModelCreating bloat
public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Payment> Payments => Set<Payment>();
    public DbSet<OutboxEvent> OutboxEvents => Set<OutboxEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(AppDbContext).Assembly);
    }
}
```

## Middleware: Exception Handling (IExceptionHandler)

```csharp
// .NET 8 IExceptionHandler — replaces UseExceptionHandler lambda
public class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger)
    : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken ct)
    {
        var (statusCode, title) = exception switch
        {
            ValidationException => (StatusCodes.Status400BadRequest, "Validation Failed"),
            IdempotencyConflictException => (StatusCodes.Status409Conflict, "Idempotency Conflict"),
            NotFoundException => (StatusCodes.Status404NotFound, "Not Found"),
            _ => (StatusCodes.Status500InternalServerError, "Internal Error")
        };

        logger.LogError(exception, "Unhandled exception: {Message}", exception.Message);

        var problem = new ProblemDetails
        {
            Status = statusCode,
            Title = title,
            Instance = httpContext.Request.Path,
            Extensions = { ["traceId"] = httpContext.TraceIdentifier }
        };

        httpContext.Response.StatusCode = statusCode;
        await httpContext.Response.WriteAsJsonAsync(problem, ct);
        return true; // Exception handled
    }
}

// Registration in Program.cs
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();
// ...
app.UseExceptionHandler();
```

## Middleware: Correlation ID

```csharp
public class CorrelationIdMiddleware(RequestDelegate next)
{
    private const string Header = "X-Correlation-Id";

    public async Task InvokeAsync(HttpContext context)
    {
        var correlationId = context.Request.Headers[Header].FirstOrDefault()
            ?? Guid.NewGuid().ToString();

        context.Items["CorrelationId"] = correlationId;
        context.Response.Headers[Header] = correlationId;

        using (LogContext.PushProperty("CorrelationId", correlationId))
        {
            await next(context);
        }
    }
}
```

## HttpClient with Resilience (.NET 8)

```csharp
// BAD: Raw HttpClient with no resilience
public class PspClient(HttpClient http)
{
    public async Task<PspResponse> SubmitAsync(PspRequest request)
    {
        var response = await http.PostAsJsonAsync("/v1/charges", request);
        response.EnsureSuccessStatusCode(); // Throws on any non-2xx
        return await response.Content.ReadFromJsonAsync<PspResponse>();
    }
}

// GOOD: Typed client with .NET 8 standard resilience
// Registration in Program.cs
builder.Services.AddHttpClient<PspClient>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["Psp:BaseUrl"]!);
    client.DefaultRequestHeaders.Add("Accept", "application/json");
})
.AddStandardResilienceHandler(options =>
{
    options.Retry.MaxRetryAttempts = 3;
    options.Retry.Delay = TimeSpan.FromMilliseconds(500);
    options.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(30);
    options.AttemptTimeout.Timeout = TimeSpan.FromSeconds(5);
});

// Client implementation
public class PspClient(HttpClient http, ILogger<PspClient> logger)
{
    public async Task<PspResponse?> SubmitAsync(
        PspRequest request, CancellationToken ct)
    {
        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, "/v1/charges");
        httpRequest.Headers.Add("Idempotency-Key", request.IdempotencyKey.ToString());
        httpRequest.Content = JsonContent.Create(request);

        var response = await http.SendAsync(httpRequest, ct);

        if (!response.IsSuccessStatusCode)
        {
            logger.LogWarning("PSP returned {Status}", response.StatusCode);
            return null;
        }

        return await response.Content.ReadFromJsonAsync<PspResponse>(ct);
    }
}
```

## BackgroundService + Outbox Relay

```csharp
public class OutboxRelayService(
    IServiceScopeFactory scopeFactory,
    ILogger<OutboxRelayService> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var scope = scopeFactory.CreateScope();
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                var publisher = scope.ServiceProvider.GetRequiredService<IEventPublisher>();

                var pending = await db.OutboxEvents
                    .Where(e => e.PublishedAt == null)
                    .OrderBy(e => e.CreatedAt)
                    .Take(50)
                    .ToListAsync(stoppingToken);

                foreach (var evt in pending)
                {
                    await publisher.PublishAsync(evt.Topic, evt.Payload, stoppingToken);
                    evt.PublishedAt = DateTimeOffset.UtcNow;
                }

                await db.SaveChangesAsync(stoppingToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                logger.LogError(ex, "Outbox relay failed");
            }

            await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
        }
    }
}
```

## Validation with FluentValidation

```csharp
public record CreatePaymentRequest(
    Guid TenantId,
    Guid IdempotencyKey,
    decimal Amount,
    string Currency,
    string SourceAccount,
    string DestAccount);

public class CreatePaymentRequestValidator : AbstractValidator<CreatePaymentRequest>
{
    public CreatePaymentRequestValidator()
    {
        RuleFor(x => x.TenantId).NotEmpty();
        RuleFor(x => x.IdempotencyKey).NotEmpty();
        RuleFor(x => x.Amount).GreaterThan(0);
        RuleFor(x => x.Currency).NotEmpty().Length(3);
        RuleFor(x => x.SourceAccount).NotEmpty().MaximumLength(50);
        RuleFor(x => x.DestAccount).NotEmpty().MaximumLength(50);
    }
}
```

## Test: WebApplicationFactory + Testcontainers

```csharp
public class PaymentApiTests : IClassFixture<PaymentApiFixture>
{
    private readonly HttpClient _client;

    public PaymentApiTests(PaymentApiFixture fixture)
    {
        _client = fixture.CreateClient();
    }

    [Fact]
    public async Task CreatePayment_WithValidRequest_Returns201()
    {
        var request = new CreatePaymentRequest(
            Guid.NewGuid(), Guid.NewGuid(),
            100.00m, "VND", "ACC-001", "ACC-002");

        var response = await _client.PostAsJsonAsync("/api/payments", request);

        response.StatusCode.Should().Be(HttpStatusCode.Created);
        var body = await response.Content.ReadFromJsonAsync<PaymentResponse>();
        body!.Status.Should().Be("Pending");
    }

    [Fact]
    public async Task CreatePayment_WithDuplicateKey_Returns409()
    {
        var request = new CreatePaymentRequest(
            Guid.NewGuid(), Guid.NewGuid(),
            100.00m, "VND", "ACC-001", "ACC-002");

        await _client.PostAsJsonAsync("/api/payments", request);
        var response = await _client.PostAsJsonAsync("/api/payments", request);

        response.StatusCode.Should().Be(HttpStatusCode.Conflict);
    }
}

// Fixture with Testcontainers
public class PaymentApiFixture : WebApplicationFactory<Program>, IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder()
        .WithImage("postgres:16")
        .Build();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureServices(services =>
        {
            services.RemoveAll<DbContextOptions<AppDbContext>>();
            services.AddDbContext<AppDbContext>(options =>
                options.UseNpgsql(_postgres.GetConnectionString()));
        });
    }

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
    }

    public new async Task DisposeAsync()
    {
        await _postgres.DisposeAsync();
    }
}
```

## Anti-Patterns

- **Sync-over-async**: `.Result` or `.Wait()` on async calls (deadlocks in ASP.NET).
- **Captive dependency**: Scoped service injected into singleton (stale DbContext).
- **Lazy loading in API**: Navigation properties trigger N+1 queries per serialized entity.
- `AddDbContext` without `pooling: true` in high-throughput scenarios.
- `Task.Run` in ASP.NET endpoints (wastes thread pool threads).
- Returning `IQueryable` from repository (leaks query logic to callers).
- `catch (Exception) { }` — swallows all errors including `OperationCanceledException`.

## Gotchas

- `CancellationToken`: always pass through; ASP.NET cancels on client disconnect.
- `IServiceScopeFactory` required in `BackgroundService` — cannot inject scoped services directly.
- EF Core `SaveChangesAsync` is NOT thread-safe — one `DbContext` per request.
- `AddStandardResilienceHandler` wraps the entire pipeline — order matters with delegating handlers.
- `record` types: EF Core cannot map records with positional constructors — use `class` for entities.
- `[FromBody]` is implicit in Minimal APIs but explicit in MVC controllers.

---
name: go-standard
description: 'Go code patterns: net/http handlers, chi router, sqlc/pgx, context propagation, errors wrapping, table-driven tests.'
---
# Go Code Patterns

## Handler Pattern

```go
// BAD: Logic in handler, no context, panics on error
func createPayment(w http.ResponseWriter, r *http.Request) {
    var req map[string]any
    json.NewDecoder(r.Body).Decode(&req)
    db.Exec("INSERT INTO payments ...", req["amount"]) // SQLi + no validation
    w.Write([]byte("ok"))
}

// GOOD: Typed request, validation, context, structured error
type CreatePaymentRequest struct {
    TenantID       uuid.UUID       `json:"tenantId" validate:"required"`
    IdempotencyKey uuid.UUID       `json:"idempotencyKey" validate:"required"`
    Amount         decimal.Decimal `json:"amount" validate:"required,gt=0"`
    Currency       string          `json:"currency" validate:"required,len=3"`
}

func (h *PaymentHandler) Create(w http.ResponseWriter, r *http.Request) {
    var req CreatePaymentRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_json", err)
        return
    }
    if err := h.validate.Struct(req); err != nil {
        writeError(w, http.StatusBadRequest, "validation_failed", err)
        return
    }
    payment, err := h.svc.Create(r.Context(), req)
    if errors.Is(err, ErrIdempotencyConflict) {
        writeError(w, http.StatusConflict, "idempotency_conflict", err)
        return
    }
    if err != nil {
        writeError(w, http.StatusInternalServerError, "internal", err)
        return
    }
    writeJSON(w, http.StatusCreated, PaymentResponse{ID: payment.ID, Status: string(payment.Status)})
}
```

## Service + Transaction Pattern (sqlc + pgx)

```go
type PaymentService struct {
    db      *pgxpool.Pool
    queries *db.Queries
}

func (s *PaymentService) Create(ctx context.Context, req CreatePaymentRequest) (db.Payment, error) {
    tx, err := s.db.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
    if err != nil {
        return db.Payment{}, fmt.Errorf("begin tx: %w", err)
    }
    defer tx.Rollback(ctx) // safe; no-op if committed

    q := s.queries.WithTx(tx)

    if existing, err := q.FindByIdempotencyKey(ctx, db.FindParams{
        TenantID: req.TenantID, Key: req.IdempotencyKey,
    }); err == nil {
        return existing, ErrIdempotencyConflict
    } else if !errors.Is(err, pgx.ErrNoRows) {
        return db.Payment{}, fmt.Errorf("idempotency lookup: %w", err)
    }

    payment, err := q.InsertPayment(ctx, db.InsertPaymentParams{
        TenantID: req.TenantID, Amount: req.Amount, Currency: req.Currency,
        IdempotencyKey: req.IdempotencyKey, Status: "PENDING",
    })
    if err != nil {
        return db.Payment{}, fmt.Errorf("insert: %w", err)
    }
    if err := q.InsertOutbox(ctx, db.OutboxParams{
        AggregateID: payment.ID, EventType: "payment.created",
    }); err != nil {
        return db.Payment{}, fmt.Errorf("outbox: %w", err)
    }
    if err := tx.Commit(ctx); err != nil {
        return db.Payment{}, fmt.Errorf("commit: %w", err)
    }
    return payment, nil
}
```

## Error Handling — Sentinel + Wrap

```go
var (
    ErrIdempotencyConflict = errors.New("idempotency conflict")
    ErrPaymentNotFound     = errors.New("payment not found")
)

// Wrap with %w to preserve chain; check with errors.Is
if err != nil {
    return fmt.Errorf("PaymentService.Create: %w", err)
}
```

## HTTP Client with Timeout + Retry

```go
client := &http.Client{
    Timeout: 5 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns: 100, MaxIdleConnsPerHost: 10, IdleConnTimeout: 90 * time.Second,
    },
}

// Retry with exponential backoff (use cenkalti/backoff or custom)
op := func() error {
    req, _ := http.NewRequestWithContext(ctx, "POST", url, body)
    resp, err := client.Do(req)
    if err != nil { return err }
    defer resp.Body.Close()
    if resp.StatusCode >= 500 { return fmt.Errorf("server error: %d", resp.StatusCode) }
    return nil
}
return backoff.Retry(op, backoff.WithContext(backoff.NewExponentialBackOff(), ctx))
```

## Table-Driven Test

```go
func TestPaymentService_Create(t *testing.T) {
    tests := []struct {
        name    string
        req     CreatePaymentRequest
        setup   func(*testing.T, *PaymentService)
        wantErr error
    }{
        {
            name: "valid request creates payment",
            req:  validRequest(),
        },
        {
            name: "duplicate idempotency key returns conflict",
            req:  validRequest(),
            setup: func(t *testing.T, s *PaymentService) {
                _, _ = s.Create(context.Background(), validRequest())
            },
            wantErr: ErrIdempotencyConflict,
        },
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            svc := newTestService(t) // testcontainers-go for real PG
            if tt.setup != nil { tt.setup(t, svc) }
            _, err := svc.Create(context.Background(), tt.req)
            if !errors.Is(err, tt.wantErr) {
                t.Fatalf("got %v, want %v", err, tt.wantErr)
            }
        })
    }
}
```

## Verification

```bash
go test ./... -race -cover -coverprofile=cover.out
go vet ./...
golangci-lint run
govulncheck ./...
```


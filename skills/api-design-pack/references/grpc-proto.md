---
name: grpc-proto
description: 'gRPC patterns: protobuf authoring with buf, unary/streaming RPCs, generated clients/servers, deadlines, interceptors.'
---
# gRPC + Protobuf Patterns

## Proto File (proto3, buf-managed)

```proto
syntax = "proto3";
package payments.v1;
option go_package = "example.com/payments/v1;paymentsv1";
option java_package = "com.example.payments.v1";
option java_multiple_files = true;

import "google/protobuf/timestamp.proto";

service PaymentService {
  rpc CreatePayment(CreatePaymentRequest) returns (CreatePaymentResponse);
  rpc GetPayment(GetPaymentRequest) returns (Payment);
  rpc StreamPaymentEvents(StreamPaymentEventsRequest) returns (stream PaymentEvent);
}

message CreatePaymentRequest {
  string tenant_id        = 1;
  string idempotency_key  = 2;
  string amount           = 3;   // decimal as string to avoid float
  string currency         = 4;   // ISO 4217
}

message CreatePaymentResponse {
  Payment payment = 1;
}

message Payment {
  string id          = 1;
  PaymentStatus status = 2;
  string amount      = 3;
  string currency    = 4;
  google.protobuf.Timestamp created_at = 5;
  // Reserve removed fields to prevent reuse
  reserved 6, 7;
  reserved "old_field";
}

enum PaymentStatus {
  PAYMENT_STATUS_UNSPECIFIED = 0;
  PAYMENT_STATUS_PENDING     = 1;
  PAYMENT_STATUS_COMPLETED   = 2;
  PAYMENT_STATUS_FAILED      = 3;
}
```

Rules:
- Field number `0` reserved for `*_UNSPECIFIED` enums (default-safe).
- Never reuse field numbers — `reserved` removed ones.
- Decimals as `string` (or use `google.type.Money`).
- `package` always versioned (`payments.v1`).

## buf — Lint, Breaking-Change, Generate

```yaml
# buf.yaml
version: v2
modules:
  - path: proto
lint:
  use: [DEFAULT]
breaking:
  use: [FILE]
```

```yaml
# buf.gen.yaml — generate Go + Java + TS clients
version: v2
plugins:
  - remote: buf.build/protocolbuffers/go
    out: gen/go
  - remote: buf.build/grpc/go
    out: gen/go
  - remote: buf.build/grpc/java
    out: gen/java
  - remote: buf.build/connectrpc/es
    out: gen/ts
```

```bash
buf lint
buf breaking --against '.git#branch=main'
buf generate
```

## Server (Go)

```go
type paymentServer struct {
    paymentsv1.UnimplementedPaymentServiceServer
    svc *PaymentService
}

func (s *paymentServer) CreatePayment(
    ctx context.Context, req *paymentsv1.CreatePaymentRequest,
) (*paymentsv1.CreatePaymentResponse, error) {
    if err := validate(req); err != nil {
        return nil, status.Errorf(codes.InvalidArgument, "validation: %v", err)
    }
    payment, err := s.svc.Create(ctx, fromProto(req))
    switch {
    case errors.Is(err, ErrIdempotencyConflict):
        return nil, status.Error(codes.AlreadyExists, "idempotency conflict")
    case err != nil:
        return nil, status.Error(codes.Internal, "internal")
    }
    return &paymentsv1.CreatePaymentResponse{Payment: toProto(payment)}, nil
}
```

Always return canonical `codes.*` (`InvalidArgument`, `NotFound`, `AlreadyExists`, `PermissionDenied`, `Unauthenticated`, `DeadlineExceeded`, `Unavailable`, `Internal`).

## Server-Streaming RPC

```go
func (s *paymentServer) StreamPaymentEvents(
    req *paymentsv1.StreamPaymentEventsRequest,
    stream paymentsv1.PaymentService_StreamPaymentEventsServer,
) error {
    ch, cancel := s.svc.Subscribe(stream.Context(), req.GetTenantId())
    defer cancel()
    for {
        select {
        case <-stream.Context().Done():
            return stream.Context().Err()
        case event, ok := <-ch:
            if !ok { return nil }
            if err := stream.Send(toProtoEvent(event)); err != nil {
                return err
            }
        }
    }
}
```

## Client — Always Set Deadline

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
resp, err := client.CreatePayment(ctx, req)
```

```java
// Java — per-call deadline
var resp = stub.withDeadlineAfter(5, TimeUnit.SECONDS).createPayment(req);
```

## Interceptors (auth, logging, retries)

```go
conn, err := grpc.NewClient(addr,
    grpc.WithTransportCredentials(creds),
    grpc.WithUnaryInterceptor(grpc_retry.UnaryClientInterceptor(
        grpc_retry.WithMax(3),
        grpc_retry.WithBackoff(grpc_retry.BackoffExponential(100*time.Millisecond)),
        grpc_retry.WithCodes(codes.Unavailable, codes.DeadlineExceeded),
    )),
    grpc.WithChainUnaryInterceptor(otelgrpc.UnaryClientInterceptor()),
)
```

## Don't

- Skip `_UNSPECIFIED` enum value at 0.
- Use `optional` everywhere (proto3 has presence on messages; primitives need explicit `optional` only when nullability matters).
- Return raw DB errors — map to gRPC status codes.
- Stream without bounded buffer + cancellation.

## Verification

```bash
buf lint
buf breaking --against '.git#branch=main,subdir=proto'
buf format -d .
ghz --insecure --proto proto/payments.proto --call payments.v1.PaymentService/CreatePayment ...  # load test
```


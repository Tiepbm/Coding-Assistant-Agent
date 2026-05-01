---
name: rust-axum
description: 'Rust + Axum patterns: extractors, typed errors with thiserror, sqlx queries, tower middleware, async tests.'
---
# Rust / Axum Code Patterns

## Handler Pattern (Extractors)

```rust
// BAD: Untyped JSON, panic on error, no validation
async fn create_payment(Json(body): Json<serde_json::Value>) -> impl IntoResponse {
    let amount = body["amount"].as_f64().unwrap();
    // ...
}

// GOOD: Typed request, validate, structured error
use axum::{extract::State, Json, http::StatusCode};
use serde::{Deserialize, Serialize};
use validator::Validate;

#[derive(Debug, Deserialize, Validate)]
pub struct CreatePaymentRequest {
    pub tenant_id: uuid::Uuid,
    pub idempotency_key: uuid::Uuid,
    #[validate(range(exclusive_min = 0.0))]
    pub amount: rust_decimal::Decimal,
    #[validate(length(equal = 3))]
    pub currency: String,
}

#[derive(Serialize)]
pub struct PaymentResponse { pub id: uuid::Uuid, pub status: String }

pub async fn create_payment(
    State(svc): State<PaymentService>,
    Json(req): Json<CreatePaymentRequest>,
) -> Result<(StatusCode, Json<PaymentResponse>), AppError> {
    req.validate()?;
    let payment = svc.create(req).await?;
    Ok((StatusCode::CREATED, Json(PaymentResponse {
        id: payment.id, status: payment.status,
    })))
}
```

## Typed Error with thiserror + IntoResponse

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("validation: {0}")]
    Validation(#[from] validator::ValidationErrors),
    #[error("idempotency conflict")]
    IdempotencyConflict,
    #[error("not found")]
    NotFound,
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
}

impl axum::response::IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, code) = match &self {
            AppError::Validation(_) => (StatusCode::BAD_REQUEST, "validation_failed"),
            AppError::IdempotencyConflict => (StatusCode::CONFLICT, "idempotency_conflict"),
            AppError::NotFound => (StatusCode::NOT_FOUND, "not_found"),
            AppError::Database(_) => (StatusCode::INTERNAL_SERVER_ERROR, "internal"),
        };
        tracing::error!(error = %self, "request failed");
        (status, Json(serde_json::json!({"code": code, "message": self.to_string()}))).into_response()
    }
}
```

## Service + Transaction (sqlx)

```rust
#[derive(Clone)]
pub struct PaymentService { pub pool: sqlx::PgPool }

impl PaymentService {
    pub async fn create(&self, req: CreatePaymentRequest) -> Result<Payment, AppError> {
        let mut tx = self.pool.begin().await?;

        let existing = sqlx::query_as!(Payment,
            "SELECT * FROM payments WHERE tenant_id = $1 AND idempotency_key = $2",
            req.tenant_id, req.idempotency_key)
            .fetch_optional(&mut *tx).await?;
        if existing.is_some() { return Err(AppError::IdempotencyConflict); }

        let payment = sqlx::query_as!(Payment,
            r#"INSERT INTO payments (id, tenant_id, idempotency_key, amount, currency, status)
               VALUES ($1, $2, $3, $4, $5, 'PENDING') RETURNING *"#,
            uuid::Uuid::new_v4(), req.tenant_id, req.idempotency_key, req.amount, req.currency)
            .fetch_one(&mut *tx).await?;

        sqlx::query!("INSERT INTO outbox (aggregate_id, event_type) VALUES ($1, $2)",
            payment.id, "payment.created").execute(&mut *tx).await?;

        tx.commit().await?;
        Ok(payment)
    }
}
```

## Router + Middleware (tower)

```rust
use axum::{Router, routing::post, middleware};
use tower_http::trace::TraceLayer;

pub fn app(svc: PaymentService) -> Router {
    Router::new()
        .route("/payments", post(create_payment))
        .with_state(svc)
        .layer(TraceLayer::new_for_http())
        .layer(middleware::from_fn(auth::require_jwt))
}
```

## Async Test (with testcontainers)

```rust
#[tokio::test]
async fn create_payment_returns_201() {
    let pool = testdb::setup().await; // testcontainers-rs Postgres
    let svc = PaymentService { pool };
    let app = app(svc);

    let response = app.oneshot(
        Request::builder().method("POST").uri("/payments")
            .header("content-type", "application/json")
            .body(Body::from(serde_json::to_vec(&valid_request()).unwrap())).unwrap()
    ).await.unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);
}
```

## Verification

```bash
cargo test --all-features
cargo clippy --all-targets -- -D warnings
cargo fmt --check
cargo audit
```


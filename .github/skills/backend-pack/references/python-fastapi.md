---
name: python-fastapi
description: 'FastAPI code patterns: endpoints, dependency injection, Pydantic models, SQLAlchemy 2.0, async, Celery, error handling, and tests.'
---
# Python / FastAPI Code Patterns

## Endpoint Pattern

```python
# BAD: No type hints, no validation, raw dict
@app.post("/payments")
async def create_payment(request: dict):
    amount = request.get("amount")  # No validation
    # 40 lines of business logic here
    return {"status": "ok"}

# GOOD: Pydantic model, dependency injection, proper status code
from fastapi import APIRouter, Depends, status
from uuid import UUID
from decimal import Decimal

from app.schemas.payment import CreatePaymentRequest, PaymentResponse
from app.services.payment import PaymentService
from app.dependencies import get_payment_service

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    request: CreatePaymentRequest,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    payment = await service.create(request)
    return PaymentResponse.model_validate(payment)
```

## Pydantic Models

```python
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from decimal import Decimal
from datetime import datetime

class CreatePaymentRequest(BaseModel):
    tenant_id: UUID
    idempotency_key: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    source_account: str = Field(min_length=1, max_length=50)
    dest_account: str = Field(min_length=1, max_length=50)

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    amount: Decimal
    currency: str
    created_at: datetime
```

## Dependency Injection

```python
# BAD: Global DB session — not request-scoped
db = SessionLocal()  # Shared across requests, not thread-safe

# GOOD: Request-scoped async session via dependency
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(settings.database_url, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_payment_service(
    db: AsyncSession = Depends(get_db),
) -> PaymentService:
    return PaymentService(db)
```

## SQLAlchemy 2.0 Async Patterns

```python
from sqlalchemy import select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal

# Entity
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    idempotency_key: Mapped[UUID] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    version: Mapped[int] = mapped_column(default=0)  # Optimistic lock

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key"),
    )

# Repository
class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_idempotency_key(
        self, tenant_id: UUID, key: UUID
    ) -> Payment | None:
        stmt = select(Payment).where(
            Payment.tenant_id == tenant_id,
            Payment.idempotency_key == key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_paginated(
        self, tenant_id: UUID, cursor: UUID | None, limit: int = 20
    ) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.tenant_id == tenant_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        if cursor:
            stmt = stmt.where(Payment.id < cursor)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, payment: Payment) -> Payment:
        self._session.add(payment)
        await self._session.flush()
        return payment
```

## Service Layer

```python
from app.models.payment import Payment
from app.repositories.payment import PaymentRepository
from app.schemas.payment import CreatePaymentRequest
from app.exceptions import ConflictError

class PaymentService:
    def __init__(self, session: AsyncSession):
        self._repo = PaymentRepository(session)
        self._session = session

    async def create(self, request: CreatePaymentRequest) -> Payment:
        # Idempotency check
        existing = await self._repo.find_by_idempotency_key(
            request.tenant_id, request.idempotency_key
        )
        if existing:
            raise ConflictError(f"Payment already exists: {existing.id}")

        payment = Payment(
            tenant_id=request.tenant_id,
            idempotency_key=request.idempotency_key,
            amount=request.amount,
            currency=request.currency,
            status="PENDING",
        )
        return await self._repo.save(payment)
```

## Error Handling

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

class AppError(Exception):
    def __init__(self, status_code: int, message: str, code: str = "ERROR"):
        self.status_code = status_code
        self.message = message
        self.code = code

class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(status.HTTP_409_CONFLICT, message, "CONFLICT")

class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(status.HTTP_404_NOT_FOUND, message, "NOT_FOUND")

# Register handlers
app = FastAPI()

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )

@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    import logging
    logging.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )
```

## Background Tasks + Celery

```python
# Simple background task (FastAPI built-in)
from fastapi import BackgroundTasks

@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def create_payment(
    request: CreatePaymentRequest,
    background_tasks: BackgroundTasks,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    payment = await service.create(request)
    background_tasks.add_task(send_notification, payment.id)
    return PaymentResponse.model_validate(payment)

# Celery for heavy/distributed tasks
from celery import Celery

celery_app = Celery("worker", broker="redis://localhost:6379/0")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_payment(self, payment_id: str) -> dict:
    try:
        # Long-running PSP integration
        result = psp_client.submit(payment_id)
        return {"status": "completed", "reference": result.reference}
    except PspUnavailableError as exc:
        raise self.retry(exc=exc)
```

## Test: pytest + httpx + TestClient

```python
import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from decimal import Decimal

from app.main import app
from app.dependencies import get_db
from app.models.base import Base

# Fixture: test database
@pytest.fixture
async def db_session():
    """Use testcontainers for real PostgreSQL."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as postgres:
        engine = create_async_engine(postgres.get_connection_url())
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session = async_sessionmaker(engine, expire_on_commit=False)
        async with session() as s:
            yield s

        await engine.dispose()

@pytest.fixture
async def client(db_session):
    """Override dependency for test DB session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

# Tests
@pytest.mark.anyio
async def test_create_payment_returns_201(client: AsyncClient):
    response = await client.post("/payments", json={
        "tenant_id": str(uuid4()),
        "idempotency_key": str(uuid4()),
        "amount": "100.00",
        "currency": "VND",
        "source_account": "ACC-001",
        "dest_account": "ACC-002",
    })

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert "id" in data

@pytest.mark.anyio
async def test_create_payment_duplicate_returns_409(client: AsyncClient):
    body = {
        "tenant_id": str(uuid4()),
        "idempotency_key": str(uuid4()),
        "amount": "50.00",
        "currency": "VND",
        "source_account": "ACC-001",
        "dest_account": "ACC-002",
    }

    await client.post("/payments", json=body)
    response = await client.post("/payments", json=body)

    assert response.status_code == 409

@pytest.mark.anyio
async def test_create_payment_invalid_body_returns_422(client: AsyncClient):
    response = await client.post("/payments", json={"amount": -10})

    assert response.status_code == 422
```

## Anti-Patterns

- **Sync DB calls in async endpoints**: Using `session.execute()` (sync) inside `async def` blocks the event loop.
- **Missing type hints**: Defeats FastAPI's auto-validation and OpenAPI generation.
- `from app.models import *` — pollutes namespace, hides dependencies.
- Mutable default arguments: `def create(items: list = [])` — shared across calls.
- `datetime.utcnow()` — deprecated in 3.12, use `datetime.now(UTC)`.
- Global `Session()` instead of request-scoped dependency.
- `except Exception: pass` — swallows all errors silently.
- Returning SQLAlchemy model directly (leaks internal schema, lazy-load errors).

## Gotchas

- FastAPI validates `Decimal` from JSON as string — send `"100.00"` not `100.00` for precision.
- `async def` endpoint with sync ORM call blocks the event loop — use `def` or async driver.
- `expire_on_commit=False` required for async sessions — otherwise attributes expire after commit.
- Pydantic V2 `model_validate` replaces V1 `from_orm` — use `ConfigDict(from_attributes=True)`.
- `Depends()` creates a new instance per request — not a singleton.
- `BackgroundTasks` run in the same process — use Celery for CPU-heavy or distributed work.
- `pytest-anyio` or `pytest-asyncio` required for async test functions.

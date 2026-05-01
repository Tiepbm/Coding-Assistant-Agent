---
name: nodejs-express
description: 'Node.js/Express/Fastify code patterns: routes, middleware, Prisma/TypeORM, async patterns, validation, error handling, and tests.'
---
# Node.js / Express Code Patterns

## Route Pattern

```typescript
// BAD: Fat route handler with inline logic
app.post('/payments', async (req, res) => {
  const { amount, currency } = req.body; // No validation
  const payment = await db.query(`INSERT INTO payments VALUES ('${amount}', '${currency}')`);
  res.json(payment); // SQL injection + no error handling
});

// GOOD: Validated request, service layer, proper error handling
import { Router } from 'express';
import { z } from 'zod';
import { validate } from '../middleware/validate';
import { PaymentService } from '../services/payment.service';

const router = Router();

const CreatePaymentSchema = z.object({
  tenantId: z.string().uuid(),
  idempotencyKey: z.string().uuid(),
  amount: z.number().positive(),
  currency: z.string().length(3),
  sourceAccount: z.string().min(1).max(50),
  destAccount: z.string().min(1).max(50),
});

router.post(
  '/payments',
  validate(CreatePaymentSchema),
  async (req, res, next) => {
    try {
      const payment = await PaymentService.create(req.body);
      res.status(201).json(payment);
    } catch (err) {
      next(err); // Forward to error middleware
    }
  }
);

export default router;
```

## Fastify Route Pattern

```typescript
import { FastifyInstance } from 'fastify';
import { Type, Static } from '@sinclair/typebox';

const CreatePaymentBody = Type.Object({
  tenantId: Type.String({ format: 'uuid' }),
  idempotencyKey: Type.String({ format: 'uuid' }),
  amount: Type.Number({ minimum: 0, exclusiveMinimum: true }),
  currency: Type.String({ minLength: 3, maxLength: 3 }),
});

type CreatePaymentInput = Static<typeof CreatePaymentBody>;

export async function paymentRoutes(app: FastifyInstance) {
  app.post<{ Body: CreatePaymentInput }>(
    '/payments',
    {
      schema: {
        body: CreatePaymentBody,
        response: { 201: PaymentResponseSchema },
      },
    },
    async (request, reply) => {
      const payment = await app.paymentService.create(request.body);
      return reply.status(201).send(payment);
    }
  );
}
```

## Service Layer

```typescript
import { PrismaClient, Payment } from '@prisma/client';
import { CreatePaymentInput } from '../schemas/payment.schema';
import { ConflictError, NotFoundError } from '../errors';

export class PaymentService {
  constructor(private readonly prisma: PrismaClient) {}

  async create(input: CreatePaymentInput): Promise<Payment> {
    // Idempotency check
    const existing = await this.prisma.payment.findUnique({
      where: {
        tenantId_idempotencyKey: {
          tenantId: input.tenantId,
          idempotencyKey: input.idempotencyKey,
        },
      },
    });

    if (existing) {
      throw new ConflictError(`Payment already exists: ${existing.id}`);
    }

    // Transaction: create payment + outbox event
    return this.prisma.$transaction(async (tx) => {
      const payment = await tx.payment.create({
        data: {
          tenantId: input.tenantId,
          idempotencyKey: input.idempotencyKey,
          amount: input.amount,
          currency: input.currency,
          status: 'PENDING',
        },
      });

      await tx.outboxEvent.create({
        data: {
          aggregateId: payment.id,
          eventType: 'payment.created',
          payload: JSON.stringify(payment),
        },
      });

      return payment;
    });
  }

  async findById(id: string): Promise<Payment> {
    const payment = await this.prisma.payment.findUnique({ where: { id } });
    if (!payment) throw new NotFoundError(`Payment ${id} not found`);
    return payment;
  }
}
```

## Prisma Schema + Queries

```prisma
// schema.prisma
model Payment {
  id             String   @id @default(uuid())
  tenantId       String   @map("tenant_id")
  idempotencyKey String   @map("idempotency_key")
  amount         Decimal  @db.Decimal(18, 2)
  currency       String   @db.VarChar(3)
  status         String   @default("PENDING")
  createdAt      DateTime @default(now()) @map("created_at")
  version        Int      @default(0)

  @@unique([tenantId, idempotencyKey])
  @@map("payments")
}
```

```typescript
// BAD: Select * with no pagination
const payments = await prisma.payment.findMany({
  include: { lineItems: true, customer: { include: { address: true } } },
});

// GOOD: Select specific fields, cursor-based pagination
const payments = await prisma.payment.findMany({
  select: {
    id: true,
    status: true,
    amount: true,
    currency: true,
    createdAt: true,
  },
  where: { tenantId },
  orderBy: { createdAt: 'desc' },
  take: pageSize,
  ...(cursor ? { skip: 1, cursor: { id: cursor } } : {}),
});
```

## Middleware: Validation (Zod)

```typescript
import { Request, Response, NextFunction } from 'express';
import { ZodSchema, ZodError } from 'zod';

export function validate(schema: ZodSchema) {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      req.body = schema.parse(req.body);
      next();
    } catch (err) {
      if (err instanceof ZodError) {
        res.status(400).json({
          type: 'validation_error',
          errors: err.errors.map((e) => ({
            path: e.path.join('.'),
            message: e.message,
          })),
        });
        return;
      }
      next(err);
    }
  };
}
```

## Middleware: Error Handling

```typescript
// BAD: No error middleware — unhandled rejections crash the process
app.post('/payments', async (req, res) => {
  const payment = await paymentService.create(req.body); // Throws → 500 HTML page
  res.json(payment);
});

// GOOD: Centralized error handler
import { Request, Response, NextFunction } from 'express';

export class AppError extends Error {
  constructor(
    public readonly statusCode: number,
    message: string,
    public readonly code?: string
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export function errorHandler(
  err: Error,
  _req: Request,
  res: Response,
  _next: NextFunction
): void {
  if (err instanceof AppError) {
    res.status(err.statusCode).json({
      error: { code: err.code, message: err.message },
    });
    return;
  }

  // Never leak stack traces in production
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' },
  });
}

// Register AFTER all routes
app.use(errorHandler);
```

## Middleware: Auth (JWT)

```typescript
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

export interface AuthRequest extends Request {
  user?: { sub: string; tenantId: string; roles: string[] };
}

export function authenticate(req: AuthRequest, res: Response, next: NextFunction): void {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    res.status(401).json({ error: { message: 'Missing token' } });
    return;
  }

  try {
    const token = header.slice(7);
    const payload = jwt.verify(token, process.env.JWT_SECRET!, {
      algorithms: ['RS256'],
      issuer: process.env.JWT_ISSUER,
    });
    req.user = payload as AuthRequest['user'];
    next();
  } catch {
    res.status(401).json({ error: { message: 'Invalid token' } });
  }
}
```

## Async Patterns

```typescript
// BAD: Callback hell
fs.readFile('config.json', (err, data) => {
  if (err) throw err;
  db.connect(JSON.parse(data), (err, conn) => {
    if (err) throw err;
    conn.query('SELECT 1', (err, result) => { /* ... */ });
  });
});

// BAD: Unhandled promise rejection
app.get('/data', async (req, res) => {
  const data = await fetchData(); // If this throws, Express < 5 won't catch it
  res.json(data);
});

// GOOD: Async wrapper for Express 4 (Express 5 handles this natively)
const asyncHandler = (fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) =>
  (req: Request, res: Response, next: NextFunction) => fn(req, res, next).catch(next);

app.get('/data', asyncHandler(async (req, res) => {
  const data = await fetchData();
  res.json(data);
}));

// GOOD: Graceful shutdown — prevent memory leaks
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    prisma.$disconnect();
    process.exit(0);
  });
  // Force exit after 10s
  setTimeout(() => process.exit(1), 10_000);
});
```

## Test: Vitest + Supertest + Testcontainers

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { PostgreSqlContainer, StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { createApp } from '../src/app';
import { PrismaClient } from '@prisma/client';

describe('Payment API', () => {
  let container: StartedPostgreSqlContainer;
  let prisma: PrismaClient;
  let app: Express.Application;

  beforeAll(async () => {
    container = await new PostgreSqlContainer('postgres:16').start();
    prisma = new PrismaClient({
      datasources: { db: { url: container.getConnectionUri() } },
    });
    await prisma.$executeRaw`CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`;
    app = createApp(prisma);
  }, 60_000);

  afterAll(async () => {
    await prisma.$disconnect();
    await container.stop();
  });

  it('POST /payments → 201 with valid request', async () => {
    const response = await request(app)
      .post('/payments')
      .send({
        tenantId: crypto.randomUUID(),
        idempotencyKey: crypto.randomUUID(),
        amount: 100.0,
        currency: 'VND',
        sourceAccount: 'ACC-001',
        destAccount: 'ACC-002',
      });

    expect(response.status).toBe(201);
    expect(response.body).toHaveProperty('id');
    expect(response.body.status).toBe('PENDING');
  });

  it('POST /payments → 409 on duplicate idempotency key', async () => {
    const body = {
      tenantId: crypto.randomUUID(),
      idempotencyKey: crypto.randomUUID(),
      amount: 50.0,
      currency: 'VND',
      sourceAccount: 'ACC-001',
      destAccount: 'ACC-002',
    };

    await request(app).post('/payments').send(body);
    const response = await request(app).post('/payments').send(body);

    expect(response.status).toBe(409);
  });

  it('POST /payments → 400 with invalid body', async () => {
    const response = await request(app)
      .post('/payments')
      .send({ amount: -10 });

    expect(response.status).toBe(400);
    expect(response.body.errors).toBeDefined();
  });
});
```

## Anti-Patterns

- **Callback hell**: Nested callbacks instead of async/await.
- **Unhandled rejections**: Missing `.catch()` or `asyncHandler` wrapper in Express 4.
- **Memory leaks**: Event listeners not removed, unbounded caches, unclosed DB connections.
- `require()` in hot paths (blocks event loop on first load).
- `JSON.parse` without try/catch on user input.
- Storing secrets in `process.env` without validation at startup.
- `any` type everywhere — defeats TypeScript's purpose.
- `console.log` instead of structured logger (pino, winston).

## Gotchas

- Express 4 does NOT catch async errors — use wrapper or upgrade to Express 5.
- Prisma `$transaction` has a default 5s timeout — increase for long operations.
- `node:crypto.randomUUID()` requires Node 19+ or `crypto.randomUUID()` polyfill.
- `BigInt` from Prisma Decimal — use `.toNumber()` or string serialization.
- `process.on('unhandledRejection')` — always register to prevent silent crashes.
- TypeORM `synchronize: true` in production will drop columns — use migrations only.

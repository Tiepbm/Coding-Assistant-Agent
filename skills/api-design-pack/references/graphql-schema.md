---
name: graphql-schema
description: 'GraphQL schema design + resolvers: SDL-first, DataLoader for N+1, error handling, code generation, persisted queries.'
---
# GraphQL Schema + Resolver Patterns

## Schema (SDL-first)

```graphql
type Query {
  payment(id: ID!): Payment
  payments(filter: PaymentFilter, first: Int = 20, after: String): PaymentConnection!
}

type Mutation {
  createPayment(input: CreatePaymentInput!): CreatePaymentPayload!
}

input CreatePaymentInput {
  clientMutationId: ID                # idempotency
  tenantId: ID!
  amount: Decimal!
  currency: CurrencyCode!
}

union CreatePaymentPayload = CreatePaymentSuccess | ValidationError | IdempotencyConflict

type CreatePaymentSuccess { payment: Payment! }
type ValidationError      { message: String!, fields: [FieldError!]! }
type IdempotencyConflict  { existingPaymentId: ID! }

type Payment {
  id: ID!
  status: PaymentStatus!
  amount: Decimal!
  currency: CurrencyCode!
  createdBy: User!         # → DataLoader
  events: [PaymentEvent!]! # → DataLoader (batch by paymentId)
}

enum PaymentStatus { PENDING COMPLETED FAILED }
scalar Decimal
scalar CurrencyCode  # ISO 4217 — validate in scalar
```

## Resolver — Avoid N+1 with DataLoader

```typescript
// BAD: each payment.createdBy fires its own query
const resolvers = {
  Payment: {
    createdBy: (p, _, { db }) => db.user.findUnique({ where: { id: p.createdById } }),
  },
};

// GOOD: batch loads per request
import DataLoader from 'dataloader';

export function createContext({ req }) {
  const userLoader = new DataLoader<string, User>(async (ids) => {
    const users = await db.user.findMany({ where: { id: { in: [...ids] } } });
    const byId = new Map(users.map(u => [u.id, u]));
    return ids.map(id => byId.get(id) ?? new Error(`user not found: ${id}`));
  });
  return { db, userLoader, viewer: req.viewer };
}

const resolvers = {
  Payment: {
    createdBy: (p, _, { userLoader }) => userLoader.load(p.createdById),
  },
};
```

## Errors as Data (Union Types)

```typescript
// BAD: throw GraphQLError for business errors → loses type info, awkward client handling
throw new GraphQLError('IDEMPOTENCY_CONFLICT');

// GOOD: typed payload union — client handles each case
const resolvers = {
  Mutation: {
    async createPayment(_, { input }, { svc }) {
      const result = await svc.create(input);
      switch (result.kind) {
        case 'success':  return { __typename: 'CreatePaymentSuccess',  payment: result.payment };
        case 'conflict': return { __typename: 'IdempotencyConflict',   existingPaymentId: result.id };
        case 'invalid':  return { __typename: 'ValidationError',       message: 'Invalid', fields: result.fields };
      }
    },
  },
};
```

Reserve thrown errors for **unexpected** failures (DB down, bug). Business outcomes = typed payloads.

## Pagination — Relay Cursor Connection

```graphql
type PaymentConnection {
  edges: [PaymentEdge!]!
  pageInfo: PageInfo!
  totalCount: Int   # OPTIONAL — expensive on large tables
}
type PaymentEdge { cursor: String!, node: Payment! }
type PageInfo { endCursor: String, hasNextPage: Boolean! }
```

Use keyset (cursor encodes `(created_at, id)`), not OFFSET — see `database-pack/sql-patterns`.

## Code Generation

```bash
# Server (TypeScript) — typed resolvers from SDL
graphql-codegen --config codegen.ts

# Client — typed hooks
graphql-codegen # generates useCreatePaymentMutation, etc.

# Java — Netflix DGS / Spring GraphQL
./gradlew generateJava
```

## Persisted Queries (production)

```typescript
// Reject arbitrary queries in production; only allow hash-pinned operations
import { createPersistedQueryLink } from 'apollo-server-plugin-persisted-queries';
// Server: validate hash → load query from store → execute
```

Benefits: smaller request payloads, prevents query-shape attacks, CDN-cacheable.

## Authorization at the Field Level

```typescript
// Use schema directives or per-resolver checks; NEVER trust client to filter
const resolvers = {
  Payment: {
    internalNotes: (p, _, { viewer }) => {
      if (!viewer.hasRole('admin') && p.tenantId !== viewer.tenantId) return null;
      return p.internalNotes;
    },
  },
};
```

## Don't

- Expose Prisma/JPA model directly as schema — leaks DB shape.
- Allow unbounded `first`/`limit` — cap at 100.
- Skip query depth/complexity limits — vulnerable to DoS.

```typescript
// graphql-armor — depth, cost, alias, directive limits
import { graphqlArmor } from '@escape.tech/graphql-armor';
const plugins = [...graphqlArmor()];
```

## Verification

```bash
graphql-inspector diff schema.prev.graphql schema.graphql --rule consider-usage
graphql-codegen --check
```


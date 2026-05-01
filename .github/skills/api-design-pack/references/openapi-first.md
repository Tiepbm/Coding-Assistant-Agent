---
name: openapi-first
description: 'OpenAPI 3.1 spec authoring, request/response validation, codegen for server stubs and typed clients.'
---
# OpenAPI-First Patterns

## Spec Skeleton (3.1)

```yaml
openapi: 3.1.0
info:
  title: Payments API
  version: 1.4.0
servers:
  - url: https://api.example.com/v1
paths:
  /payments:
    post:
      operationId: createPayment
      summary: Create a payment
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/CreatePaymentRequest' }
      responses:
        '201':
          description: Created
          content: { application/json: { schema: { $ref: '#/components/schemas/Payment' } } }
        '400': { $ref: '#/components/responses/ValidationError' }
        '409': { $ref: '#/components/responses/Conflict' }
      security: [ { bearerAuth: [] } ]
components:
  schemas:
    CreatePaymentRequest:
      type: object
      required: [tenantId, idempotencyKey, amount, currency]
      properties:
        tenantId:        { type: string, format: uuid }
        idempotencyKey:  { type: string, format: uuid }
        amount:          { type: number, exclusiveMinimum: 0 }
        currency:        { type: string, minLength: 3, maxLength: 3 }
    Payment:
      type: object
      required: [id, status, amount, currency, createdAt]
      properties:
        id:        { type: string, format: uuid }
        status:    { type: string, enum: [PENDING, COMPLETED, FAILED] }
        amount:    { type: number }
        currency:  { type: string }
        createdAt: { type: string, format: date-time }
    Error:
      type: object
      required: [code, message]
      properties:
        code:    { type: string }
        message: { type: string }
        details: { type: array, items: { type: string } }
  responses:
    ValidationError:
      description: Validation failed
      content: { application/json: { schema: { $ref: '#/components/schemas/Error' } } }
    Conflict:
      description: Idempotency conflict
      content: { application/json: { schema: { $ref: '#/components/schemas/Error' } } }
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer, bearerFormat: JWT }
```

## Codegen Recipes

```bash
# Server stubs
openapi-generator-cli generate -i openapi.yaml -g spring         -o gen/server-spring
openapi-generator-cli generate -i openapi.yaml -g aspnetcore     -o gen/server-aspnet
oapi-codegen -package api -generate types,server openapi.yaml > gen/api.go
openapi-python-client generate --path openapi.yaml --output-path gen/py-client

# Typed clients
openapi-generator-cli generate -i openapi.yaml -g typescript-axios -o gen/ts-client
```

## Spec-First Workflow

```
1. Edit openapi.yaml → 2. spectral lint → 3. codegen server interfaces
4. Implement handlers (interfaces force you to honor schema)
5. Generate clients for consumers
6. CI validates: spec lint + breaking-change diff + contract tests
```

## Request Validation Middleware

```typescript
// Express + express-openapi-validator — validate against spec at runtime
import * as OpenApiValidator from 'express-openapi-validator';
app.use(OpenApiValidator.middleware({
  apiSpec: 'openapi.yaml',
  validateRequests: true,
  validateResponses: process.env.NODE_ENV !== 'production',
}));
```

```python
# FastAPI is already OpenAPI-native; export and verify
from fastapi.openapi.utils import get_openapi
spec = get_openapi(title=app.title, version=app.version, routes=app.routes)
```

## Breaking-Change Detection (CI)

```bash
# oasdiff — fails CI if spec breaks consumers
oasdiff breaking origin/main:openapi.yaml HEAD:openapi.yaml --fail-on ERR

# Spectral lint with org ruleset
spectral lint openapi.yaml --ruleset .spectral.yaml
```

## Don't

- Hand-write client code — generate it.
- Allow `additionalProperties: true` on request schemas (silent acceptance of typos).
- Use HTTP 200 for errors — return appropriate 4xx/5xx with `Error` schema.
- Embed business rules in spec descriptions only — enforce in handler too.

## Verification

```bash
spectral lint openapi.yaml
oasdiff breaking BASE.yaml HEAD.yaml
schemathesis run --base-url=$URL openapi.yaml --checks=all
```


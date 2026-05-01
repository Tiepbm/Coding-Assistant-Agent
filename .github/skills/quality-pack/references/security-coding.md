---
name: security-coding
description: 'Security coding: OWASP Top 10 with code examples, input validation, SQL injection, XSS, auth patterns per stack.'
---
# Security Coding Patterns

## SQL Injection Prevention

```java
// BAD: String concatenation — SQL injection
String query = "SELECT * FROM users WHERE email = '" + email + "'";
// Input: ' OR '1'='1' -- → Returns all users

// GOOD: Parameterized query (Java/JDBC)
PreparedStatement stmt = conn.prepareStatement(
    "SELECT id, email, name FROM users WHERE email = ?");
stmt.setString(1, email);
```

```csharp
// GOOD: Parameterized query (C#/Dapper)
var user = await connection.QuerySingleOrDefaultAsync<User>(
    "SELECT id, email, name FROM users WHERE email = @Email",
    new { Email = email });
```

```typescript
// GOOD: Parameterized query (Node.js/Prisma)
const user = await prisma.user.findUnique({ where: { email } });

// GOOD: Raw query with parameters (Node.js/pg)
const { rows } = await pool.query(
  'SELECT id, email, name FROM users WHERE email = $1', [email]);
```

```python
# GOOD: Parameterized query (Python/SQLAlchemy)
stmt = select(User).where(User.email == email)
result = await session.execute(stmt)
```

## Input Validation at Trust Boundaries

```java
// Java: Bean Validation
public record CreateUserRequest(
    @NotBlank @Email @Size(max = 255) String email,
    @NotBlank @Size(min = 2, max = 100) String name,
    @NotBlank @Size(min = 8, max = 128) String password
) {}
```

```csharp
// C#: FluentValidation
public class CreateUserRequestValidator : AbstractValidator<CreateUserRequest>
{
    public CreateUserRequestValidator()
    {
        RuleFor(x => x.Email).NotEmpty().EmailAddress().MaximumLength(255);
        RuleFor(x => x.Name).NotEmpty().Length(2, 100);
        RuleFor(x => x.Password).NotEmpty().MinimumLength(8).MaximumLength(128);
    }
}
```

```typescript
// TypeScript: Zod
const CreateUserSchema = z.object({
  email: z.string().email().max(255),
  name: z.string().min(2).max(100),
  password: z.string().min(8).max(128),
});
```

```python
# Python: Pydantic
class CreateUserRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
```

## XSS Prevention

```typescript
// BAD: Rendering user input as HTML
element.innerHTML = userInput; // XSS vulnerability

// GOOD: Use framework's built-in escaping
// React: JSX auto-escapes by default
return <p>{userInput}</p>; // Safe — React escapes HTML entities

// BAD: dangerouslySetInnerHTML without sanitization
return <div dangerouslySetInnerHTML={{ __html: userInput }} />; // XSS!

// GOOD: Sanitize if HTML rendering is required
import DOMPurify from 'dompurify';
return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />;
```

```
Content Security Policy (CSP) header — defense in depth:
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.example.com
```

## Authentication Patterns

```typescript
// BAD: JWT in localStorage — XSS can steal it
localStorage.setItem('token', jwt);

// GOOD: httpOnly cookie — not accessible via JavaScript
// Server sets the cookie:
res.cookie('access_token', jwt, {
  httpOnly: true,    // Not accessible via document.cookie
  secure: true,      // HTTPS only
  sameSite: 'lax',   // CSRF protection
  maxAge: 900_000,   // 15 minutes
  path: '/',
});
```

```java
// JWT validation (Spring Security)
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    return http
        .csrf(csrf -> csrf.csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse()))
        .sessionManagement(session -> session.sessionCreationPolicy(STATELESS))
        .oauth2ResourceServer(oauth2 -> oauth2
            .jwt(jwt -> jwt
                .decoder(jwtDecoder())
                .jwtAuthenticationConverter(jwtAuthConverter())))
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/api/public/**").permitAll()
            .requestMatchers("/api/admin/**").hasRole("ADMIN")
            .anyRequest().authenticated())
        .build();
}
```

## Authorization: Resource-Level

```java
// BAD: Route-level only — any authenticated user can access any payment
@GetMapping("/payments/{id}")
public Payment getPayment(@PathVariable UUID id) {
    return paymentRepository.findById(id).orElseThrow(); // No tenant check!
}

// GOOD: Resource-level authorization — check ownership
@GetMapping("/payments/{id}")
public PaymentResponse getPayment(@PathVariable UUID id, @AuthenticationPrincipal JwtUser user) {
    Payment payment = paymentRepository.findById(id)
        .orElseThrow(() -> new NotFoundException("Payment not found"));

    if (!payment.getTenantId().equals(user.getTenantId())) {
        throw new ForbiddenException("Access denied"); // Don't reveal existence
    }

    return PaymentResponse.from(payment);
}
```

## Secret Management

```yaml
# BAD: Secrets in code or config files
database:
  password: "super-secret-password"  # Committed to git!

# GOOD: Environment variables (never committed)
database:
  password: ${DATABASE_PASSWORD}

# GOOD: Secrets manager (AWS, Azure, GCP)
```

```java
// BAD: Logging secrets
log.info("Connecting with password: {}", password);

// GOOD: Never log secrets
log.info("Connecting to database: {}", databaseHost);
```

## OWASP Top 10 Quick Reference

| # | Risk | Prevention |
|---|---|---|
| A01 | Broken Access Control | Resource-level authz, deny by default |
| A02 | Cryptographic Failures | TLS everywhere, encrypt PII at rest, no custom crypto |
| A03 | Injection | Parameterized queries, input validation |
| A04 | Insecure Design | Threat modeling, abuse cases in requirements |
| A05 | Security Misconfiguration | Secure defaults, remove debug endpoints |
| A06 | Vulnerable Components | Dependency scanning (Dependabot, Snyk) |
| A07 | Auth Failures | MFA, rate limiting, secure session management |
| A08 | Data Integrity Failures | Verify signatures, pin dependencies |
| A09 | Logging Failures | Structured logging, no PII in logs, audit trail |
| A10 | SSRF | Allowlist URLs, validate redirects |

## Anti-Patterns

- **Custom crypto**: Never implement your own encryption — use framework primitives.
- **Client-side auth**: Never trust client-side authorization checks alone.
- **Secrets in code**: No API keys, passwords, or tokens in source code, logs, or tests.
- `catch (Exception) { return null; }` — hides security errors.
- Disabling CSRF protection "because we use JWT" — still needed for cookie-based auth.
- Trusting `X-Forwarded-For` header without validation — can be spoofed.
- Using `MD5` or `SHA1` for password hashing — use `bcrypt`, `scrypt`, or `argon2`.

## Gotchas

- `@PreAuthorize` in Spring requires `@EnableMethodSecurity` — silent no-op without it.
- CORS `Access-Control-Allow-Origin: *` with credentials is rejected by browsers.
- `SameSite=Lax` cookies are not sent on cross-site POST — use `SameSite=None; Secure` for cross-origin APIs.
- Rate limiting must be per-user, not per-IP — multiple users behind NAT share IPs.
- JWT `exp` claim is in seconds since epoch — not milliseconds.
- `bcrypt` has a 72-byte input limit — hash long passwords with SHA-256 first.

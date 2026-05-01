# Example: Fix a SQL Injection + IDOR Vulnerability

Stack: Java + Spring Boot. Reported by security audit.

**Vulnerability A (SQLi):** Search endpoint concatenates user input into SQL.
**Vulnerability B (IDOR):** Detail endpoint authorizes by route, not by resource ownership.

## 1. Reproduce as Failing Tests (Red)

Always start with a test that proves the exploit, then make it pass.

### SQLi Repro

```java
@SpringBootTest
@AutoConfigureMockMvc
class PaymentSearchSecurityTest {
    @Autowired MockMvc mvc;

    @Test
    @WithMockUser(username = "alice", authorities = "TENANT_T1")
    void search_rejectsSqlInjectionPayload() throws Exception {
        // Exploit: union-select to leak users table
        String payload = "VND' UNION SELECT id, email, password_hash, NULL FROM users--";
        mvc.perform(get("/payments/search").param("currency", payload))
           .andExpect(status().isBadRequest())              // expect rejection
           .andExpect(jsonPath("$.code").value("validation_failed"));
    }

    @Test
    @WithMockUser(username = "alice", authorities = "TENANT_T1")
    void search_returnsOnlyOwnTenantPayments() throws Exception {
        // Seed: payment p1 owned by t1, p2 owned by t2
        mvc.perform(get("/payments/search").param("currency", "VND"))
           .andExpect(status().isOk())
           .andExpect(jsonPath("$..tenantId").value(everyItem(equalTo("t1"))));
    }
}
```

### IDOR Repro

```java
@Test
@WithMockUser(username = "alice", authorities = "TENANT_T1")
void getPayment_returns404ForOtherTenantsPayment() throws Exception {
    UUID t2Payment = seed.createPaymentForTenant(UUID.fromString("t2-..."));
    mvc.perform(get("/payments/" + t2Payment))
       .andExpect(status().isNotFound());   // NOT 200, NOT 403 (info leak)
}
```

Run → both fail (current code allows the exploit). Now fix.

## 2. Fix SQLi — Parameterized Query (Green)

```java
// BAD: string concatenation — exploitable
@Repository
public class PaymentSearchRepository {
    public List<Payment> search(String currency) {
        String sql = "SELECT * FROM payments WHERE currency = '" + currency + "'";
        return jdbc.query(sql, rowMapper);
    }
}

// GOOD: parameterized + input validation at boundary
@RestController
public class PaymentSearchController {
    @GetMapping("/payments/search")
    public List<PaymentResponse> search(
            @RequestParam @Pattern(regexp = "^[A-Z]{3}$",
                message = "currency must be ISO 4217") String currency,
            @AuthenticationPrincipal AuthUser user) {
        return service.search(user.tenantId(), currency).stream()
            .map(PaymentResponse::from).toList();
    }
}

@Repository
public class PaymentSearchRepository {
    public List<Payment> search(UUID tenantId, String currency) {
        // Parameterized: driver escapes; SQL injection impossible
        return jdbc.query(
            "SELECT * FROM payments WHERE tenant_id = ? AND currency = ?",
            new Object[]{ tenantId, currency },
            rowMapper);
    }
}
```

Two layers of defense: validation at the boundary (regex), parameterization at the data layer.

## 3. Fix IDOR — Resource-Level Authorization

```java
// BAD: route-level only — any authenticated user can fetch any payment
@GetMapping("/payments/{id}")
@PreAuthorize("isAuthenticated()")
public PaymentResponse get(@PathVariable UUID id) {
    return PaymentResponse.from(repo.findById(id).orElseThrow(NotFoundException::new));
}

// GOOD: query scoped to caller's tenant; non-owners get 404 (no info leak)
@GetMapping("/payments/{id}")
public PaymentResponse get(@PathVariable UUID id, @AuthenticationPrincipal AuthUser user) {
    Payment payment = repo.findByIdAndTenantId(id, user.tenantId())
        .orElseThrow(NotFoundException::new);   // 404 — don't reveal existence
    return PaymentResponse.from(payment);
}
```

Repository enforces ownership in the query — defense in depth even if controller is bypassed by future bug.

## 4. Audit Sibling Endpoints

A single bug = pattern. Grep for all endpoints with same anti-pattern:

```bash
# Find all repository methods missing tenantId scope
grep -rn "findById\|findAll\b" src/main/java --include="*Repository.java" \
  | grep -v "TenantId"

# Find all string-concatenated SQL
grep -rn '"\s*+\s*\w' src/main/java --include="*Repository.java" --include="*Service.java"
```

Open separate PRs for each finding (small, reviewable).

## 5. Verification

- [ ] Both repro tests pass after fix.
- [ ] Add to test suite — they become permanent regression armor.
- [ ] Run security scanner: `./mvnw org.owasp:dependency-check-maven:check`.
- [ ] Run SAST: `semgrep --config p/owasp-top-ten src/`.
- [ ] Add metrics: `auth_denied_total{reason="cross_tenant"}` to detect future probing.
- [ ] Log denied attempts at WARN with `user_id`, `requested_resource_id`, NOT the resource itself.

```bash
./mvnw verify
./mvnw org.owasp:dependency-check-maven:check
semgrep --config p/java --config p/owasp-top-ten src/
```

## 6. Don't

- Don't return 403 for IDOR — confirms resource exists. Use 404.
- Don't log the injection payload at INFO — it could contain PII or chain into log injection.
- Don't fix in stealth without test — next refactor will reintroduce.
- Don't blocklist SQLi patterns (`grep "UNION"`) — bypass is trivial. Allowlist-validate + parameterize.

## Skills Used

- `quality-pack/security-coding` — OWASP A01 (Broken Access Control) + A03 (Injection).
- `testing-pack/unit-testing` — security regression tests with `@WithMockUser`.
- `backend-pack/java-spring-boot` — `@AuthenticationPrincipal`, parameterized JDBC.
- `observability-pack/structured-logging` — log denials safely.
- `quality-pack/code-review-patterns` — find sibling instances of the same pattern.


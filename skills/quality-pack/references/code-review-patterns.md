---
name: code-review-patterns
description: 'Code review patterns: severity levels with emoji, terse format, review checklist by change type, anti-patterns.'
---
# Code Review Patterns

## Severity Levels

```
🔴 BLOCKER  — Must fix before merge. Security vulnerability, data loss, crash.
🟠 HIGH     — Should fix before merge. Bug, performance issue, missing validation.
🟡 MEDIUM   — Fix in this PR or create follow-up ticket. Design concern, missing test.
🔵 LOW      — Nice to have. Naming, minor readability improvement.
💬 NIT      — Optional. Style preference, not blocking.
```

## Terse Review Format

```
L42: 🔴 sql-injection: User input concatenated into query. Use parameterized query.
L67: 🟠 null-check: `payment` can be null here. Add guard or use Optional.
L89: 🟡 missing-test: New validation rule has no test. Add unit test.
L15: 🔵 naming: `doStuff()` → `processPayment()` for clarity.
L33: 💬 nit: Prefer `var` over explicit type (Java 21 style).
```

## Review Checklist by Change Type

### API Endpoint Change

```markdown
□ Input validation on all user-provided fields
□ Proper HTTP status codes (201 for create, 404 for not found, etc.)
□ Error responses use ProblemDetails/standard format
□ Authorization check (not just authentication)
□ Idempotency for POST/PUT operations
□ Rate limiting considered
□ API versioning if breaking change
□ OpenAPI/Swagger documentation updated
□ Integration test for happy path + error cases
```

### Database Change

```markdown
□ Migration is reversible (or has rollback plan)
□ No locking migration on large tables (use expand-contract)
□ Indexes added for new query patterns
□ No `SELECT *` in application queries
□ Transaction boundaries are correct (not too wide)
□ Backfill strategy for new NOT NULL columns
□ Data type appropriate (DECIMAL for money, TIMESTAMPTZ for dates)
□ Foreign keys and constraints present
```

### UI Change

```markdown
□ Accessible (ARIA labels, keyboard navigation, focus management)
□ Loading and error states handled
□ Form validation with user-friendly messages
□ Responsive design (mobile + desktop)
□ No hardcoded strings (i18n ready)
□ Component test with Testing Library
□ No `useEffect` for derived state
□ No secrets or tokens in client-side code
```

### Configuration Change

```markdown
□ No secrets in config files (use env vars or secrets manager)
□ Default values are safe (not production credentials)
□ Validation at startup (fail fast on missing config)
□ Environment-specific overrides work correctly
□ Documentation updated for new config options
□ Backward compatible (old config still works)
```

## Review Examples

### Security Issue (Blocker)

```java
// PR diff:
+ String query = "SELECT * FROM users WHERE email = '" + email + "'";
+ ResultSet rs = stmt.executeQuery(query);

// Review:
// L42: 🔴 sql-injection: Direct string concatenation with user input.
// Fix: Use PreparedStatement with parameterized query.
// ```java
// PreparedStatement stmt = conn.prepareStatement(
//     "SELECT * FROM users WHERE email = ?");
// stmt.setString(1, email);
// ```
```

### Missing Error Handling (High)

```typescript
// PR diff:
+ const response = await fetch('/api/payments');
+ const data = await response.json();
+ setPayments(data);

// Review:
// L67: 🟠 error-handling: No check for response.ok, no try/catch.
// Network errors and non-2xx responses will crash the component.
// Fix:
// ```typescript
// const response = await fetch('/api/payments');
// if (!response.ok) throw new Error(`HTTP ${response.status}`);
// const data = await response.json();
// ```
```

### Design Concern (Medium)

```python
# PR diff:
+ class PaymentService:
+     def create(self, request, db, cache, logger, metrics, notifier):
+         # 200 lines of logic

# Review:
# L15: 🟡 design: 6 dependencies injected as method params.
# Consider constructor injection and splitting into smaller services.
# PaymentService → PaymentCreator + PaymentNotifier
```

## How to Receive Review Feedback

```markdown
## For the author:
- Don't take it personally — reviews improve code, not judge people.
- Respond to every comment (even if just "done" or "won't fix because X").
- If you disagree, explain your reasoning — reviewers may have missed context.
- Fix blockers and highs before requesting re-review.
- Create tickets for mediums you won't fix in this PR.
```

## Anti-Patterns

- **Blocking on style while missing security issues**: Priorities matter — check security first.
- Rubber-stamp reviews ("LGTM" without reading the code).
- Reviewing only the diff without understanding the context.
- Nitpicking on style when the team has a linter — let tools handle formatting.
- "I would have done it differently" without explaining why the current approach is wrong.
- Reviewing 1000+ line PRs — ask the author to split into smaller PRs.

## Gotchas

- Review the test changes first — they tell you what the code is supposed to do.
- Check what's NOT in the PR — missing tests, missing error handling, missing docs.
- Look at the file list — unexpected files may indicate scope creep.
- `git diff --stat` gives a quick overview of change size and affected areas.
- Review migrations separately from application code — different risk profile.
- Time-box reviews: 60 minutes max per session, take breaks for large PRs.

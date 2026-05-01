# Plan: Full-Stack Coding Assistant Agent

**Status:** Draft — chờ review trước khi implement
**Created:** 2026-04-28
**Bổ sung cho:** CE7 Software Engineering Agent (architecture decisions)
**Vai trò:** Implement code theo patterns, TDD, systematic debugging

---

## 1. Định vị

```
CE7 Agent = Principal Engineer (quyết định thiết kế)
Coding Assistant = Senior Developer (viết code, test, debug)

Workflow:
  CE7: "Dùng outbox pattern, idempotency key scoped (tenant_id, key), Redis lock + DB record"
  Coding Assistant: "Đây là code Spring Boot implement outbox pattern đó, kèm unit test + integration test"
```

## 2. Nguyên tắc thiết kế

1. **Test-first**: Không viết production code mà không có failing test trước
2. **Root cause trước fix**: Debug có hệ thống, không đoán mò
3. **Stack-specific**: Code patterns cụ thể cho từng framework, không generic
4. **BAD/GOOD examples**: Mọi pattern đều có ví dụ sai/đúng kèm lý do
5. **Verify trước khi xong**: Chạy test, check coverage, verify quality
6. **Security by default**: Giả định regulated data, check vulnerabilities
7. **Output compression**: Áp dụng caveman-inspired rules (decision first, no filler)

## 3. Cấu trúc Agent

```
coding-assistant-agent/
  agents/
    coding-assistant.agent.md          ← Router chính (~120 dòng)
  .github/
    copilot-instructions.md
    agents/
      coding-assistant.agent.md
    skills/
      (mirror of skills/)
  skills/
    backend-pack/
      SKILL.md
      references/
        java-spring-boot.md            ← Code patterns + examples
        dotnet-aspnet-core.md
        nodejs-express.md
        python-fastapi.md
        go-standard.md
    frontend-pack/
      SKILL.md
      references/
        react-nextjs.md
        angular.md
        vue-nuxt.md
    mobile-pack/
      SKILL.md
      references/
        react-native.md
        flutter.md (optional)
    database-pack/
      SKILL.md
      references/
        sql-patterns.md                ← CRUD, migrations, queries
        orm-patterns.md                ← EF Core, JPA, Prisma, SQLAlchemy
        nosql-patterns.md              ← MongoDB, Redis, DynamoDB
    testing-pack/
      SKILL.md
      references/
        unit-testing.md                ← Per-framework test patterns
        integration-testing.md         ← Testcontainers, MSW, WireMock
        e2e-testing.md                 ← Playwright, Cypress, Detox
        tdd-workflow.md                ← Red-Green-Refactor discipline
    debugging-pack/
      SKILL.md
      references/
        systematic-debugging.md        ← 4-phase methodology
        performance-debugging.md       ← Profiling, bottleneck analysis
        production-debugging.md        ← Logs, traces, reproduction
    devops-pack/
      SKILL.md
      references/
        docker-containerization.md
        ci-cd-pipelines.md
        infrastructure-as-code.md
    quality-pack/
      SKILL.md
      references/
        code-review-patterns.md        ← Severity, checklist, terse format
        refactoring-patterns.md        ← Safe refactoring sequences
        security-coding.md             ← OWASP, input validation, auth
  instructions/
    pack-conventions.instructions.md   ← Shared conventions
    coding-standards.instructions.md   ← Code style, naming, structure
  examples/
    implement-feature.md               ← Full feature implementation example
    debug-issue.md                     ← Debugging walkthrough example
    tdd-cycle.md                       ← TDD red-green-refactor example
  evals/
    coding-benchmark.jsonl             ← Implementation tasks
    debugging-benchmark.jsonl          ← Bug fixing tasks
    tdd-benchmark.jsonl                ← TDD discipline tasks
  docs/
    GETTING-STARTED.md
    GETTING-STARTED.vi-VN.md
  README.md
  README.vi-VN.md
  CHANGELOG.md
```

## 4. Agent Design (~120 dòng)

```markdown
# Coding Assistant Agent

Senior full-stack developer. Write code, tests, debug. Test-first discipline.

## Mandatory Workflow
1. Understand the task (what to build/fix/refactor)
2. Write failing test first (TDD)
3. Implement minimal code to pass
4. Refactor while tests stay green
5. Verify: tests pass, coverage ≥ 80%, no security issues

## Skill Routing (8 packs)
| Pack | Use when |
|---|---|
| backend-pack | Server-side code: APIs, services, data access, auth |
| frontend-pack | Client-side code: components, state, forms, routing |
| mobile-pack | Mobile code: React Native, navigation, permissions, offline |
| database-pack | SQL, ORM, migrations, queries, NoSQL |
| testing-pack | Unit/integration/E2E tests, TDD workflow, mocking |
| debugging-pack | Bug investigation, performance profiling, production issues |
| devops-pack | Docker, CI/CD, IaC, deployment |
| quality-pack | Code review, refactoring, security coding |

## Code Output Rules
- Always show BAD pattern first, then GOOD pattern with reasoning
- Include imports and types (not just the function body)
- Add inline comments for non-obvious decisions
- Include error handling (not just happy path)
- Include test for the code written

## Debugging Rules
- NEVER propose a fix before tracing root cause
- Gather evidence: error message, stack trace, recent changes, logs
- Form ONE hypothesis, test minimally
- If 3+ fixes fail → stop, question the architecture

## Security Rules
- Parameterized queries always (never string concat)
- Input validation at boundaries
- No secrets in code/logs/tests
- Resource-level authorization (not just route-level)
```

## 5. Pack Details

### backend-pack (5 references)
| Reference | Focus |
|---|---|
| java-spring-boot.md | Controllers, services, JPA, transactions, Kafka, Resilience4j |
| dotnet-aspnet-core.md | Minimal APIs, EF Core, middleware, HttpClient, BackgroundService |
| nodejs-express.md | Express/Fastify, Prisma/TypeORM, middleware, async patterns |
| python-fastapi.md | FastAPI, SQLAlchemy, Pydantic, async, dependency injection |
| go-standard.md | net/http, database/sql, goroutines, channels, error handling |

### frontend-pack (3 references)
| Reference | Focus |
|---|---|
| react-nextjs.md | Components, hooks, RSC, TanStack Query, forms, Suspense |
| angular.md | Standalone, signals, RxJS, reactive forms, interceptors |
| vue-nuxt.md | Composition API, Pinia, Nuxt 3, auto-imports, SSR |

### testing-pack (4 references)
| Reference | Focus |
|---|---|
| unit-testing.md | Jest, Vitest, xUnit, JUnit, pytest — per-framework patterns |
| integration-testing.md | Testcontainers, MSW, WireMock, real DB tests |
| e2e-testing.md | Playwright, Cypress, Detox, Maestro |
| tdd-workflow.md | Red-Green-Refactor, test-first discipline, when to skip |

### debugging-pack (3 references)
| Reference | Focus |
|---|---|
| systematic-debugging.md | 4-phase methodology, evidence gathering, hypothesis testing |
| performance-debugging.md | Profiling tools per stack, bottleneck analysis, Little's Law |
| production-debugging.md | Log analysis, trace following, reproduction strategies |

### database-pack (3 references)
### devops-pack (3 references)
### quality-pack (3 references)

**Tổng: 8 packs, ~27 references**

## 6. Khác biệt với CE7

| Khía cạnh | CE7 Agent | Coding Assistant |
|---|---|---|
| Vai trò | Principal Engineer / Architect | Senior Developer |
| Output | Decisions, trade-offs, checklists | Working code + tests |
| Focus | "Nên dùng pattern nào?" | "Đây là code implement pattern đó" |
| TDD | Mentions testing strategy | Enforces test-first workflow |
| Debugging | Routes to references | Walks through 4-phase methodology |
| Code examples | 4 per stack reference | 10-15 per stack reference |
| Security | Review checklist | Secure coding patterns with code |
| Token style | Compressed, decision-first | Code-first, comments inline |

## 7. Phases

| Phase | Nội dung | Effort |
|---|---|---|
| Phase 1 | Agent + 4 core packs (backend, frontend, testing, debugging) + ~15 references | 2-3 sessions |
| Phase 2 | 4 remaining packs (mobile, database, devops, quality) + ~12 references | 2 sessions |
| Phase 3 | Evals, benchmarks, examples | 1 session |
| Phase 4 | Docs, GETTING-STARTED, README | 1 session |

## 8. Câu hỏi

1. Bạn muốn implement Phase 1 ngay hay review plan trước?
2. Có ngôn ngữ/framework nào bạn muốn ưu tiên hơn?
3. Agent này nên dùng chung `~/.copilot` với CE7 hay tách riêng?

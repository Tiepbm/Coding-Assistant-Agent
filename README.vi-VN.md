# Coding Assistant Agent

Agent lập trình viên full-stack cấp chuyên gia (Senior+). Viết code production, test, debug, và instrument trên **10 hệ sinh thái** (Java, Kotlin, C#, JS/TS, Python, Go, Rust, Swift, Dart) và **10 skill packs**. Kỷ luật test-first. Bổ sung cho CE7 Software Engineering Agent.

## Tổng Quan

- **[CE7 Software Engineering Agent](https://github.com/Tiepbm/software-engineering-agent)** = Principal Engineer → quyết định kiến trúc, trade-off, governance, SLO, vendor selection.
- **Coding Assistant** = Senior+ Developer (chuyên gia cao cấp) → code hoạt động, test, debug, instrumentation, contracts (chỉ implementation).

## Cài Đặt

### Global (tất cả dự án)

```bash
cp -r coding-assistant-agent/agents/ ~/.config/agents/
cp -r coding-assistant-agent/skills/  ~/.config/skills/
```

### Theo dự án

```bash
cp -r coding-assistant-agent/ your-project/
```

### GitHub Copilot

```bash
cp -r coding-assistant-agent/.github/ your-project/.github/
```

## Bản Đồ Pack (10 packs)

| Pack | References | Ngôn ngữ |
|---|---|---|
| **backend-pack** | java-spring-boot, kotlin-spring, dotnet-aspnet-core, nodejs-express, python-fastapi, go-standard, rust-axum, concurrency-patterns | Java, Kotlin, C#, TS, Python, Go, Rust |
| **frontend-pack** | react-nextjs, angular, vue-nuxt, accessibility, state-management-advanced | TypeScript |
| **mobile-pack** | react-native, flutter, swift-ios, kotlin-android | TS, Dart, Swift, Kotlin |
| **database-pack** | sql-patterns, orm-patterns, nosql-patterns, migration-safety | SQL, TS, Java, C#, Python |
| **api-design-pack** ✨ | openapi-first, graphql-schema, grpc-proto, contract-testing | YAML, GraphQL, Proto |
| **observability-pack** ✨ | structured-logging, otel-tracing, metrics-instrumentation | Tất cả |
| **testing-pack** | unit-testing, integration-testing, e2e-testing, tdd-workflow | Tất cả |
| **debugging-pack** | systematic-debugging, performance-debugging, production-debugging | Tất cả |
| **devops-pack** | docker-containerization, ci-cd-pipelines, infrastructure-as-code, aws-services | YAML, HCL, Dockerfile |
| **quality-pack** | code-review-patterns, refactoring-patterns, security-coding, feature-flags | Tất cả |

✨ = thêm mới trong v1.1.0. Các pack mới cover **implementation** cho các concern liên quan đến design; trade-off vẫn defer cho CE7.

## Ví Dụ Nhanh

**Implement tính năng (fullstack):**
```
"Thêm endpoint 'mark payment as paid' với audit log, optimistic UI, contract test, behind a flag"
→ api-design-pack/openapi-first → backend-pack/java-spring-boot → database-pack/migration-safety
  → frontend-pack/react-nextjs + state-management-advanced + accessibility
  → api-design-pack/contract-testing → quality-pack/feature-flags
→ Xem examples/fullstack-feature.md
```

**Debug lỗi:**
```
"NullPointerException trong PaymentService.process(), 5% event"
→ debugging-pack/systematic-debugging
→ Output: Phân tích 4 giai đoạn, root cause, fix kèm regression test
```

**Tối ưu hiệu năng:**
```
"GET /payments p99 = 1.8s, SLO 300ms"
→ debugging-pack/performance-debugging + database-pack/sql-patterns
  + observability-pack/otel-tracing + observability-pack/metrics-instrumentation
→ Xem examples/perf-tuning.md
```

**Migration:**
```
"Đổi tên payments.amount thành amount_cents trên production, zero downtime"
→ database-pack/migration-safety + quality-pack/feature-flags
→ Output: Kế hoạch 3 deploy expand → migrate → contract với batched backfill
```

**Thêm observability:**
```
"Instrument FastAPI service với OTel traces và JSON logs có PII redaction"
→ observability-pack/otel-tracing + observability-pack/structured-logging
```

**Fix bảo mật:**
```
"Audit phát hiện SQLi + IDOR trong /payments/search. Fix kèm regression test."
→ Xem examples/security-fix.md
```

## Cấu Trúc

```
coding-assistant-agent/
├── agents/coding-assistant.agent.md    # Router (10 packs, expert escalation, verification)
├── skills/
│   ├── backend-pack/                   # +Go, Rust, Kotlin, concurrency
│   ├── frontend-pack/                  # +a11y, advanced state mgmt
│   ├── mobile-pack/                    # +Flutter, iOS Swift, Android Kotlin
│   ├── database-pack/                  # +migration-safety
│   ├── api-design-pack/                # MỚI — OpenAPI/GraphQL/gRPC/contracts
│   ├── observability-pack/             # MỚI — logs/traces/metrics
│   ├── testing-pack/                   # không đổi
│   ├── debugging-pack/                 # không đổi
│   ├── devops-pack/                    # +aws-services
│   └── quality-pack/                   # +feature-flags
├── examples/                           # implement, debug, tdd, refactor, perf, security, fullstack
├── evals/                              # 25-task benchmark + rubric.md + run_eval.py
├── docs/                               # Hướng dẫn bắt đầu
├── .github/                            # Tích hợp GitHub Copilot (mirror)
└── instructions/                       # Quy ước pack
```

## Eval Suite

```bash
python evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$RUN_ID/responses.jsonl \
  --report   runs/$RUN_ID/report.json \
  --fail-under 90 \
  --critical-must-pass code-024,code-001,code-011,code-017,code-018
```

Xem [evals/rubric.md](evals/rubric.md) để biết chi tiết scoring.

## Tài Liệu

- [Bắt Đầu](docs/GETTING-STARTED.md)
- [Bắt Đầu (Tiếng Việt)](docs/GETTING-STARTED.vi-VN.md)
- [Quy Ước Pack](instructions/pack-conventions.instructions.md)
- [Changelog](CHANGELOG.md)

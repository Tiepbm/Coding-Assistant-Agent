# Bắt Đầu với Coding Assistant Agent

## Đây Là Gì?

Agent lập trình viên full-stack cấp chuyên gia (Senior+), viết code production, test, debug, và instrument trên **10 hệ sinh thái** (Java, Kotlin, C#, JS/TS, Python, Go, Rust, Swift, Dart) và **10 skill packs**. Kỷ luật test-first. Bổ sung cho CE7 Software Engineering Agent.

## Khi Nào Dùng

- **Implement tính năng**: API endpoint, UI component, database query, fullstack flow (xem `examples/fullstack-feature.md`).
- **Viết test**: Unit, integration, E2E, contract — theo quy trình TDD.
- **Debug lỗi**: Phương pháp 4 giai đoạn có hệ thống, không đoán mò (xem `examples/perf-tuning.md`).
- **Code review**: Phản hồi có cấu trúc với mức độ nghiêm trọng.
- **Refactoring**: Trình tự an toàn dưới test coverage (xem `examples/refactor-legacy.md`).
- **API contracts**: OpenAPI / GraphQL / gRPC implementation + contract tests.
- **Observability**: Structured logging, OTel tracing, RED/USE metrics — chỉ instrumentation.
- **Migrations**: Zero-downtime expand → migrate → contract patterns.
- **Feature flags**: Kill-switches, percentage rollouts, in-memory test providers.
- **Fix bảo mật**: Reproduce → parameterize → resource-level authz (xem `examples/security-fix.md`).

## Khi Nào KHÔNG Dùng (defer cho CE7)

- **Topology hệ thống** (split/merge service, bounded context mới).
- **Định nghĩa SLO/SLI**, error-budget policy, alert thresholds.
- **Chiến lược versioning API public** và breaking-change governance.
- **Chọn vendor** (observability platform, feature-flag SaaS, message broker).
- **Chiến lược multi-region / multi-tenant isolation**.

```
CE7 Agent          → "Dùng outbox pattern; idempotency key scoped (tenant_id, key); SLO p99 < 300ms"
Coding Assistant   → "Đây là code Spring Boot + Postgres + integration test + OTel span + Pact contract"
```

## Cài Đặt 5 Phút

### Cách 1: Cài Global (tất cả dự án)

Copy thư mục `agents/` và `skills/` vào thư mục cấu hình agent global.

### Cách 2: Cài Theo Dự Án

Copy toàn bộ thư mục `coding-assistant-agent/` vào root dự án.

### Cách 3: Cài Workspace

Symlink hoặc copy vào thư mục `.agents/` hoặc `.github/` của workspace.

## Ví Dụ Nhanh

### "Implement endpoint thanh toán"

Agent sẽ:
1. Viết integration test thất bại (RED)
2. Implement endpoint với validation, service layer, error handling (GREEN)
3. Refactor trong khi test vẫn pass
4. Xác minh: test pass, coverage ≥ 80%, không có lỗi bảo mật

### "Debug NullPointerException này"

Agent sẽ:
1. Thu thập bằng chứng (stack trace, log, thay đổi gần đây)
2. Thu hẹp phạm vi (Ở ĐÂU, CÁI GÌ, KHI NÀO, TẠI SAO)
3. Đặt một giả thuyết và kiểm tra
4. Implement fix kèm regression test

### "Review PR này"

Agent sẽ:
1. Kiểm tra lỗi bảo mật trước (blocker)
2. Kiểm tra tính đúng đắn (high)
3. Kiểm tra thiết kế và test (medium)
4. Ghi chú cải thiện style (low/nit)

## Bản Đồ Pack (10 packs)

| Pack | Ngôn ngữ/Framework | Khi Nào Dùng |
|---|---|---|
| backend-pack | Java, Kotlin, C#, Node.js, Python, Go, Rust | Code server-side, concurrency |
| frontend-pack | React, Angular, Vue | Code client-side, a11y, state management |
| mobile-pack | React Native, Flutter, iOS Swift, Android Kotlin | Ứng dụng mobile |
| database-pack | SQL, ORM, Redis, MongoDB, DynamoDB | Tầng dữ liệu, migration zero-downtime |
| api-design-pack | OpenAPI, GraphQL, gRPC, Pact | API contracts, contract testing |
| observability-pack | OTel, Prometheus, structlog | Logging, tracing, metrics |
| testing-pack | JUnit, xUnit, Jest, pytest, Go test | Viết test, TDD workflow |
| debugging-pack | Tất cả stack | Điều tra bug, performance profiling |
| devops-pack | Docker, GitHub Actions, Terraform, AWS CDK | Hạ tầng, CI/CD, AWS services |
| quality-pack | Tất cả stack | Code review, bảo mật, feature flags |

## So Sánh với CE7 Agent

| Khía cạnh | CE7 Agent | Coding Assistant |
|---|---|---|
| Vai trò | Principal Engineer | Senior+ Developer |
| Output | Quyết định, trade-off | Code hoạt động + test |
| Focus | "Dùng pattern nào?" | "Đây là code" |
| TDD | Đề cập testing | Bắt buộc test-first |
| Debug | Chỉ đến reference | Phương pháp 4 giai đoạn |
| API contracts | Chọn REST vs GraphQL | Viết OpenAPI spec + contract test |
| Observability | Định nghĩa SLO/SLI | Viết code OTel + metrics |

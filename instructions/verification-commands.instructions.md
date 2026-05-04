---
description: 'Verification commands per stack and language support matrix. Referenced by the agent at verify step.'
applyTo: 'agents/*.agent.md'
---
# Verification Commands & Language Support

## Verification Commands (per stack)

Run before declaring done. Coverage threshold: 80% for changed lines.

```bash
# Java / Kotlin (Maven)
./mvnw verify -Pjacoco
# Java / Kotlin (Gradle)
./gradlew check koverHtmlReport detekt
# .NET
dotnet test --collect:"XPlat Code Coverage" --logger trx
dotnet format --verify-no-changes
# Node.js / TypeScript
npm test -- --coverage && npm run lint && npm audit --production
# Python
pytest --cov=src --cov-fail-under=80 && ruff check . && mypy src && bandit -r src
# Go
go test ./... -race -cover -coverprofile=cover.out && go vet ./... && golangci-lint run && govulncheck ./...
# Rust
cargo test --all-features && cargo clippy --all-targets -- -D warnings && cargo fmt --check && cargo audit
# Flutter
flutter test --coverage && flutter analyze
# iOS
xcodebuild test -scheme App -enableCodeCoverage YES && swiftlint --strict
# Android
./gradlew testDebugUnitTest detekt ktlintCheck lintDebug
```

## Language Support Matrix

| Language | Frameworks | Reference |
|---|---|---|
| **Java** | Spring Boot 3, JPA, Kafka, Resilience4j, virtual threads | `backend-pack/java-spring-boot`, `concurrency-patterns` |
| **Kotlin (server)** | Spring Boot 3 + coroutines, R2DBC, MockK | `backend-pack/kotlin-spring` |
| **Kotlin (Android)** | Jetpack Compose, ViewModel, Hilt, Retrofit | `mobile-pack/kotlin-android` |
| **C#** | ASP.NET Core 8, EF Core, Minimal APIs, Channels | `backend-pack/dotnet-aspnet-core`, `concurrency-patterns` |
| **JavaScript/TypeScript** | Node.js/Express, React/Next.js, Angular, Vue/Nuxt, React Native | `backend-pack/nodejs-express`, `frontend-pack/*`, `mobile-pack/react-native` |
| **Python** | FastAPI, SQLAlchemy 2.0, Pydantic, asyncio TaskGroup | `backend-pack/python-fastapi`, `concurrency-patterns` |
| **Go** | net/http, chi, sqlc/pgx, errgroup | `backend-pack/go-standard`, `concurrency-patterns` |
| **Rust** | Axum, sqlx, thiserror, tokio | `backend-pack/rust-axum`, `concurrency-patterns` |
| **Swift** | SwiftUI, Observable, async/await, URLSession | `mobile-pack/swift-ios` |
| **Dart** | Flutter, Riverpod, go_router, Dio | `mobile-pack/flutter` |

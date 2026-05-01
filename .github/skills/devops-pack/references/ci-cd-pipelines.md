---
name: ci-cd-pipelines
description: 'CI/CD patterns: GitHub Actions workflows, build/test/scan/deploy stages, secret management, matrix builds, caching.'
---
# CI/CD Pipeline Patterns

## GitHub Actions: Standard Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: write

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'gradle'

      - name: Build
        run: ./gradlew build -x test

      - name: Test
        run: ./gradlew test
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: build/reports/tests/

  security-scan:
    runs-on: ubuntu-latest
    needs: build-and-test
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  deploy:
    runs-on: ubuntu-latest
    needs: [build-and-test, security-scan]
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Node.js Workflow

```yaml
name: CI - Node.js

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]

    steps:
      - uses: actions/checkout@v4

      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm run build
      - run: npm test -- --coverage

      - name: Upload coverage
        if: matrix.node-version == 20
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/
```

## Python Workflow

```yaml
name: CI - Python

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint
        run: ruff check .

      - name: Type check
        run: mypy src/

      - name: Test
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
```

## .NET Workflow

```yaml
name: CI - .NET

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - name: Restore
        run: dotnet restore

      - name: Build
        run: dotnet build --no-restore

      - name: Test
        run: dotnet test --no-build --verbosity normal --collect:"XPlat Code Coverage"
```

## Secret Management

```yaml
# BAD: Secrets in workflow file
env:
  API_KEY: "sk-1234567890"  # ❌ Exposed in repo

# GOOD: GitHub Secrets + environment protection
jobs:
  deploy:
    environment: production  # Requires approval
    steps:
      - name: Deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: ./deploy.sh

# GOOD: OIDC for cloud providers (no long-lived secrets)
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/deploy
          aws-region: ap-southeast-1
```

## Caching Strategies

```yaml
# Gradle cache
- uses: actions/setup-java@v4
  with:
    cache: 'gradle'

# npm cache
- uses: actions/setup-node@v4
  with:
    cache: 'npm'

# Docker layer cache
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max

# Custom cache
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: ${{ runner.os }}-pip-
```

## Anti-Patterns

- **Long-lived secrets**: Use OIDC federation for cloud providers instead of static keys.
- **No caching**: Every build downloads dependencies from scratch — slow and wasteful.
- **No artifact pinning**: `uses: actions/checkout@main` — pin to SHA or version tag.
- Running all tests sequentially when they can be parallelized.
- No `if: always()` on test result upload — results lost on failure.
- Deploying without security scan — vulnerabilities reach production.
- `npm install` instead of `npm ci` in CI — `ci` is faster and deterministic.

## Gotchas

- GitHub Actions `services` only work on `ubuntu-latest` — not on macOS or Windows runners.
- `actions/cache` key must be unique per dependency lockfile — use `hashFiles()`.
- `GITHUB_TOKEN` permissions are read-only by default — set `permissions` explicitly.
- Matrix builds run in parallel — ensure tests don't share state.
- `if: github.ref == 'refs/heads/main'` — use for deploy-only steps.
- Docker build cache with `type=gha` requires `docker/setup-buildx-action`.

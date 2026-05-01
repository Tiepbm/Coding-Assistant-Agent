---
name: docker-containerization
description: 'Docker patterns: multi-stage Dockerfiles per stack, .dockerignore, layer caching, security, docker-compose for local dev.'
---
# Docker & Containerization Patterns

## Multi-Stage Dockerfile: Java (Spring Boot)

```dockerfile
# BAD: Single stage, JDK in production, no layer caching
FROM eclipse-temurin:21-jdk
COPY . /app
WORKDIR /app
RUN ./gradlew build
CMD ["java", "-jar", "build/libs/app.jar"]
# Image: ~800MB, includes build tools, source code, and JDK

# GOOD: Multi-stage, JRE only, layer caching
FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY gradle gradle
COPY gradlew build.gradle.kts settings.gradle.kts ./
RUN ./gradlew dependencies --no-daemon  # Cache dependencies layer
COPY src src
RUN ./gradlew bootJar --no-daemon

FROM eclipse-temurin:21-jre-alpine AS runtime
RUN addgroup -S app && adduser -S app -G app
USER app
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-XX:+UseContainerSupport", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]
# Image: ~200MB, JRE only, non-root user
```

## Multi-Stage Dockerfile: .NET

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY *.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine AS runtime
RUN addgroup -S app && adduser -S app -G app
USER app
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/health || exit 1
ENTRYPOINT ["dotnet", "MyApp.dll"]
```

## Multi-Stage Dockerfile: Node.js

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production=false

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build
RUN npm prune --production  # Remove devDependencies

FROM node:20-alpine AS runtime
RUN addgroup -S app && adduser -S app -G app
USER app
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/main.js"]
```

## Multi-Stage Dockerfile: Python

```dockerfile
FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt -o requirements.txt --without-hashes
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
RUN groupadd -r app && useradd -r -g app app
USER app
WORKDIR /app
COPY --from=build /install /usr/local
COPY . .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## .dockerignore

```
# Always include — prevents leaking secrets and bloating context
.git
.gitignore
node_modules
__pycache__
*.pyc
.env
.env.*
*.log
dist
build
target
bin
obj
.idea
.vscode
*.md
docker-compose*.yml
Dockerfile*
.dockerignore
tests
**/*.test.*
**/*.spec.*
coverage
.nyc_output
```

## Docker Compose for Local Development

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      target: build  # Use build stage for hot reload
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://app:secret@postgres:5432/appdb
      - REDIS_URL=redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src  # Hot reload
    develop:
      watch:
        - action: sync
          path: ./src
          target: /app/src

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret  # Local dev only
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d appdb"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

## Anti-Patterns

- **Running as root**: Always create and use a non-root user in production images.
- **Large images**: Using `jdk` instead of `jre`, `node` instead of `node-alpine`.
- **Secrets in layers**: `ENV API_KEY=secret` or `COPY .env .` — use runtime env vars or secrets.
- `COPY . .` before `RUN npm install` — invalidates dependency cache on every code change.
- No `.dockerignore` — sends `.git`, `node_modules`, secrets to build context.
- No `HEALTHCHECK` — orchestrator can't detect unhealthy containers.
- `latest` tag — unpredictable, use specific version tags.

## Gotchas

- Alpine images use `musl` libc — some native modules may not work (use `-slim` for Python).
- `--platform=linux/amd64` needed when building on Apple Silicon for x86 deployment.
- Docker layer cache is invalidated from the first changed layer downward — order matters.
- `ENTRYPOINT` vs `CMD`: ENTRYPOINT is the executable, CMD provides default arguments.
- `docker-compose` (v1) vs `docker compose` (v2) — use v2 (built into Docker CLI).
- Container memory limits: JVM needs `-XX:+UseContainerSupport` to respect cgroup limits.

---
name: devops-pack
description: 'Use when writing Dockerfiles, CI/CD pipelines, infrastructure-as-code, AWS service integrations, deployment scripts, or environment configuration.'
---
# DevOps Pack

## When to Use
- Writing or optimizing Dockerfiles and docker-compose configurations.
- CI/CD pipeline setup (GitHub Actions, GitLab CI, Jenkins).
- Infrastructure-as-code (Terraform, CDK, Docker Compose for local dev).
- AWS service integrations (S3, SQS, DynamoDB, Lambda, Secrets Manager, CDK).
- Deployment scripts and environment configuration.
- Secret management in CI/CD and runtime.

## When NOT to Use
- Application code that runs inside containers → `backend-pack` or `frontend-pack`.
- Database schema migrations → `database-pack`.
- Performance profiling of deployed services → `debugging-pack`.
- Security review of deployment config → `quality-pack/security-coding`.
- DynamoDB access patterns (data modeling) → `database-pack/nosql-patterns`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `docker-containerization` | Dockerfiles (multi-stage), .dockerignore, docker-compose, image security. |
| `ci-cd-pipelines` | GitHub Actions workflows, build/test/deploy stages, secret management, matrix builds. |
| `infrastructure-as-code` | Terraform basics, Docker Compose for local dev, environment-specific config. |
| `aws-services` | AWS SDK patterns (S3, SQS, DynamoDB, Lambda, Secrets Manager), CDK stacks, IAM least-privilege. |

## Cross-Pack Handoffs
- → `backend-pack` for application code and configuration.
- → `testing-pack` for CI test configuration and Testcontainers setup.
- → `quality-pack` for security scanning in CI pipeline.
- → `database-pack` for migration scripts run during deployment, DynamoDB data modeling.
- → `debugging-pack` for container and infrastructure troubleshooting.
- → `observability-pack` for shipping collector configs and dashboards-as-code.

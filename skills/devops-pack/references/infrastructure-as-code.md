---
name: infrastructure-as-code
description: 'IaC patterns: Terraform basics (providers, resources, modules, state), Docker Compose for local dev, environment-specific config.'
---
# Infrastructure as Code Patterns

## Terraform Basics

```hcl
# BAD: Hardcoded values, no variables, no state management
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t3.large"  # Hardcoded, same for all environments
  tags = { Name = "production-web" }
}

# GOOD: Variables, locals, proper naming
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "myapp-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

locals {
  name_prefix = "myapp-${var.environment}"
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = "myapp"
  }
}
```

## Terraform: Resources and Modules

```hcl
# modules/database/main.tf
resource "aws_db_instance" "main" {
  identifier     = "${var.name_prefix}-db"
  engine         = "postgres"
  engine_version = "16.1"
  instance_class = var.instance_class

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password  # From secrets manager, not hardcoded

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = var.environment == "prod" ? 30 : 7
  deletion_protection     = var.environment == "prod"
  skip_final_snapshot     = var.environment != "prod"

  tags = var.common_tags
}

# modules/database/variables.tf
variable "name_prefix" { type = string }
variable "environment" { type = string }
variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}
variable "db_name" { type = string }
variable "db_username" { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "allocated_storage" {
  type    = number
  default = 20
}
variable "max_allocated_storage" {
  type    = number
  default = 100
}
variable "common_tags" {
  type    = map(string)
  default = {}
}

# Usage in root module
module "database" {
  source = "./modules/database"

  name_prefix           = local.name_prefix
  environment           = var.environment
  instance_class        = var.environment == "prod" ? "db.r6g.large" : "db.t3.micro"
  db_name               = "appdb"
  db_username           = "app"
  db_password           = data.aws_secretsmanager_secret_version.db_password.secret_string
  allocated_storage     = var.environment == "prod" ? 100 : 20
  max_allocated_storage = var.environment == "prod" ? 500 : 50
  common_tags           = local.common_tags
}
```

## Environment-Specific Configuration

```hcl
# environments/dev.tfvars
environment    = "dev"
instance_type  = "t3.micro"
min_capacity   = 1
max_capacity   = 2
enable_waf     = false

# environments/prod.tfvars
environment    = "prod"
instance_type  = "t3.large"
min_capacity   = 3
max_capacity   = 10
enable_waf     = true

# Apply with:
# terraform apply -var-file=environments/dev.tfvars
# terraform apply -var-file=environments/prod.tfvars
```

## Application Configuration per Environment

```yaml
# BAD: Hardcoded config in code
database_url = "postgresql://user:pass@prod-db:5432/app"

# GOOD: Environment variables with validation at startup
```

```typescript
// config.ts — validate all config at startup, fail fast
import { z } from 'zod';

const ConfigSchema = z.object({
  NODE_ENV: z.enum(['development', 'staging', 'production']),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  REDIS_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
});

export const config = ConfigSchema.parse(process.env);
// Throws at startup if any required config is missing
```

```python
# Python: pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    environment: str = "development"
    database_url: str
    redis_url: str
    jwt_secret: str
    log_level: str = "info"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()  # Validates at import time
```

## Docker Compose: Multi-Environment

```yaml
# docker-compose.yml (base)
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://app:secret@postgres:5432/appdb
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
      interval: 5s

# docker-compose.override.yml (local dev — auto-loaded)
services:
  app:
    build:
      target: build
    volumes:
      - ./src:/app/src
    ports:
      - "8080:8080"
      - "5005:5005"  # Debug port

  postgres:
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: secret

# docker-compose.test.yml (CI)
services:
  app:
    build:
      target: runtime
    environment:
      - NODE_ENV=test
```

## Anti-Patterns

- **Manual infrastructure**: Clicking in AWS Console instead of using Terraform.
- **Hardcoded values**: IP addresses, passwords, AMI IDs in Terraform code.
- Terraform state in local file — use remote backend (S3, GCS) with locking.
- No `terraform plan` before `apply` — always review changes.
- Secrets in `.tfvars` files committed to git — use secrets manager.
- Single Terraform state for all environments — separate state per environment.
- No `deletion_protection` on production databases.

## Gotchas

- `terraform destroy` is irreversible — always use `deletion_protection` on critical resources.
- Terraform state contains secrets in plaintext — encrypt the state backend.
- `terraform plan` output can be misleading — `~` means update, `-/+` means destroy and recreate.
- Docker Compose `depends_on` doesn't wait for app readiness — use `healthcheck` + `condition`.
- Environment variables in Docker: `ENV` in Dockerfile bakes into image, `-e` at runtime is dynamic.
- Terraform `count` vs `for_each`: prefer `for_each` — `count` index shifts cause recreation.

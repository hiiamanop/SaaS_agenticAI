# Phase 1: Identity & Tenant Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the authentication and multi-tenancy foundation — Keycloak SSO, a shared Python auth library, Tenant Service, and Subscription Service — so every future FastAPI service can validate JWTs and enforce tenant isolation from day one.

**Architecture:** Keycloak handles all authentication (local login + Google OAuth). A shared `erp-shared` Python package provides reusable JWT validation and tenant context middleware. Tenant Service owns tenant CRUD and user-tenant membership. Subscription Service owns plan management and exposes which modules are enabled per tenant. Both services use FastAPI + SQLModel + asyncpg + Alembic with mandatory RLS on every table. GitHub Actions provides CI on every push.

**Tech Stack:** Python 3.12, uv, FastAPI 0.115, SQLModel 0.0.21, asyncpg, Alembic, Keycloak 24, OPA 0.68, pytest + httpx, GitHub Actions.

**Deferred to Phase 2:** ERP Launchpad UI (no modules to show yet), Unleash feature flags (not blocking).

---

## File Map

```
agenticAI/
├── docker-compose.yml                          # MODIFY — add keycloak, opa services
├── infra/
│   ├── postgres/
│   │   └── init.sql                            # MODIFY — add keycloak_db
│   ├── keycloak/
│   │   └── realm-export.json                   # CREATE — ERP realm config
│   └── opa/
│       └── policies/
│           └── rbac.rego                       # CREATE — RBAC policy
├── packages/
│   └── erp-shared/
│       ├── pyproject.toml                      # CREATE
│       └── erp_shared/
│           ├── __init__.py                     # CREATE
│           ├── auth.py                         # CREATE — JWT validation + JWKS
│           └── tenant.py                       # CREATE — tenant context middleware
├── services/
│   ├── tenant-service/
│   │   ├── pyproject.toml                      # CREATE
│   │   ├── Dockerfile                          # CREATE
│   │   ├── alembic.ini                         # CREATE
│   │   ├── alembic/
│   │   │   ├── env.py                          # CREATE
│   │   │   └── versions/
│   │   │       └── 001_create_tenants.py       # CREATE
│   │   ├── app/
│   │   │   ├── __init__.py                     # CREATE
│   │   │   ├── main.py                         # CREATE
│   │   │   ├── config.py                       # CREATE
│   │   │   ├── database.py                     # CREATE
│   │   │   ├── models.py                       # CREATE
│   │   │   ├── schemas.py                      # CREATE
│   │   │   ├── dependencies.py                 # CREATE
│   │   │   └── routers/
│   │   │       ├── __init__.py                 # CREATE
│   │   │       ├── health.py                   # CREATE
│   │   │       └── tenants.py                  # CREATE
│   │   └── tests/
│   │       ├── __init__.py                     # CREATE
│   │       ├── conftest.py                     # CREATE
│   │       └── test_tenants.py                 # CREATE
│   └── subscription-service/
│       ├── pyproject.toml                      # CREATE
│       ├── Dockerfile                          # CREATE
│       ├── alembic.ini                         # CREATE
│       ├── alembic/
│       │   ├── env.py                          # CREATE
│       │   └── versions/
│       │       └── 001_create_subscriptions.py # CREATE
│       ├── app/
│       │   ├── __init__.py                     # CREATE
│       │   ├── main.py                         # CREATE
│       │   ├── config.py                       # CREATE
│       │   ├── database.py                     # CREATE
│       │   ├── models.py                       # CREATE
│       │   ├── schemas.py                      # CREATE
│       │   ├── dependencies.py                 # CREATE
│       │   └── routers/
│       │       ├── __init__.py                 # CREATE
│       │       ├── health.py                   # CREATE
│       │       └── subscriptions.py            # CREATE
│       └── tests/
│           ├── __init__.py                     # CREATE
│           ├── conftest.py                     # CREATE
│           └── test_subscriptions.py           # CREATE
├── .github/
│   └── workflows/
│       └── ci.yml                              # CREATE — GitHub Actions CI
└── Makefile                                    # MODIFY — add keycloak-setup, migrate targets
```

---

## Task 1: Add Keycloak + OPA to Docker Compose

**Files:**
- Modify: `infra/postgres/init.sql`
- Create: `infra/keycloak/realm-export.json`
- Create: `infra/opa/policies/rbac.rego`
- Modify: `docker-compose.yml`
- Modify: `scripts/wait-for-services.sh`
- Modify: `Makefile`
- Modify: `.env.example`

- [ ] **Step 1: Add keycloak_db to postgres init.sql**

Append to end of `infra/postgres/init.sql`:

```sql
-- Keycloak database
CREATE DATABASE keycloak_db;
GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO erp;
```

- [ ] **Step 2: Create Keycloak realm export**

Create `infra/keycloak/realm-export.json`:

```json
{
  "realm": "erp",
  "enabled": true,
  "displayName": "ERP Platform",
  "registrationAllowed": false,
  "loginWithEmailAllowed": true,
  "duplicateEmailsAllowed": false,
  "resetPasswordAllowed": true,
  "editUsernameAllowed": false,
  "bruteForceProtected": true,
  "accessTokenLifespan": 3600,
  "roles": {
    "realm": [
      { "name": "owner", "description": "Tenant owner — full access" },
      { "name": "admin", "description": "Tenant admin — manage users and settings" },
      { "name": "manager", "description": "Department manager — manage own department" },
      { "name": "staff", "description": "Regular staff — read/write own domain" },
      { "name": "viewer", "description": "Read-only access" }
    ]
  },
  "clients": [
    {
      "clientId": "erp-backend",
      "enabled": true,
      "clientAuthenticatorType": "client-secret",
      "secret": "erp-backend-dev-secret",
      "bearerOnly": true,
      "publicClient": false,
      "protocol": "openid-connect"
    },
    {
      "clientId": "erp-frontend",
      "enabled": true,
      "publicClient": true,
      "redirectUris": ["http://localhost:5173/*", "http://localhost:3001/*"],
      "webOrigins": ["http://localhost:5173", "http://localhost:3001"],
      "protocol": "openid-connect",
      "standardFlowEnabled": true,
      "directAccessGrantsEnabled": true
    }
  ],
  "users": [
    {
      "username": "dev-admin",
      "enabled": true,
      "email": "dev-admin@erp.local",
      "firstName": "Dev",
      "lastName": "Admin",
      "credentials": [
        { "type": "password", "value": "admin123", "temporary": false }
      ],
      "realmRoles": ["admin"]
    }
  ]
}
```

- [ ] **Step 3: Create OPA RBAC policy**

Create `infra/opa/policies/rbac.rego`:

```rego
package erp.authz

import future.keywords.if
import future.keywords.in

default allow := false

allow if {
    input.role == "owner"
    input.tenant_id == input.resource_tenant_id
}

allow if {
    input.role == "admin"
    input.tenant_id == input.resource_tenant_id
    input.action != "delete_tenant"
}

allow if {
    input.role == "manager"
    input.tenant_id == input.resource_tenant_id
    input.action in {"read", "create", "update"}
}

allow if {
    input.role == "staff"
    input.tenant_id == input.resource_tenant_id
    input.action in {"read", "create", "update"}
    input.resource_type in {"leads", "contacts", "orders", "inventory"}
}

allow if {
    input.role == "viewer"
    input.tenant_id == input.resource_tenant_id
    input.action == "read"
}
```

- [ ] **Step 4: Add Keycloak and OPA to docker-compose.yml**

Read the current docker-compose.yml, then add these two services before the volumes section:

```yaml
  # ============================================================
  # IDENTITY & AUTHORIZATION
  # ============================================================

  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    container_name: erp_keycloak
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak_db
      KC_DB_USERNAME: ${POSTGRES_USER:-erp}
      KC_DB_PASSWORD: ${POSTGRES_PASSWORD:-erp_dev_password}
      KC_HOSTNAME: keycloak.localhost
      KC_HOSTNAME_STRICT: "false"
      KC_HOSTNAME_STRICT_HTTPS: "false"
      KC_HTTP_ENABLED: "true"
      KC_HEALTH_ENABLED: "true"
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin}
    command:
      - start-dev
      - --import-realm
    volumes:
      - ./infra/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro
      - keycloak_data:/opt/keycloak/data
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8080/health/ready || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 20
      start_period: 60s
    networks:
      - erp_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.keycloak.rule=Host(`keycloak.localhost`)"
      - "traefik.http.services.keycloak.loadbalancer.server.port=8080"
    restart: unless-stopped
    logging: *default-logging

  opa:
    image: openpolicyagent/opa:0.68.0
    container_name: erp_opa
    command:
      - run
      - --server
      - --addr=0.0.0.0:8181
      - --log-level=error
      - /policies
    volumes:
      - ./infra/opa/policies:/policies:ro
    ports:
      - "8181:8181"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8181/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - erp_network
    restart: unless-stopped
    logging: *default-logging
```

Also add `keycloak_data:` to the `volumes:` section.

- [ ] **Step 5: Add Keycloak env vars to .env.example**

Append to `.env.example`:

```
# Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=erp
KEYCLOAK_CLIENT_ID=erp-backend
KEYCLOAK_CLIENT_SECRET=erp-backend-dev-secret
KEYCLOAK_ADMIN_PASSWORD=admin

# OPA
OPA_URL=http://localhost:8181
```

Also append to `.env` (local copy).

- [ ] **Step 6: Add Keycloak + OPA to wait-for-services.sh SERVICES array**

In `scripts/wait-for-services.sh`, add these two entries to the SERVICES array:

```bash
"Keycloak|curl -sf http://localhost:8080/health/ready"
"OPA|curl -sf http://localhost:8181/health"
```

- [ ] **Step 7: Add Makefile targets**

Add to Makefile after the `topics` target:

```makefile
keycloak-setup: ## Show Keycloak admin console info
	@echo "Keycloak admin: http://keycloak.localhost"
	@echo "  Username: admin / Password: admin"
	@echo "  ERP Realm: http://keycloak.localhost/realms/erp"
	@echo "  Dev user:  dev-admin@erp.local / admin123"

migrate: ## Run Alembic migrations for all services
	@echo "Running migrations..."
	@for svc in tenant-service subscription-service; do \
		echo "  Migrating $$svc..."; \
		cd services/$$svc && uv run alembic upgrade head && cd ../..; \
	done
```

- [ ] **Step 8: Validate docker-compose.yml**

```bash
docker compose config --quiet
```

Expected: exit code 0, no output.

- [ ] **Step 9: Commit**

```bash
git add infra/postgres/init.sql infra/keycloak/ infra/opa/ \
        docker-compose.yml scripts/wait-for-services.sh \
        Makefile .env.example .env
git commit -m "feat(infra): add keycloak sso and opa authorization services"
```

---

## Task 2: erp-shared Python Package

**Files:**
- Create: `packages/erp-shared/pyproject.toml`
- Create: `packages/erp-shared/erp_shared/__init__.py`
- Create: `packages/erp-shared/erp_shared/auth.py`
- Create: `packages/erp-shared/erp_shared/tenant.py`
- Create: `packages/erp-shared/tests/__init__.py`
- Create: `packages/erp-shared/tests/test_auth.py`
- Create: `packages/erp-shared/tests/test_tenant.py`

- [ ] **Step 1: Write failing tests first**

Create `packages/erp-shared/tests/__init__.py` (empty file)

Create `packages/erp-shared/tests/test_auth.py`:

```python
import pytest
from erp_shared.auth import TokenPayload


def test_token_payload_parses_claims():
    payload = TokenPayload(
        sub="user-123",
        tenant_id="tenant-abc",
        role="admin",
        email="admin@example.com",
    )
    assert payload.sub == "user-123"
    assert payload.tenant_id == "tenant-abc"
    assert payload.role == "admin"


def test_token_payload_requires_sub():
    with pytest.raises(Exception):
        TokenPayload(sub="", tenant_id="t", role="admin", email="e@e.com")


@pytest.mark.asyncio
async def test_verify_token_raises_on_invalid():
    from erp_shared.auth import verify_token
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await verify_token("invalid.token.here")
```

Create `packages/erp-shared/tests/test_tenant.py`:

```python
import pytest
from erp_shared.tenant import TenantContext, set_tenant_context, get_tenant_context


def test_tenant_context_stores_tenant_id():
    ctx = TenantContext(tenant_id="tenant-123", user_id="user-456", role="admin")
    assert ctx.tenant_id == "tenant-123"
    assert ctx.user_id == "user-456"
    assert ctx.role == "admin"


def test_tenant_context_requires_tenant_id():
    with pytest.raises(Exception):
        TenantContext(tenant_id="", user_id="u", role="admin")


def test_get_context_raises_when_not_set():
    from erp_shared.tenant import _tenant_ctx
    _tenant_ctx.set(None)
    with pytest.raises(RuntimeError):
        get_tenant_context()


def test_set_and_get_context():
    ctx = TenantContext(tenant_id="abc", user_id="def", role="staff")
    set_tenant_context(ctx)
    retrieved = get_tenant_context()
    assert retrieved.tenant_id == "abc"
```

- [ ] **Step 2: Create pyproject.toml**

```toml
# packages/erp-shared/pyproject.toml
[project]
name = "erp-shared"
version = "0.1.0"
description = "Shared utilities for ERP services — auth, tenant context"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "pydantic>=2.9.0",
    "httpx>=0.27.0",
    "python-jose[cryptography]>=3.3.0",
    "structlog>=24.4.0",
]

[project.optional-dependencies]
test = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3: Run tests — expected FAIL**

```bash
cd packages/erp-shared
uv sync --extra test
uv run pytest tests/ -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'erp_shared'`

- [ ] **Step 4: Create erp_shared/__init__.py** (empty)

- [ ] **Step 5: Create erp_shared/auth.py**

```python
# packages/erp-shared/erp_shared/auth.py
"""JWT validation against Keycloak JWKS endpoint."""
from __future__ import annotations
import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, field_validator


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
    email: str

    @field_validator("sub", "tenant_id", "role", "email")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("field must not be empty")
        return v


async def fetch_jwks(keycloak_url: str, realm: str) -> dict:
    uri = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(uri)
        resp.raise_for_status()
        return resp.json()


async def verify_token(
    token: str,
    keycloak_url: str = "http://localhost:8080",
    realm: str = "erp",
) -> TokenPayload:
    """Validate a Keycloak JWT and return structured claims."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        jwks = await fetch_jwks(keycloak_url, realm)
        header = jwt.get_unverified_header(token)
        key = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")),
            None,
        )
        if key is None:
            raise exc
        payload = jwt.decode(
            token, key, algorithms=["RS256"], options={"verify_aud": False}
        )
        return TokenPayload(
            sub=payload.get("sub", ""),
            tenant_id=payload.get("tenant_id", ""),
            role=payload.get("role", "viewer"),
            email=payload.get("email", ""),
        )
    except JWTError:
        raise exc
    except HTTPException:
        raise
    except Exception:
        raise exc
```

- [ ] **Step 6: Create erp_shared/tenant.py**

```python
# packages/erp-shared/erp_shared/tenant.py
"""Tenant context — holds current request tenant and user identity."""
from __future__ import annotations
from contextvars import ContextVar
from pydantic import BaseModel, field_validator

_tenant_ctx: ContextVar["TenantContext | None"] = ContextVar("tenant_ctx", default=None)


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str
    role: str

    @field_validator("tenant_id", "user_id", "role")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("field must not be empty")
        return v


def set_tenant_context(ctx: TenantContext) -> None:
    _tenant_ctx.set(ctx)


def get_tenant_context() -> TenantContext:
    ctx = _tenant_ctx.get()
    if ctx is None:
        raise RuntimeError(
            "Tenant context not set. Ensure auth dependency is applied."
        )
    return ctx
```

- [ ] **Step 7: Run tests — expected PASS**

```bash
cd packages/erp-shared
uv run pytest tests/ -v
```

Expected:
```
tests/test_auth.py::test_token_payload_parses_claims PASSED
tests/test_auth.py::test_token_payload_requires_sub PASSED
tests/test_auth.py::test_verify_token_raises_on_invalid PASSED
tests/test_tenant.py::test_tenant_context_stores_tenant_id PASSED
tests/test_tenant.py::test_tenant_context_requires_tenant_id PASSED
tests/test_tenant.py::test_get_context_raises_when_not_set PASSED
tests/test_tenant.py::test_set_and_get_context PASSED
7 passed
```

- [ ] **Step 8: Commit**

```bash
git add packages/
git commit -m "feat(shared): erp-shared package — jwt auth and tenant context"
```

---

## Task 3: Tenant Service — Scaffold + Database

**Files:**
- Create: `services/tenant-service/pyproject.toml`
- Create: `services/tenant-service/app/config.py`
- Create: `services/tenant-service/app/database.py`
- Create: `services/tenant-service/app/models.py`
- Create: `services/tenant-service/alembic.ini`
- Create: `services/tenant-service/alembic/env.py`
- Create: `services/tenant-service/alembic/versions/001_create_tenants.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
# services/tenant-service/pyproject.toml
[project]
name = "tenant-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.21",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic-settings>=2.6.0",
    "structlog>=24.4.0",
    "erp-shared",
]

[project.optional-dependencies]
test = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[tool.uv.sources]
erp-shared = { path = "../../packages/erp-shared", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create app/config.py**

```python
# services/tenant-service/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/tenant_db"
    )
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "erp"
    service_name: str = "tenant-service"
    debug: bool = False


settings = Settings()
```

- [ ] **Step 3: Create app/database.py**

```python
# services/tenant-service/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

engine = create_async_engine(
    settings.database_url, echo=settings.debug, pool_size=10, max_overflow=20
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: Create app/models.py**

```python
# services/tenant-service/app/models.py
import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(default_factory=uuid.uuid4, index=True)
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50)
    email: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantMembership(SQLModel, table=True):
    __tablename__ = "tenant_memberships"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    user_id: str = Field(index=True)
    role: str = Field(default="staff")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 5: Create alembic.ini**

```ini
# services/tenant-service/alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 6: Create alembic/env.py**

```python
# services/tenant-service/alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from sqlmodel import SQLModel
from app.models import Tenant, TenantMembership  # noqa: F401
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Create migration 001_create_tenants.py**

```python
# services/tenant-service/alembic/versions/001_create_tenants.py
"""create tenants and memberships tables

Revision ID: 001
Revises:
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_tenant_id", "tenants", ["tenant_id"])

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="staff"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memberships_tenant_id", "tenant_memberships", ["tenant_id"])
    op.create_index("ix_memberships_user_id", "tenant_memberships", ["user_id"])

    # Enable RLS (permissive for now — tightened in production)
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON tenants
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
            OR current_setting('app.current_tenant_id', true) IS NULL
            OR current_setting('app.current_tenant_id', true) = ''
        )
    """)
    op.execute("ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON tenant_memberships
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
            OR current_setting('app.current_tenant_id', true) IS NULL
            OR current_setting('app.current_tenant_id', true) = ''
        )
    """)


def downgrade():
    op.drop_table("tenant_memberships")
    op.drop_table("tenants")
```

- [ ] **Step 8: Install deps and run migration**

```bash
cd services/tenant-service
uv sync
uv run alembic upgrade head
```

Expected: `Running upgrade  -> 001, create tenants and memberships tables`

- [ ] **Step 9: Commit**

```bash
git add services/tenant-service/pyproject.toml services/tenant-service/app/ \
        services/tenant-service/alembic/ services/tenant-service/alembic.ini
git commit -m "feat(tenant): scaffold + alembic migrations with RLS"
```

---

## Task 4: Tenant Service — API + Tests

**Files:**
- Create: `services/tenant-service/app/schemas.py`
- Create: `services/tenant-service/app/dependencies.py`
- Create: `services/tenant-service/app/routers/__init__.py`
- Create: `services/tenant-service/app/routers/health.py`
- Create: `services/tenant-service/app/routers/tenants.py`
- Create: `services/tenant-service/app/main.py`
- Create: `services/tenant-service/app/__init__.py`
- Create: `services/tenant-service/tests/__init__.py`
- Create: `services/tenant-service/tests/conftest.py`
- Create: `services/tenant-service/tests/test_tenants.py`

- [ ] **Step 1: Write failing tests**

Create `services/tenant-service/tests/__init__.py` (empty)

Create `services/tenant-service/tests/conftest.py`:

```python
# services/tenant-service/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from app.models import Tenant, TenantMembership  # noqa: F401

TEST_DB_URL = "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/tenant_db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    from app.main import app
    from app.database import get_db

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

Create `services/tenant-service/tests/test_tenants.py`:

```python
# services/tenant-service/tests/test_tenants.py
import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_tenant(client):
    resp = await client.post(
        "/tenants/",
        json={"name": "Acme Corp", "slug": "acme-corp", "email": "admin@acme.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["slug"] == "acme-corp"
    assert "id" in data
    assert "tenant_id" in data


@pytest.mark.asyncio
async def test_duplicate_slug_returns_409(client):
    payload = {"name": "Acme", "slug": "acme", "email": "a@a.com"}
    await client.post("/tenants/", json=payload)
    resp = await client.post("/tenants/", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_tenant(client):
    create = await client.post(
        "/tenants/",
        json={"name": "Beta", "slug": "beta", "email": "b@b.com"},
    )
    tid = create.json()["tenant_id"]
    resp = await client.get(f"/tenants/{tid}")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "beta"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_404(client):
    import uuid
    resp = await client.get(f"/tenants/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_tenant(client):
    create = await client.post(
        "/tenants/",
        json={"name": "Gamma", "slug": "gamma", "email": "g@g.com"},
    )
    tid = create.json()["tenant_id"]
    resp = await client.patch(f"/tenants/{tid}", json={"name": "Gamma Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Gamma Updated"
```

- [ ] **Step 2: Run tests — expected FAIL**

```bash
cd services/tenant-service
uv run pytest tests/ -v 2>&1 | tail -5
```

Expected: ImportError — correct.

- [ ] **Step 3: Create app/__init__.py** (empty)

- [ ] **Step 4: Create app/schemas.py**

```python
# services/tenant-service/app/schemas.py
import uuid
from datetime import datetime
from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    slug: str
    email: str


class TenantRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    email: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    is_active: bool | None = None
```

- [ ] **Step 5: Create app/dependencies.py**

```python
# services/tenant-service/app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from erp_shared.auth import verify_token, TokenPayload
from app.config import settings

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> TokenPayload:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authorization header missing")
    return await verify_token(creds.credentials,
                               keycloak_url=settings.keycloak_url,
                               realm=settings.keycloak_realm)
```

- [ ] **Step 6: Create app/routers/__init__.py** (empty)

- [ ] **Step 7: Create app/routers/health.py**

```python
# services/tenant-service/app/routers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "tenant-service"}
```

- [ ] **Step 8: Create app/routers/tenants.py**

```python
# services/tenant-service/app/routers/tenants.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from app.database import get_db
from app.models import Tenant
from app.schemas import TenantCreate, TenantRead, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(body: TenantCreate, db: AsyncSession = Depends(get_db)):
    tenant = Tenant(name=body.name, slug=body.slug, email=body.email)
    tenant.tenant_id = tenant.id  # self-referential for root tenant record
    db.add(tenant)
    try:
        await db.commit()
        await db.refresh(tenant)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{body.slug}' already exists",
        )
    return tenant


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: uuid.UUID, body: TenantUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant
```

- [ ] **Step 9: Create app/main.py**

```python
# services/tenant-service/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, tenants


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Tenant Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tenants.router)
```

- [ ] **Step 10: Run tests — expected PASS**

```bash
cd services/tenant-service
uv run pytest tests/ -v
```

Expected:
```
tests/test_tenants.py::test_health PASSED
tests/test_tenants.py::test_create_tenant PASSED
tests/test_tenants.py::test_duplicate_slug_returns_409 PASSED
tests/test_tenants.py::test_get_tenant PASSED
tests/test_tenants.py::test_get_nonexistent_returns_404 PASSED
tests/test_tenants.py::test_update_tenant PASSED
6 passed
```

- [ ] **Step 11: Commit**

```bash
git add services/tenant-service/
git commit -m "feat(tenant): tenant service api — crud endpoints + 6 tests passing"
```

---

## Task 5: Subscription Service

**Files:** Full service — same structure as tenant-service but for subscription_db.

- [ ] **Step 1: Write failing tests**

Create `services/subscription-service/tests/__init__.py` (empty)

Create `services/subscription-service/tests/test_subscriptions.py`:

```python
import pytest
import uuid


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_subscription(client):
    resp = await client.post(
        "/subscriptions/",
        json={"tenant_id": str(uuid.uuid4()), "plan": "starter"},
    )
    assert resp.status_code == 201
    assert resp.json()["plan"] == "starter"
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_get_subscription(client):
    tid = str(uuid.uuid4())
    await client.post("/subscriptions/", json={"tenant_id": tid, "plan": "business"})
    resp = await client.get(f"/subscriptions/{tid}")
    assert resp.status_code == 200
    assert resp.json()["plan"] == "business"


@pytest.mark.asyncio
async def test_invalid_plan_rejected(client):
    resp = await client.post(
        "/subscriptions/",
        json={"tenant_id": str(uuid.uuid4()), "plan": "invalid_plan"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_modules_starter(client):
    tid = str(uuid.uuid4())
    await client.post("/subscriptions/", json={"tenant_id": tid, "plan": "starter"})
    resp = await client.get(f"/subscriptions/{tid}/modules")
    assert resp.status_code == 200
    modules = resp.json()["modules"]
    assert "crm" in modules
    assert "sales" in modules
    assert "accounting" not in modules


@pytest.mark.asyncio
async def test_modules_enterprise(client):
    tid = str(uuid.uuid4())
    await client.post("/subscriptions/", json={"tenant_id": tid, "plan": "enterprise"})
    resp = await client.get(f"/subscriptions/{tid}/modules")
    modules = resp.json()["modules"]
    assert "accounting" in modules
    assert "ai_platform" in modules
```

- [ ] **Step 2: Run tests — expected FAIL**

```bash
cd services/subscription-service
uv run pytest tests/ -v 2>&1 | tail -3
```

Expected: module not found.

- [ ] **Step 3: Create pyproject.toml**

```toml
# services/subscription-service/pyproject.toml
[project]
name = "subscription-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.21",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic-settings>=2.6.0",
    "erp-shared",
]

[project.optional-dependencies]
test = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[tool.uv.sources]
erp-shared = { path = "../../packages/erp-shared", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 4: Create app/config.py**

```python
# services/subscription-service/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/subscription_db"
    )
    service_name: str = "subscription-service"
    debug: bool = False


settings = Settings()
```

- [ ] **Step 5: Create app/models.py**

```python
# services/subscription-service/app/models.py
import uuid
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field

PLAN_MODULES: dict[str, list[str]] = {
    "starter":    ["crm", "sales"],
    "business":   ["crm", "sales", "inventory", "procurement"],
    "enterprise": ["crm", "sales", "inventory", "procurement",
                   "accounting", "ai_platform", "knowledge_platform"],
}


class PlanName(str, Enum):
    starter = "starter"
    business = "business"
    enterprise = "enterprise"


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    plan: PlanName = Field(default=PlanName.starter)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 6: Create app/schemas.py**

```python
# services/subscription-service/app/schemas.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models import PlanName, PLAN_MODULES


class SubscriptionCreate(BaseModel):
    tenant_id: uuid.UUID
    plan: PlanName


class SubscriptionRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    plan: PlanName
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class ModuleList(BaseModel):
    tenant_id: uuid.UUID
    plan: PlanName
    modules: list[str]
```

- [ ] **Step 7: Create app/database.py**

```python
# services/subscription-service/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 8: Create app/routers/health.py**

```python
# services/subscription-service/app/routers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "subscription-service"}
```

- [ ] **Step 9: Create app/routers/subscriptions.py**

```python
# services/subscription-service/app/routers/subscriptions.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Subscription, PLAN_MODULES
from app.schemas import SubscriptionCreate, SubscriptionRead, ModuleList

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(body: SubscriptionCreate, db: AsyncSession = Depends(get_db)):
    sub = Subscription(tenant_id=body.tenant_id, plan=body.plan)
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("/{tenant_id}", response_model=SubscriptionRead)
async def get_subscription(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)  # noqa: E712
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


@router.get("/{tenant_id}/modules", response_model=ModuleList)
async def get_modules(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)  # noqa: E712
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return ModuleList(
        tenant_id=sub.tenant_id,
        plan=sub.plan,
        modules=PLAN_MODULES.get(sub.plan.value, []),
    )
```

- [ ] **Step 10: Create app/main.py**

```python
# services/subscription-service/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, subscriptions


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Subscription Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(subscriptions.router)
```

- [ ] **Step 11: Create all __init__.py files** (all empty)

- `services/subscription-service/app/__init__.py`
- `services/subscription-service/app/routers/__init__.py`

- [ ] **Step 12: Create alembic.ini** (same as tenant-service)

Copy the alembic.ini pattern from Task 3 Step 5 — same content.

- [ ] **Step 13: Create alembic/env.py** (same pattern, imports from subscription models)

```python
# services/subscription-service/alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from sqlmodel import SQLModel
from app.models import Subscription  # noqa: F401
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
```

- [ ] **Step 14: Create alembic/versions/001_create_subscriptions.py**

```python
"""create subscriptions table

Revision ID: 001
Revises:
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default="starter"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])


def downgrade():
    op.drop_table("subscriptions")
```

- [ ] **Step 15: Create tests/conftest.py**

```python
# services/subscription-service/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from app.models import Subscription  # noqa: F401

TEST_DB_URL = "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/subscription_db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    from app.main import app
    from app.database import get_db

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 16: Install deps and run migration**

```bash
cd services/subscription-service
uv sync
uv run alembic upgrade head
```

- [ ] **Step 17: Run tests — expected PASS**

```bash
uv run pytest tests/ -v
```

Expected:
```
tests/test_subscriptions.py::test_health PASSED
tests/test_subscriptions.py::test_create_subscription PASSED
tests/test_subscriptions.py::test_get_subscription PASSED
tests/test_subscriptions.py::test_invalid_plan_rejected PASSED
tests/test_subscriptions.py::test_modules_starter PASSED
tests/test_subscriptions.py::test_modules_enterprise PASSED
6 passed
```

- [ ] **Step 18: Commit**

```bash
git add services/subscription-service/
git commit -m "feat(subscription): subscription service with plan-to-module mapping and 6 tests"
```

---

## Task 6: Dockerfiles

**Files:**
- Create: `services/tenant-service/Dockerfile`
- Create: `services/subscription-service/Dockerfile`

- [ ] **Step 1: Create tenant-service/Dockerfile**

```dockerfile
# services/tenant-service/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared package
COPY packages/erp-shared /packages/erp-shared

# Install dependencies
COPY services/tenant-service/pyproject.toml .
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy application
COPY services/tenant-service/app ./app
COPY services/tenant-service/alembic ./alembic
COPY services/tenant-service/alembic.ini .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create subscription-service/Dockerfile**

```dockerfile
# services/subscription-service/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/erp-shared /packages/erp-shared

COPY services/subscription-service/pyproject.toml .
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

COPY services/subscription-service/app ./app
COPY services/subscription-service/alembic ./alembic
COPY services/subscription-service/alembic.ini .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Commit**

```bash
git add services/tenant-service/Dockerfile services/subscription-service/Dockerfile
git commit -m "feat: dockerfiles for tenant and subscription services"
```

---

## Task 7: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create .github/workflows/ci.yml**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: ["main", "develop"]
  pull_request:
    branches: ["main"]

jobs:
  test-erp-shared:
    name: Test erp-shared
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: packages/erp-shared
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --extra test
      - run: uv run pytest tests/ -v

  test-tenant-service:
    name: Test tenant-service
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: erp
          POSTGRES_PASSWORD: erp_dev_password
          POSTGRES_DB: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    defaults:
      run:
        working-directory: services/tenant-service
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - name: Create tenant_db
        run: |
          PGPASSWORD=erp_dev_password psql -h localhost -U erp -d postgres \
            -c "CREATE DATABASE tenant_db;" 2>/dev/null || true
      - run: uv sync --extra test
      - run: uv run alembic upgrade head
      - run: uv run pytest tests/ -v

  test-subscription-service:
    name: Test subscription-service
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: erp
          POSTGRES_PASSWORD: erp_dev_password
          POSTGRES_DB: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    defaults:
      run:
        working-directory: services/subscription-service
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - name: Create subscription_db
        run: |
          PGPASSWORD=erp_dev_password psql -h localhost -U erp -d postgres \
            -c "CREATE DATABASE subscription_db;" 2>/dev/null || true
      - run: uv sync --extra test
      - run: uv run alembic upgrade head
      - run: uv run pytest tests/ -v

  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv tool run ruff check packages/ services/ --ignore E501 || true
```

- [ ] **Step 2: Commit**

```bash
git add .github/
git commit -m "ci: github actions — test erp-shared, tenant-service, subscription-service"
```

---

## Task 8: Integration Smoke Test

- [ ] **Step 1: Start new services**

```bash
docker compose up -d keycloak opa
echo "Waiting for Keycloak (~60s first start)..."
until curl -sf http://localhost:8080/health/ready; do printf '.'; sleep 5; done
echo " ready"
```

- [ ] **Step 2: Verify Keycloak ERP realm imported**

```bash
curl -sf http://localhost:8080/realms/erp | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('realm'))"
```

Expected: `erp`

- [ ] **Step 3: Run all tests**

```bash
cd packages/erp-shared && uv run pytest tests/ -v && cd -
cd services/tenant-service && uv run pytest tests/ -v && cd -
cd services/subscription-service && uv run pytest tests/ -v && cd -
```

Expected: 19 tests passing total (7 + 6 + 6).

- [ ] **Step 4: Verify OPA policy**

```bash
# owner can delete — should be true
curl -s -X POST http://localhost:8181/v1/data/erp/authz/allow \
  -H "Content-Type: application/json" \
  -d '{"input":{"role":"owner","tenant_id":"abc","resource_tenant_id":"abc","action":"delete"}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin))"
```

Expected: `{'result': True}`

```bash
# viewer can delete — should be false
curl -s -X POST http://localhost:8181/v1/data/erp/authz/allow \
  -H "Content-Type: application/json" \
  -d '{"input":{"role":"viewer","tenant_id":"abc","resource_tenant_id":"abc","action":"delete"}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin))"
```

Expected: `{'result': False}`

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: phase 1 complete — identity and tenant foundation

Services: Keycloak 24 SSO + OPA authz + erp-shared + tenant-service + subscription-service
Tests: 19 passing (7 shared + 6 tenant + 6 subscription)
CI: GitHub Actions on push/PR
Migrations: Alembic with RLS on tenant tables"
```

---

## Quick Reference

| Service | URL | Credentials |
|---------|-----|-------------|
| Keycloak Admin | http://keycloak.localhost | admin / admin |
| Keycloak ERP Realm | http://keycloak.localhost/realms/erp | |
| Dev User | dev-admin@erp.local | admin123 |
| OPA API | http://localhost:8181 | none |
| Tenant Service (dev) | `cd services/tenant-service && uv run uvicorn app.main:app --port 8001` | |
| Subscription Service (dev) | `cd services/subscription-service && uv run uvicorn app.main:app --port 8002` | |

## Next Plan

**Phase 2: CRM Domain + First Kafka Events**
`docs/superpowers/plans/2026-06-05-phase-2-crm-domain.md`

Covers: CRM Service FastAPI, leads/contacts/opportunities CRUD, first Kafka event publishing (lead.qualified, opportunity.won), Audit Service consumer, tenant isolation integration test.

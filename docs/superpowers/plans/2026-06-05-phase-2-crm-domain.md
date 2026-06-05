# Phase 2: CRM Domain + First Kafka Events — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the CRM Service (leads, contacts, opportunities) with Kafka event publishing, and an Audit Service that consumes all events and persists them — proving the full event-driven loop works end-to-end, with tenant isolation validated by integration test.

**Architecture:** CRM Service is a FastAPI app with SQLModel + RLS (same pattern as tenant-service). When a lead is qualified or an opportunity is won, it publishes a CloudEvents-formatted message to Kafka via aiokafka. Audit Service is a FastAPI app with a background aiokafka consumer that writes every event to `audit_db`. Kafka producer is a singleton held in app lifespan. Tests mock the Kafka producer — no Redpanda required for unit tests.

**Tech Stack:** FastAPI, SQLModel, asyncpg, aiokafka 2.x, Alembic, erp-shared, pytest + httpx. Redpanda already running locally from Phase 0.

---

## File Map

```
services/
  crm-service/
    pyproject.toml                              # CREATE
    Dockerfile                                  # CREATE
    alembic.ini                                 # CREATE
    alembic/
      env.py                                    # CREATE
      versions/
        001_create_crm_tables.py                # CREATE
    app/
      __init__.py                               # CREATE
      main.py                                   # CREATE
      config.py                                 # CREATE
      database.py                               # CREATE
      models.py                                 # CREATE — Lead, Contact, Opportunity
      schemas.py                                # CREATE
      dependencies.py                           # CREATE
      events.py                                 # CREATE — Kafka publisher (CloudEvents)
      routers/
        __init__.py                             # CREATE
        health.py                               # CREATE
        leads.py                                # CREATE
        contacts.py                             # CREATE
        opportunities.py                        # CREATE
    tests/
      __init__.py                               # CREATE
      conftest.py                               # CREATE
      test_leads.py                             # CREATE
      test_contacts.py                          # CREATE
      test_opportunities.py                     # CREATE
      test_tenant_isolation.py                  # CREATE
  audit-service/
    pyproject.toml                              # CREATE
    Dockerfile                                  # CREATE
    alembic.ini                                 # CREATE
    alembic/
      env.py                                    # CREATE
      versions/
        001_create_audit_logs.py                # CREATE
    app/
      __init__.py                               # CREATE
      main.py                                   # CREATE — starts Kafka consumer as background task
      config.py                                 # CREATE
      database.py                               # CREATE
      models.py                                 # CREATE — AuditLog
      consumer.py                               # CREATE — aiokafka consumer loop
      routers/
        __init__.py                             # CREATE
        health.py                               # CREATE
    tests/
      __init__.py                               # CREATE
      conftest.py                               # CREATE
      test_audit_consumer.py                    # CREATE
.github/workflows/ci.yml                        # MODIFY — add crm-service and audit-service jobs
```

---

## Task 1: CRM Service — Scaffold + Models + Migrations

**Files:**
- Create: `services/crm-service/pyproject.toml`
- Create: `services/crm-service/app/config.py`
- Create: `services/crm-service/app/database.py`
- Create: `services/crm-service/app/models.py`
- Create: `services/crm-service/app/__init__.py`
- Create: `services/crm-service/alembic.ini`
- Create: `services/crm-service/alembic/env.py`
- Create: `services/crm-service/alembic/versions/001_create_crm_tables.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
# services/crm-service/pyproject.toml
[project]
name = "crm-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.21",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic-settings>=2.6.0",
    "aiokafka>=0.11.0",
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
# services/crm-service/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/crm_db"
    )
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "erp"
    kafka_brokers: str = "localhost:19092"
    service_name: str = "crm-service"
    debug: bool = False


settings = Settings()
```

- [ ] **Step 3: Create app/database.py**

```python
# services/crm-service/app/database.py
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
# services/crm-service/app/models.py
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class LeadStatus(str, Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    lost = "lost"


class Lead(SQLModel, table=True):
    __tablename__ = "leads"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    status: LeadStatus = Field(default=LeadStatus.new)
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Contact(SQLModel, table=True):
    __tablename__ = "contacts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OpportunityStage(str, Enum):
    prospect = "prospect"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class Opportunity(SQLModel, table=True):
    __tablename__ = "opportunities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    contact_id: Optional[uuid.UUID] = Field(default=None, index=True)
    title: str = Field(max_length=200)
    value: float = Field(default=0.0)
    stage: OpportunityStage = Field(default=OpportunityStage.prospect)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 5: Create app/__init__.py** (empty)

- [ ] **Step 6: Create alembic.ini**

```ini
# services/crm-service/alembic.ini
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

- [ ] **Step 7: Create alembic/env.py**

```python
# services/crm-service/alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from sqlmodel import SQLModel
from app.models import Lead, Contact, Opportunity  # noqa: F401
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
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
```

- [ ] **Step 8: Create alembic/versions/001_create_crm_tables.py**

```python
# services/crm-service/alembic/versions/001_create_crm_tables.py
"""create crm tables

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
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="new"),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])
    op.create_index("ix_leads_tenant_status", "leads", ["tenant_id", "status"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_tenant_id", "contacts", ["tenant_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stage", sa.String(), nullable=False, server_default="prospect"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_tenant_id", "opportunities", ["tenant_id"])
    op.create_index("ix_opportunities_contact_id", "opportunities", ["contact_id"])

    for table in ("leads", "contacts", "opportunities"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                tenant_id = current_setting('app.current_tenant_id', true)::uuid
                OR current_setting('app.current_tenant_id', true) IS NULL
                OR current_setting('app.current_tenant_id', true) = ''
            )
        """)


def downgrade():
    op.drop_table("opportunities")
    op.drop_table("contacts")
    op.drop_table("leads")
```

- [ ] **Step 9: Install deps and run migration**

```bash
cd services/crm-service
uv sync
uv run alembic upgrade head
```

Expected: `Running upgrade  -> 001, create crm tables`

- [ ] **Step 10: Commit**

```bash
git add services/crm-service/pyproject.toml services/crm-service/app/ \
        services/crm-service/alembic/ services/crm-service/alembic.ini
git commit -m "feat(crm): scaffold + alembic migrations with RLS for leads/contacts/opportunities"
```

---

## Task 2: CRM Service — Kafka Events Publisher

**Files:**
- Create: `services/crm-service/app/events.py`

- [ ] **Step 1: Create app/events.py**

```python
# services/crm-service/app/events.py
"""CloudEvents-formatted Kafka publisher for CRM domain."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC
from typing import Any

from aiokafka import AIOKafkaProducer
from app.config import settings

_producer: AIOKafkaProducer | None = None


async def start_producer() -> None:
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_brokers,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await _producer.start()


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def publish(topic: str, event_type: str, tenant_id: str, data: dict[str, Any]) -> None:
    """Publish a CloudEvents 1.0 message to Kafka. No-op if producer not started."""
    if _producer is None:
        return

    event = {
        "specversion": "1.0",
        "type": event_type,
        "source": "/services/crm",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "tenantid": tenant_id,
        "correlationid": str(uuid.uuid4()),
        "data": data,
    }
    await _producer.send_and_wait(
        topic,
        value=event,
        headers=[("tenantid", tenant_id.encode())],
    )
```

- [ ] **Step 2: Commit**

```bash
git add services/crm-service/app/events.py
git commit -m "feat(crm): kafka cloudEvents publisher"
```

---

## Task 3: CRM Service — API + Tests

**Files:**
- Create: `services/crm-service/app/schemas.py`
- Create: `services/crm-service/app/dependencies.py`
- Create: `services/crm-service/app/routers/__init__.py`
- Create: `services/crm-service/app/routers/health.py`
- Create: `services/crm-service/app/routers/leads.py`
- Create: `services/crm-service/app/routers/contacts.py`
- Create: `services/crm-service/app/routers/opportunities.py`
- Create: `services/crm-service/app/main.py`
- Create: `services/crm-service/tests/` (all test files)

- [ ] **Step 1: Write failing tests**

Create `services/crm-service/tests/__init__.py` (empty)

Create `services/crm-service/tests/conftest.py`:

```python
# services/crm-service/tests/conftest.py
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from app.models import Lead, Contact, Opportunity  # noqa: F401

TEST_DB_URL = "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/crm_db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()


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

    with patch("app.events._producer", new=AsyncMock()):
        app.dependency_overrides[get_db] = override
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
        app.dependency_overrides.clear()
```

Create `services/crm-service/tests/test_leads.py`:

```python
# services/crm-service/tests/test_leads.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_lead(client):
    resp = await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@acme.com",
        "company": "Acme Corp",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "John"
    assert data["status"] == "new"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_lead(client):
    create = await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@beta.com",
    })
    lead_id = create.json()["id"]
    resp = await client.get(f"/leads/{lead_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "jane@beta.com"


@pytest.mark.asyncio
async def test_list_leads_by_tenant(client):
    for i in range(3):
        await client.post("/leads/", json={
            "tenant_id": str(TENANT_A),
            "first_name": f"Lead{i}",
            "last_name": "Test",
            "email": f"lead{i}@test.com",
        })
    resp = await client.get(f"/leads/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_qualify_lead_publishes_event(client):
    create = await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Bob",
        "last_name": "Builder",
        "email": "bob@build.com",
    })
    lead_id = create.json()["id"]

    with patch("app.routers.leads.publish", new=AsyncMock()) as mock_publish:
        resp = await client.patch(f"/leads/{lead_id}", json={"status": "qualified"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "qualified"
        mock_publish.assert_awaited_once()
        assert mock_publish.call_args[0][0] == "crm.lead.qualified"


@pytest.mark.asyncio
async def test_get_nonexistent_lead_returns_404(client):
    resp = await client.get(f"/leads/{uuid.uuid4()}")
    assert resp.status_code == 404
```

Create `services/crm-service/tests/test_contacts.py`:

```python
# services/crm-service/tests/test_contacts.py
import pytest
import uuid
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_create_contact(client):
    resp = await client.post("/contacts/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Alice",
        "last_name": "Wonder",
        "email": "alice@wonder.com",
        "phone": "+62812345678",
    })
    assert resp.status_code == 201
    assert resp.json()["email"] == "alice@wonder.com"


@pytest.mark.asyncio
async def test_list_contacts(client):
    for i in range(2):
        await client.post("/contacts/", json={
            "tenant_id": str(TENANT_A),
            "first_name": f"Contact{i}",
            "last_name": "Test",
            "email": f"contact{i}@test.com",
        })
    resp = await client.get(f"/contacts/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_update_contact(client):
    create = await client.post("/contacts/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Charlie",
        "last_name": "Brown",
        "email": "charlie@brown.com",
    })
    cid = create.json()["id"]
    resp = await client.patch(f"/contacts/{cid}", json={"phone": "+628999"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+628999"


@pytest.mark.asyncio
async def test_get_nonexistent_contact_returns_404(client):
    resp = await client.get(f"/contacts/{uuid.uuid4()}")
    assert resp.status_code == 404
```

Create `services/crm-service/tests/test_opportunities.py`:

```python
# services/crm-service/tests/test_opportunities.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_create_opportunity(client):
    resp = await client.post("/opportunities/", json={
        "tenant_id": str(TENANT_A),
        "title": "Big Deal",
        "value": 50000000.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Big Deal"
    assert data["stage"] == "prospect"


@pytest.mark.asyncio
async def test_list_opportunities(client):
    for i in range(2):
        await client.post("/opportunities/", json={
            "tenant_id": str(TENANT_A),
            "title": f"Deal {i}",
            "value": float(i * 1000000),
        })
    resp = await client.get(f"/opportunities/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_win_opportunity_publishes_event(client):
    create = await client.post("/opportunities/", json={
        "tenant_id": str(TENANT_A),
        "title": "Win This Deal",
        "value": 100000000.0,
    })
    oid = create.json()["id"]

    with patch("app.routers.opportunities.publish", new=AsyncMock()) as mock_publish:
        resp = await client.patch(f"/opportunities/{oid}", json={"stage": "won"})
        assert resp.status_code == 200
        assert resp.json()["stage"] == "won"
        mock_publish.assert_awaited_once()
        assert mock_publish.call_args[0][0] == "crm.opportunity.won"


@pytest.mark.asyncio
async def test_get_nonexistent_opportunity_returns_404(client):
    resp = await client.get(f"/opportunities/{uuid.uuid4()}")
    assert resp.status_code == 404
```

Create `services/crm-service/tests/test_tenant_isolation.py`:

```python
# services/crm-service/tests/test_tenant_isolation.py
"""Critical: Tenant A must never see Tenant B data."""
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_leads_isolated_between_tenants(client):
    await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "TenantA", "last_name": "Lead", "email": "a@tenanta.com",
    })
    await client.post("/leads/", json={
        "tenant_id": str(TENANT_B),
        "first_name": "TenantB", "last_name": "Lead", "email": "b@tenantb.com",
    })

    resp_a = await client.get(f"/leads/?tenant_id={TENANT_A}")
    emails_a = [lead["email"] for lead in resp_a.json()]
    assert "a@tenanta.com" in emails_a
    assert "b@tenantb.com" not in emails_a

    resp_b = await client.get(f"/leads/?tenant_id={TENANT_B}")
    emails_b = [lead["email"] for lead in resp_b.json()]
    assert "b@tenantb.com" in emails_b
    assert "a@tenanta.com" not in emails_b


@pytest.mark.asyncio
async def test_contacts_isolated_between_tenants(client):
    await client.post("/contacts/", json={
        "tenant_id": str(TENANT_A), "first_name": "A", "last_name": "X", "email": "ax@a.com"
    })
    await client.post("/contacts/", json={
        "tenant_id": str(TENANT_B), "first_name": "B", "last_name": "Y", "email": "by@b.com"
    })

    resp_a = await client.get(f"/contacts/?tenant_id={TENANT_A}")
    emails_a = [c["email"] for c in resp_a.json()]
    assert "ax@a.com" in emails_a
    assert "by@b.com" not in emails_a
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
cd services/crm-service
uv run pytest tests/ -v 2>&1 | tail -5
```

Expected: ImportError — correct.

- [ ] **Step 3: Create app/schemas.py**

```python
# services/crm-service/app/schemas.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models import LeadStatus, OpportunityStage


class LeadCreate(BaseModel):
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None


class LeadRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    status: LeadStatus
    source: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[LeadStatus] = None
    source: Optional[str] = None


class ContactCreate(BaseModel):
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None


class ContactRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class OpportunityCreate(BaseModel):
    tenant_id: uuid.UUID
    title: str
    value: float = 0.0
    contact_id: Optional[uuid.UUID] = None


class OpportunityRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    contact_id: Optional[uuid.UUID]
    title: str
    value: float
    stage: OpportunityStage
    created_at: datetime
    model_config = {"from_attributes": True}


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[OpportunityStage] = None
    contact_id: Optional[uuid.UUID] = None
```

- [ ] **Step 4: Create app/dependencies.py**

```python
# services/crm-service/app/dependencies.py
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

- [ ] **Step 5: Create app/routers/__init__.py** (empty)

- [ ] **Step 6: Create app/routers/health.py**

```python
# services/crm-service/app/routers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "crm-service"}
```

- [ ] **Step 7: Create app/routers/leads.py**

```python
# services/crm-service/app/routers/leads.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Lead, LeadStatus
from app.schemas import LeadCreate, LeadRead, LeadUpdate
from app.events import publish

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(body: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = Lead(**body.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.get("/", response_model=list[LeadRead])
async def list_leads(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.tenant_id == tenant_id))
    return result.scalars().all()


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: uuid.UUID, body: LeadUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    prev_status = lead.status
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)

    await db.commit()
    await db.refresh(lead)

    if prev_status != LeadStatus.qualified and lead.status == LeadStatus.qualified:
        await publish(
            topic="crm.lead.qualified",
            event_type="crm.lead.qualified",
            tenant_id=str(lead.tenant_id),
            data={
                "lead_id": str(lead.id),
                "email": lead.email,
                "company": lead.company,
            },
        )

    return lead
```

- [ ] **Step 8: Create app/routers/contacts.py**

```python
# services/crm-service/app/routers/contacts.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Contact
from app.schemas import ContactCreate, ContactRead, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("/", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(body: ContactCreate, db: AsyncSession = Depends(get_db)):
    contact = Contact(**body.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/", response_model=list[ContactRead])
async def list_contacts(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.tenant_id == tenant_id))
    return result.scalars().all()


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(contact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: uuid.UUID, body: ContactUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact
```

- [ ] **Step 9: Create app/routers/opportunities.py**

```python
# services/crm-service/app/routers/opportunities.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Opportunity, OpportunityStage
from app.schemas import OpportunityCreate, OpportunityRead, OpportunityUpdate
from app.events import publish

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.post("/", response_model=OpportunityRead, status_code=status.HTTP_201_CREATED)
async def create_opportunity(body: OpportunityCreate, db: AsyncSession = Depends(get_db)):
    opp = Opportunity(**body.model_dump())
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


@router.get("/", response_model=list[OpportunityRead])
async def list_opportunities(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Opportunity).where(Opportunity.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.get("/{opp_id}", response_model=OpportunityRead)
async def get_opportunity(opp_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp


@router.patch("/{opp_id}", response_model=OpportunityRead)
async def update_opportunity(
    opp_id: uuid.UUID, body: OpportunityUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    prev_stage = opp.stage
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(opp, field, value)

    await db.commit()
    await db.refresh(opp)

    if prev_stage != OpportunityStage.won and opp.stage == OpportunityStage.won:
        await publish(
            topic="crm.opportunity.won",
            event_type="crm.opportunity.won",
            tenant_id=str(opp.tenant_id),
            data={
                "opportunity_id": str(opp.id),
                "title": opp.title,
                "value": opp.value,
                "contact_id": str(opp.contact_id) if opp.contact_id else None,
            },
        )

    return opp
```

- [ ] **Step 10: Create app/main.py**

```python
# services/crm-service/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.events import start_producer, stop_producer
from app.routers import health, leads, contacts, opportunities


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    yield
    await stop_producer()


app = FastAPI(title="CRM Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(leads.router)
app.include_router(contacts.router)
app.include_router(opportunities.router)
```

- [ ] **Step 11: Run tests — verify ALL 15 PASS**

```bash
cd services/crm-service
uv run pytest tests/ -v
```

Expected: 15 tests pass (5 leads + 4 contacts + 4 opportunities + 2 isolation). Fix any failures before committing.

- [ ] **Step 12: Commit**

```bash
git add services/crm-service/
git commit -m "feat(crm): crm service — leads/contacts/opportunities crud + kafka events + 15 tests"
```

---

## Task 4: Audit Service

**Files:** Full service — Kafka consumer that persists all events to audit_db.

- [ ] **Step 1: Create pyproject.toml**

```toml
# services/audit-service/pyproject.toml
[project]
name = "audit-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.21",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic-settings>=2.6.0",
    "aiokafka>=0.11.0",
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

- [ ] **Step 2: Write failing tests**

Create `services/audit-service/tests/__init__.py` (empty)

Create `services/audit-service/tests/conftest.py`:

```python
# services/audit-service/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from app.models import AuditLog  # noqa: F401

TEST_DB_URL = "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/audit_db"
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
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

Create `services/audit-service/tests/test_audit_consumer.py`:

```python
# services/audit-service/tests/test_audit_consumer.py
import pytest
import uuid
import json
from datetime import datetime, UTC
from sqlmodel import select
from app.models import AuditLog
from app.consumer import process_event


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_process_event_saves_to_db(db_session):
    event_payload = json.dumps({
        "specversion": "1.0",
        "type": "crm.lead.qualified",
        "source": "/services/crm",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "tenantid": str(uuid.uuid4()),
        "data": {"lead_id": str(uuid.uuid4()), "email": "test@test.com"},
    }).encode()

    await process_event("crm.lead.qualified", event_payload, db_session)
    await db_session.commit()

    result = await db_session.execute(select(AuditLog))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].event_type == "crm.lead.qualified"
    assert logs[0].topic == "crm.lead.qualified"


@pytest.mark.asyncio
async def test_process_malformed_event_does_not_crash(db_session):
    await process_event("crm.lead.qualified", b"not valid json", db_session)


@pytest.mark.asyncio
async def test_audit_log_stores_tenant_id(db_session):
    tenant_id = str(uuid.uuid4())
    event_payload = json.dumps({
        "specversion": "1.0",
        "type": "sales.order.created",
        "source": "/services/sales",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "tenantid": tenant_id,
        "data": {"order_id": "ord-001"},
    }).encode()

    await process_event("sales.order.created", event_payload, db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.tenant_id == tenant_id
```

- [ ] **Step 3: Run tests — verify FAIL**

```bash
cd services/audit-service
uv run pytest tests/ -v 2>&1 | tail -3
```

- [ ] **Step 4: Create app/config.py**

```python
# services/audit-service/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/audit_db"
    )
    kafka_brokers: str = "localhost:19092"
    kafka_group_id: str = "audit-service"
    kafka_topics: str = (
        "crm.lead.qualified,crm.opportunity.won,"
        "sales.order.created,sales.order.approved,"
        "inventory.stock.low,procurement.po.requested,procurement.po.approved,"
        "accounting.invoice.generated,accounting.payment.processed,"
        "approval.request.created,approval.request.approved,approval.request.rejected,"
        "agent.action.executed"
    )
    service_name: str = "audit-service"
    debug: bool = False


settings = Settings()
```

- [ ] **Step 5: Create app/models.py**

```python
# services/audit-service/app/models.py
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: str = Field(index=True)
    event_type: str = Field(index=True)
    topic: str
    tenant_id: Optional[str] = Field(default=None, index=True)
    source: Optional[str] = None
    payload: str
    received_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 6: Create app/database.py**

```python
# services/audit-service/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 7: Create app/consumer.py**

```python
# services/audit-service/app/consumer.py
"""Kafka consumer — persists every event to audit_logs."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from aiokafka import AIOKafkaConsumer

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import AuditLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def process_event(topic: str, payload: bytes, db: "AsyncSession") -> None:
    """Parse one Kafka message and write to audit_logs. Never raises."""
    try:
        data = json.loads(payload.decode())
        log = AuditLog(
            event_id=data.get("id", "unknown"),
            event_type=data.get("type", topic),
            topic=topic,
            tenant_id=data.get("tenantid"),
            source=data.get("source"),
            payload=payload.decode(),
        )
        db.add(log)
    except Exception as exc:
        logger.warning("audit: failed to parse event on %s: %s", topic, exc)


async def run_consumer() -> None:
    """Long-running Kafka consumer loop. Runs as background task."""
    topics = [t.strip() for t in settings.kafka_topics.split(",") if t.strip()]
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_brokers,
        group_id=settings.kafka_group_id,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            async with AsyncSessionLocal() as db:
                await process_event(msg.topic, msg.value, db)
                await db.commit()
    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()
```

- [ ] **Step 8: Create app/routers/health.py**

```python
# services/audit-service/app/routers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "audit-service"}
```

- [ ] **Step 9: Create app/main.py**

```python
# services/audit-service/app/main.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.consumer import run_consumer
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_consumer())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Audit Service", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
```

- [ ] **Step 10: Create app/__init__.py and app/routers/__init__.py** (both empty)

- [ ] **Step 11: Create alembic.ini** (same pattern as other services)

```ini
# services/audit-service/alembic.ini
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

- [ ] **Step 12: Create alembic/env.py**

```python
# services/audit-service/alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from sqlmodel import SQLModel
from app.models import AuditLog  # noqa: F401
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
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
```

- [ ] **Step 13: Create alembic/versions/001_create_audit_logs.py**

```python
# services/audit-service/alembic/versions/001_create_audit_logs.py
"""create audit_logs table

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
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_event_id", "audit_logs", ["event_id"])


def downgrade():
    op.drop_table("audit_logs")
```

- [ ] **Step 14: Install deps and run migration**

```bash
cd services/audit-service
uv sync
uv run alembic upgrade head
```

- [ ] **Step 15: Run tests — verify ALL 4 PASS**

```bash
uv run pytest tests/ -v
```

Expected:
```
tests/test_audit_consumer.py::test_health PASSED
tests/test_audit_consumer.py::test_process_event_saves_to_db PASSED
tests/test_audit_consumer.py::test_process_malformed_event_does_not_crash PASSED
tests/test_audit_consumer.py::test_audit_log_stores_tenant_id PASSED
4 passed
```

- [ ] **Step 16: Commit**

```bash
git add services/audit-service/
git commit -m "feat(audit): audit service — kafka consumer persists all events to audit_db"
```

---

## Task 5: Dockerfiles + CI Update

**Files:**
- Create: `services/crm-service/Dockerfile`
- Create: `services/audit-service/Dockerfile`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Create services/crm-service/Dockerfile**

```dockerfile
# services/crm-service/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/erp-shared /packages/erp-shared
COPY services/crm-service/pyproject.toml .
RUN uv sync --no-dev 2>/dev/null || uv sync --no-dev --no-frozen

COPY services/crm-service/app ./app
COPY services/crm-service/alembic ./alembic
COPY services/crm-service/alembic.ini .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create services/audit-service/Dockerfile**

```dockerfile
# services/audit-service/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/erp-shared /packages/erp-shared
COPY services/audit-service/pyproject.toml .
RUN uv sync --no-dev 2>/dev/null || uv sync --no-dev --no-frozen

COPY services/audit-service/app ./app
COPY services/audit-service/alembic ./alembic
COPY services/audit-service/alembic.ini .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Add crm-service and audit-service jobs to .github/workflows/ci.yml**

Read `.github/workflows/ci.yml` first. Add these two jobs BEFORE the existing `lint` job:

```yaml
  test-crm-service:
    name: Test crm-service
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
        working-directory: services/crm-service
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - name: Create crm_db
        run: |
          PGPASSWORD=erp_dev_password psql -h localhost -U erp -d postgres \
            -c "CREATE DATABASE crm_db;" 2>/dev/null || true
      - run: uv sync --extra test
      - run: uv run alembic upgrade head
      - run: uv run pytest tests/ -v

  test-audit-service:
    name: Test audit-service
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
        working-directory: services/audit-service
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - name: Create audit_db
        run: |
          PGPASSWORD=erp_dev_password psql -h localhost -U erp -d postgres \
            -c "CREATE DATABASE audit_db;" 2>/dev/null || true
      - run: uv sync --extra test
      - run: uv run alembic upgrade head
      - run: uv run pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add services/crm-service/Dockerfile services/audit-service/Dockerfile \
        .github/workflows/ci.yml
git commit -m "feat: dockerfiles for crm/audit + ci jobs for phase 2 services"
```

---

## Task 6: End-to-End Smoke Test

- [ ] **Step 1: Run all 38 tests**

```bash
cd packages/erp-shared && uv run pytest tests/ -q && cd -
cd services/tenant-service && uv run pytest tests/ -q && cd -
cd services/subscription-service && uv run pytest tests/ -q && cd -
cd services/crm-service && uv run pytest tests/ -q && cd -
cd services/audit-service && uv run pytest tests/ -q && cd -
```

Expected: `7 + 6 + 6 + 15 + 4 = 38 passed`

- [ ] **Step 2: Start CRM Service and verify Kafka event**

```bash
cd services/crm-service
uv run uvicorn app.main:app --port 8001 --reload &
sleep 3

# Create + qualify a lead
LEAD_ID=$(curl -s -X POST http://localhost:8001/leads/ \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"00000000-0000-0000-0000-000000000001","first_name":"Ahmad","last_name":"Test","email":"ahmad@meetsin.id","company":"Meetsin.Id"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X PATCH http://localhost:8001/leads/$LEAD_ID \
  -H "Content-Type: application/json" \
  -d '{"status":"qualified"}' | python3 -m json.tool
```

- [ ] **Step 3: Verify event in Redpanda Console**

Open: http://redpanda.localhost → Topics → `crm.lead.qualified`

Expected: 1 message with CloudEvents JSON, `tenantid` header present.

- [ ] **Step 4: Stop and final commit**

```bash
kill %1
git add .
git commit -m "chore: phase 2 complete — crm domain + kafka events + audit service

Services: crm-service (leads/contacts/opportunities) + audit-service (kafka consumer)
Tests: 38 total passing (7+6+6+15+4)
Events: crm.lead.qualified, crm.opportunity.won published as CloudEvents 1.0
Audit: all events persisted to audit_db via background consumer"
```

- [ ] **Step 5: Push to GitHub**

```bash
git push origin master
```

---

## Quick Reference

```bash
# CRM Service (port 8001)
cd services/crm-service && uv run uvicorn app.main:app --port 8001 --reload

# Audit Service (port 8002)
cd services/audit-service && uv run uvicorn app.main:app --port 8002 --reload

# API docs
open http://localhost:8001/docs
open http://localhost:8002/docs
```

## Next Plan

**Phase 3: Sales + Inventory + Core Business Platform**
`docs/superpowers/plans/2026-06-05-phase-3-core-business.md`

Covers: Sales Service (quotations/orders), Inventory Service (stock/warehouses), cross-domain Kafka event flow (`sales.order.created` → `inventory.stock.reserved`).

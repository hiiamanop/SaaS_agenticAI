# services/audit-service/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from app.models import AuditLog  # noqa: F401

TEST_DB_URL = "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/audit_db"

# Module level engine and session factory - reused across tests
test_engine = create_async_engine(
    TEST_DB_URL, echo=False, poolclass=NullPool
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session(reset_db):
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

# services/agent-service/tests/conftest.py
import uuid

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from app.config import settings
from app.models import AgentRecommendation, AgentActionLog  # noqa: F401

TEST_DB_URL = "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/agent_db"

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True)
def force_mock_provider():
    """Tests/CI must never reach a real LLM — pin the deterministic mock
    regardless of the runtime default (which is ``ollama``)."""
    original = settings.model_provider
    settings.model_provider = "mock"
    yield
    settings.model_provider = original


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    await engine.dispose()
    yield


@pytest_asyncio.fixture
async def db_session(reset_db):
    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


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

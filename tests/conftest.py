import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import queue
from app.core.database import Base, get_session
from app.main import app

TEST_DB = "postgresql+asyncpg://scheduler:scheduler@localhost:5432/test_scheduler"
TEST_REDIS = "redis://localhost:6379/1"  # DB 1 — isolated from dev

test_engine = create_async_engine(TEST_DB)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    await test_engine.dispose()
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE jobs CASCADE"))

    test_redis = Redis.from_url(TEST_REDIS, decode_responses=True)
    await test_redis.flushdb()
    queue._redis = test_redis  # point queue module at isolated test Redis

    async def override_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    await test_redis.aclose()
    app.dependency_overrides.clear()

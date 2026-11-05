import os
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from harvest_edge.api.dependencies import get_session
from harvest_edge.core.security import generate_api_key
from harvest_edge.main import app
from harvest_edge.models import ApiKey, Base


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-db-tests",
        action="store_true",
        default=False,
        help="Run database integration tests and fail if the test database URL is missing",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    if session.config.getoption("--run-db-tests") and not (
        os.getenv("HARVEST_EDGE_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    ):
        raise pytest.UsageError(
            "--run-db-tests requires HARVEST_EDGE_TEST_DATABASE_URL or TEST_DATABASE_URL"
        )


ApiKeyFactory = Callable[..., Awaitable[str]]


@pytest.fixture
async def test_db() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    database_url = os.getenv("HARVEST_EDGE_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set HARVEST_EDGE_TEST_DATABASE_URL or TEST_DATABASE_URL for API tests")

    schema = f"test_auth_{uuid4().hex}"
    admin_engine = create_async_engine(database_url)
    async with admin_engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    test_engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"search_path": f"{schema},public"}},
        execution_options={"schema_translate_map": {None: schema}},
    )
    try:
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield async_sessionmaker(test_engine, expire_on_commit=False)
    finally:
        await test_engine.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


@pytest.fixture
async def api_key_factory(
    test_db: async_sessionmaker[AsyncSession],
) -> ApiKeyFactory:
    async def create_api_key(
        *,
        scopes: list[str] | None = None,
        is_active: bool = True,
        expires_at: datetime | None = None,
        buyer_id: int | None = None,
        name: str = "Integration test key",
    ) -> str:
        raw_key, key_hash, key_prefix = generate_api_key()
        async with test_db() as session:
            session.add(
                ApiKey(
                    buyer_id=buyer_id,
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=name,
                    scopes=scopes or ["write:prices", "admin:all"],
                    is_active=is_active,
                    expires_at=expires_at,
                )
            )
            await session.commit()
        return raw_key

    return create_api_key


@pytest.fixture
async def client(
    test_db: async_sessionmaker[AsyncSession],
    api_key_factory: ApiKeyFactory,
) -> AsyncIterator[AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with test_db() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    raw_key = await api_key_factory()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"X-API-Key": raw_key},
    ) as test_client:
        try:
            yield test_client
        finally:
            app.dependency_overrides.pop(get_session, None)

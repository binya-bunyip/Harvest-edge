from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from harvest_edge.config import get_settings

settings = get_settings()
engine = create_async_engine(
    str(settings.database_url), echo=settings.database_echo, pool_pre_ping=True
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
SessionFactory = async_session_maker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.database import SessionFactory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session

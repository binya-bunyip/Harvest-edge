from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.models import Price
from harvest_edge.schemas.price import PriceCreate, PriceUpdate


async def create_price(db: AsyncSession, price_data: PriceCreate) -> Price:
    price = Price(**price_data.model_dump())
    db.add(price)
    await db.commit()
    await db.refresh(price)
    return price


async def get_price_by_id(db: AsyncSession, price_id: UUID) -> Price | None:
    return await db.scalar(select(Price).where(Price.id == price_id))


async def list_prices(
    db: AsyncSession,
    *,
    location_id: UUID | None = None,
    commodity: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Price]:
    statement = select(Price)
    if location_id is not None:
        statement = statement.where(Price.location_id == location_id)
    if commodity is not None:
        statement = statement.where(Price.commodity == commodity)
    result = await db.scalars(
        statement.order_by(Price.effective_date.desc(), Price.id).offset(offset).limit(limit)
    )
    return list(result.all())


async def update_price(
    db: AsyncSession, price_id: UUID, price_data: PriceUpdate
) -> Price | None:
    price = await get_price_by_id(db, price_id)
    if price is None:
        return None

    for field, value in price_data.model_dump().items():
        setattr(price, field, value)
    await db.commit()
    await db.refresh(price)
    return price


async def delete_price(db: AsyncSession, price_id: UUID) -> bool:
    price = await get_price_by_id(db, price_id)
    if price is None:
        return False

    await db.delete(price)
    await db.commit()
    return True


async def process_bulk_prices(ctx: dict, batch_id: str, records: list[dict]) -> int:
    """Background Arq task to process and persist bulk price records."""
    from harvest_edge.database import async_session_maker
    
    async with async_session_maker() as session:
        async with session.begin():
            for record_data in records:
                price = Price(**record_data)
                session.add(price)
        await session.commit()
    return len(records)

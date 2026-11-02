from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.models import Buyer
from harvest_edge.schemas.buyers import BuyerCreate, BuyerUpdate


async def create_buyer(db: AsyncSession, buyer_data: BuyerCreate) -> Buyer:
    buyer = Buyer(**buyer_data.model_dump())
    db.add(buyer)
    await db.commit()
    await db.refresh(buyer)
    return buyer


async def get_buyer_by_id(db: AsyncSession, buyer_id: int) -> Buyer | None:
    return await db.scalar(select(Buyer).where(Buyer.id == buyer_id))


async def list_buyers(db: AsyncSession, *, offset: int = 0, limit: int = 100) -> list[Buyer]:
    result = await db.scalars(select(Buyer).order_by(Buyer.id).offset(offset).limit(limit))
    return list(result.all())


async def update_buyer(
    db: AsyncSession, buyer_id: int, buyer_data: BuyerUpdate
) -> Buyer | None:
    buyer = await get_buyer_by_id(db, buyer_id)
    if buyer is None:
        return None

    for field, value in buyer_data.model_dump().items():
        setattr(buyer, field, value)
    await db.commit()
    await db.refresh(buyer)
    return buyer


async def delete_buyer(db: AsyncSession, buyer_id: int) -> bool:
    buyer = await get_buyer_by_id(db, buyer_id)
    if buyer is None:
        return False

    await db.delete(buyer)
    await db.commit()
    return True

from collections.abc import Awaitable
from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


async def run_with_integrity_handling(
    db: AsyncSession, operation: Awaitable[T], entity_name: str
) -> T:
    try:
        return await operation
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail=f"{entity_name} violates a database constraint"
        ) from exc

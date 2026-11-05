from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.api.constraints import run_with_integrity_handling
from harvest_edge.api.dependencies import get_session
from harvest_edge.api.deps import require_scopes
from harvest_edge.schemas.price import PriceCreate, PriceRead, PriceUpdate
from harvest_edge.services.price import (
    create_price,
    delete_price,
    get_price_by_id,
    list_prices,
    update_price,
)

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.post(
    "",
    response_model=PriceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scopes(["write:prices"]))],
)
async def create(
    price_data: PriceCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PriceRead:
    price = await run_with_integrity_handling(
        session, create_price(session, price_data), "Price"
    )
    return PriceRead.model_validate(price)


@router.get("", response_model=list[PriceRead])
async def list_all(
    session: Annotated[AsyncSession, Depends(get_session)],
    location_id: UUID | None = None,
    commodity: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[PriceRead]:
    prices = await list_prices(
        session,
        location_id=location_id,
        commodity=commodity,
        offset=offset,
        limit=limit,
    )
    return [PriceRead.model_validate(price) for price in prices]


@router.get("/{id}", response_model=PriceRead)
async def get_by_id(
    id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PriceRead:
    price = await get_price_by_id(session, id)
    if price is None:
        raise HTTPException(status_code=404, detail="Price not found")
    return PriceRead.model_validate(price)


@router.put("/{id}", response_model=PriceRead)
async def update(
    price_data: PriceUpdate,
    id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PriceRead:
    price = await run_with_integrity_handling(
        session, update_price(session, id, price_data), "Price"
    )
    if price is None:
        raise HTTPException(status_code=404, detail="Price not found")
    return PriceRead.model_validate(price)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    deleted = await run_with_integrity_handling(session, delete_price(session, id), "Price")
    if not deleted:
        raise HTTPException(status_code=404, detail="Price not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

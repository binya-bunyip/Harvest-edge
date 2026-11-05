from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.api.constraints import run_with_integrity_handling
from harvest_edge.api.dependencies import get_session
from harvest_edge.api.deps import require_scopes
from harvest_edge.schemas.buyers import BuyerCreate, BuyerRead, BuyerUpdate
from harvest_edge.services.buyers import (
    create_buyer,
    delete_buyer,
    get_buyer_by_id,
    list_buyers,
    update_buyer,
)

router = APIRouter(prefix="/api/buyers", tags=["buyers"])


@router.post(
    "",
    response_model=BuyerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scopes(["write:prices"]))],
)
async def create(
    buyer_data: BuyerCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BuyerRead:
    buyer = await run_with_integrity_handling(
        session, create_buyer(session, buyer_data), "Buyer"
    )
    return BuyerRead.model_validate(buyer)


@router.get("", response_model=list[BuyerRead])
async def list_all(
    session: Annotated[AsyncSession, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[BuyerRead]:
    buyers = await list_buyers(session, offset=offset, limit=limit)
    return [BuyerRead.model_validate(buyer) for buyer in buyers]


@router.get("/{id}", response_model=BuyerRead)
async def get_by_id(
    id: Annotated[int, Path(gt=0)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BuyerRead:
    buyer = await get_buyer_by_id(session, id)
    if buyer is None:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return BuyerRead.model_validate(buyer)


@router.put("/{id}", response_model=BuyerRead)
async def update(
    buyer_data: BuyerUpdate,
    id: Annotated[int, Path(gt=0)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BuyerRead:
    buyer = await run_with_integrity_handling(
        session, update_buyer(session, id, buyer_data), "Buyer"
    )
    if buyer is None:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return BuyerRead.model_validate(buyer)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    id: Annotated[int, Path(gt=0)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    deleted = await run_with_integrity_handling(
        session, delete_buyer(session, id), "Buyer"
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

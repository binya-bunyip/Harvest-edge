from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.api.dependencies import get_session
from harvest_edge.models import BuyerBid, DataSource
from harvest_edge.schemas.bids import BuyerBidList, BuyerBidRead
from harvest_edge.schemas.common import ProvenanceBundle, ProvenanceMetadata

router = APIRouter(prefix="/api/bids", tags=["bids"])


@router.get("", response_model=BuyerBidList)
async def list_bids(
    session: Annotated[AsyncSession, Depends(get_session)],
    receival_site_id: Annotated[int | None, Query(gt=0)] = None,
    commodity_id: Annotated[int | None, Query(gt=0)] = None,
    grade_id: Annotated[int | None, Query(gt=0)] = None,
    season_id: Annotated[int | None, Query(gt=0)] = None,
    delivery_window_id: Annotated[int | None, Query(gt=0)] = None,
) -> BuyerBidList:
    as_of_date = datetime.now(UTC).date()
    statement = (
        select(BuyerBid, DataSource)
        .join(DataSource, BuyerBid.data_source_id == DataSource.id)
        .where(
            BuyerBid.effective_start_date <= as_of_date,
            (BuyerBid.effective_end_date.is_(None) | (BuyerBid.effective_end_date >= as_of_date)),
        )
    )
    filters = (
        (BuyerBid.receival_site_id, receival_site_id),
        (BuyerBid.commodity_id, commodity_id),
        (BuyerBid.grade_id, grade_id),
        (BuyerBid.season_id, season_id),
        (BuyerBid.delivery_window_id, delivery_window_id),
    )
    for column, value in filters:
        if value is not None:
            statement = statement.where(column == value)

    rows = (await session.execute(statement.order_by(BuyerBid.quoted_at.desc()))).all()
    source_by_id: dict[int, DataSource] = {}
    for _, source in rows:
        source_by_id[source.id] = source
    return BuyerBidList(
        items=[BuyerBidRead.model_validate(bid) for bid, _ in rows],
        provenance=ProvenanceBundle(
            sources=[
                ProvenanceMetadata.model_validate({"source_id": source.id, **source.__dict__})
                for source in source_by_id.values()
            ]
        ),
    )

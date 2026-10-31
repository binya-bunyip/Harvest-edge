from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.api.dependencies import get_session
from harvest_edge.models import BuyerBid, DataSource, HandlingFreightCharge
from harvest_edge.schemas.common import ProvenanceBundle, ProvenanceMetadata
from harvest_edge.schemas.netback import NetbackRead
from harvest_edge.services.pricing import calculate_netback

router = APIRouter(prefix="/api/netback", tags=["netback"])


@router.get("", response_model=NetbackRead)
async def get_netback(
    receival_site_id: Annotated[int, Query(gt=0)],
    port_terminal_id: Annotated[int, Query(gt=0)],
    commodity_id: Annotated[int, Query(gt=0)],
    session: Annotated[AsyncSession, Depends(get_session)],
    grade_id: Annotated[int | None, Query(gt=0)] = None,
    season_id: Annotated[int | None, Query(gt=0)] = None,
    delivery_window_id: Annotated[int | None, Query(gt=0)] = None,
    as_of_date: date | None = None,
) -> NetbackRead:
    effective_date = as_of_date or datetime.now(UTC).date()
    bid_query = (
        select(BuyerBid, DataSource)
        .join(DataSource, BuyerBid.data_source_id == DataSource.id)
        .where(
            BuyerBid.receival_site_id == receival_site_id,
            BuyerBid.commodity_id == commodity_id,
            BuyerBid.fob_export_price_aud_per_tonne.is_not(None),
            BuyerBid.effective_start_date <= effective_date,
            or_(
                BuyerBid.effective_end_date.is_(None), BuyerBid.effective_end_date >= effective_date
            ),
        )
    )
    for column, value in (
        (BuyerBid.grade_id, grade_id),
        (BuyerBid.season_id, season_id),
        (BuyerBid.delivery_window_id, delivery_window_id),
    ):
        if value is not None:
            bid_query = bid_query.where(column == value)
    bid_row = (
        await session.execute(bid_query.order_by(BuyerBid.quoted_at.desc()).limit(1))
    ).first()
    if bid_row is None:
        raise HTTPException(
            status_code=404, detail="No eligible FOB bid found for the requested filters"
        )
    bid, bid_source = bid_row

    charge_query = (
        select(HandlingFreightCharge, DataSource)
        .join(DataSource, HandlingFreightCharge.data_source_id == DataSource.id)
        .where(
            HandlingFreightCharge.receival_site_id == receival_site_id,
            HandlingFreightCharge.port_terminal_id == port_terminal_id,
            or_(
                HandlingFreightCharge.commodity_id.is_(None),
                HandlingFreightCharge.commodity_id == commodity_id,
            ),
            HandlingFreightCharge.effective_start_date <= effective_date,
            or_(
                HandlingFreightCharge.effective_end_date.is_(None),
                HandlingFreightCharge.effective_end_date >= effective_date,
            ),
        )
        .order_by(
            HandlingFreightCharge.commodity_id.is_(None),
            HandlingFreightCharge.effective_start_date.desc(),
        )
        .limit(1)
    )
    charge_row = (await session.execute(charge_query)).first()
    if charge_row is None:
        raise HTTPException(
            status_code=404, detail="No eligible freight and handling charges found"
        )
    charge, charge_source = charge_row

    uncertainty = bid.uncertainty_margin_aud_per_tonne + charge.uncertainty_margin_aud_per_tonne
    total_costs, netback = calculate_netback(
        bid.fob_export_price_aud_per_tonne,
        charge.freight_cost_aud_per_tonne,
        charge.receival_fee_aud_per_tonne,
        charge.handling_fee_aud_per_tonne,
        uncertainty,
    )
    sources = {source.id: source for source in (bid_source, charge_source)}
    return NetbackRead(
        bid_id=bid.id,
        receival_site_id=receival_site_id,
        port_terminal_id=port_terminal_id,
        commodity_id=commodity_id,
        grade_id=bid.grade_id,
        season_id=bid.season_id,
        delivery_window_id=bid.delivery_window_id,
        as_of_date=effective_date,
        fob_export_price_aud_per_tonne=bid.fob_export_price_aud_per_tonne,
        freight_cost_aud_per_tonne=charge.freight_cost_aud_per_tonne,
        receival_fee_aud_per_tonne=charge.receival_fee_aud_per_tonne,
        handling_fee_aud_per_tonne=charge.handling_fee_aud_per_tonne,
        total_costs_aud_per_tonne=total_costs,
        uncertainty_margin_aud_per_tonne=uncertainty,
        netback_aud_per_tonne=netback,
        provenance=ProvenanceBundle(
            sources=[
                ProvenanceMetadata.model_validate({"source_id": source.id, **source.__dict__})
                for source in sources.values()
            ]
        ),
    )

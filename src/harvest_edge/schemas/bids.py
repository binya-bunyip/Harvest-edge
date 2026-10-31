from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from harvest_edge.schemas.common import ProvenanceBundle


class BuyerBidRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receival_site_id: int
    commodity_id: int
    grade_id: int
    season_id: int
    delivery_window_id: int
    data_source_id: int
    bid_price_aud_per_tonne: Decimal
    fob_export_price_aud_per_tonne: Decimal | None
    uncertainty_margin_aud_per_tonne: Decimal
    quoted_at: datetime
    effective_start_date: date
    effective_end_date: date | None


class BuyerBidList(BaseModel):
    items: list[BuyerBidRead]
    provenance: ProvenanceBundle

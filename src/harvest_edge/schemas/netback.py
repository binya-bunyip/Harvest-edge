from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from harvest_edge.schemas.common import ProvenanceBundle


class NetbackRead(BaseModel):
    bid_id: int
    receival_site_id: int
    port_terminal_id: int
    commodity_id: int
    grade_id: int
    season_id: int
    delivery_window_id: int
    as_of_date: date
    fob_export_price_aud_per_tonne: Decimal
    freight_cost_aud_per_tonne: Decimal
    receival_fee_aud_per_tonne: Decimal
    handling_fee_aud_per_tonne: Decimal
    total_costs_aud_per_tonne: Decimal
    uncertainty_margin_aud_per_tonne: Decimal
    netback_aud_per_tonne: Decimal
    provenance: ProvenanceBundle

from pydantic import Field

from harvest_edge.schemas.buyers import BuyerRead
from harvest_edge.schemas.locations import LocationRead
from harvest_edge.schemas.price import PriceRead


class NearbyLocationRead(LocationRead):
    buyer: BuyerRead
    prices: list[PriceRead] = Field(default_factory=list)

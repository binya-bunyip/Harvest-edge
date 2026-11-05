from geoalchemy2 import Geography
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.models import Buyer, Location, Price


async def get_locations_nearby(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_km: float,
    commodity: str | None = None,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[Location, Buyer, Price | None]]:
    search_point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326).cast(
        Geography(geometry_type="POINT", srid=4326)
    )
    distance = func.ST_Distance(Location.point, search_point)
    nearby_ids = select(Location.id).where(
        func.ST_DWithin(Location.point, search_point, radius_km * 1000)
    )
    if commodity is not None:
        nearby_ids = nearby_ids.where(Location.prices.any(Price.commodity == commodity))
    nearby_ids = nearby_ids.order_by(distance, Location.id).limit(limit).offset(offset).subquery()
    price_join = Price.location_id == Location.id
    if commodity is not None:
        price_join = and_(price_join, Price.commodity == commodity)

    statement = (
        select(Location, Buyer, Price)
        .join(Buyer, Buyer.id == Location.buyer_id)
        .outerjoin(Price, price_join)
        .join(nearby_ids, nearby_ids.c.id == Location.id)
    )

    result = await db.execute(
        statement.order_by(distance, Location.id, Price.effective_date.desc())
    )
    return list(result.all())

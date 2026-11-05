from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.models import Location
from harvest_edge.schemas.locations import LocationCreate, LocationUpdate


def _point_from_coordinates(latitude: float, longitude: float) -> WKTElement:
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


async def create_location(db: AsyncSession, location_data: LocationCreate) -> Location:
    values = location_data.model_dump()
    location = Location(
        **values,
        point=_point_from_coordinates(values["latitude"], values["longitude"]),
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


async def get_location_by_id(db: AsyncSession, location_id: UUID) -> Location | None:
    return await db.scalar(select(Location).where(Location.id == location_id))


async def list_locations(
    db: AsyncSession, *, offset: int = 0, limit: int = 100
) -> list[Location]:
    result = await db.scalars(select(Location).order_by(Location.id).offset(offset).limit(limit))
    return list(result.all())


async def update_location(
    db: AsyncSession, location_id: UUID, location_data: LocationUpdate
) -> Location | None:
    location = await get_location_by_id(db, location_id)
    if location is None:
        return None

    values = location_data.model_dump()
    for field, value in values.items():
        setattr(location, field, value)
    location.point = _point_from_coordinates(values["latitude"], values["longitude"])
    await db.commit()
    await db.refresh(location)
    return location


async def delete_location(db: AsyncSession, location_id: UUID) -> bool:
    location = await get_location_by_id(db, location_id)
    if location is None:
        return False

    await db.delete(location)
    await db.commit()
    return True

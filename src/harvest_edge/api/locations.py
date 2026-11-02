from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.api.constraints import run_with_integrity_handling
from harvest_edge.api.dependencies import get_session
from harvest_edge.schemas.locations import LocationCreate, LocationRead, LocationUpdate
from harvest_edge.services.locations import (
    create_location,
    delete_location,
    get_location_by_id,
    list_locations,
    update_location,
)

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create(
    location_data: LocationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LocationRead:
    location = await run_with_integrity_handling(
        session, create_location(session, location_data), "Location"
    )
    return LocationRead.model_validate(location)


@router.get("", response_model=list[LocationRead])
async def list_all(
    session: Annotated[AsyncSession, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[LocationRead]:
    locations = await list_locations(session, offset=offset, limit=limit)
    return [LocationRead.model_validate(location) for location in locations]


@router.get("/{id}", response_model=LocationRead)
async def get_by_id(
    id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LocationRead:
    location = await get_location_by_id(session, id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationRead.model_validate(location)


@router.put("/{id}", response_model=LocationRead)
async def update(
    location_data: LocationUpdate,
    id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LocationRead:
    location = await run_with_integrity_handling(
        session, update_location(session, id, location_data), "Location"
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationRead.model_validate(location)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    deleted = await run_with_integrity_handling(
        session, delete_location(session, id), "Location"
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Location not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LocationFields(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    buyer_id: int = Field(gt=0)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class LocationCreate(LocationFields):
    pass


class LocationUpdate(LocationFields):
    pass


class LocationRead(LocationFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

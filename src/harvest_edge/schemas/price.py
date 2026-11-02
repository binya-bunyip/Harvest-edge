from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PriceFields(BaseModel):
    location_id: UUID
    commodity: str = Field(min_length=1, max_length=100)
    price_per_tonne: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    effective_date: datetime

    @field_validator("commodity")
    @classmethod
    def normalize_commodity(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("commodity must not be empty")
        return value

    @field_validator("effective_date")
    @classmethod
    def normalize_effective_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("effective_date must include a timezone")
        return value.astimezone(UTC)


class PriceCreate(PriceFields):
    pass


class PriceUpdate(PriceFields):
    pass


class PriceRead(PriceFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

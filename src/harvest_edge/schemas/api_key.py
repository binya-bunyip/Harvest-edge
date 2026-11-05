from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    buyer_id: int | None = Field(default=None, gt=0)
    scopes: list[str] = Field(min_length=1)
    expires_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized

    @field_validator("scopes")
    @classmethod
    def scopes_must_not_be_blank(cls, scopes: list[str]) -> list[str]:
        normalized = [scope.strip() for scope in scopes]
        if any(not scope for scope in normalized):
            raise ValueError("scopes must not contain blank values")
        return normalized

    @field_validator("expires_at")
    @classmethod
    def expiry_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("expires_at must include a timezone")
        if value is not None and value <= datetime.now(UTC):
            raise ValueError("expires_at must be in the future")
        return value


class ApiKeyCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    buyer_id: int | None
    name: str
    scopes: list[str]
    key_prefix: str
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    api_key: str

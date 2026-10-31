from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProvenanceMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: int
    publisher_name: str
    source_url: str
    retrieved_at: datetime
    published_at: datetime | None
    verification_status: str
    licence_restrictions: str | None


class ProvenanceBundle(BaseModel):
    sources: list[ProvenanceMetadata]

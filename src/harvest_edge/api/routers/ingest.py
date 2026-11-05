from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from harvest_edge.api.deps import require_scopes
from harvest_edge.config import get_settings
from harvest_edge.schemas.price import PriceCreate

router = APIRouter(prefix="/api/v1/prices", tags=["price ingestion"])


class BulkIngestPayload(BaseModel):
    batch_id: UUID
    records: list[PriceCreate] = Field(min_length=1, max_length=1000)


class BulkIngestAccepted(BaseModel):
    job_id: str
    status: str = "accepted"


@router.post(
    "/bulk-upload",
    response_model=BulkIngestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_scopes(["write:prices"]))],
)
async def bulk_upload(payload: BulkIngestPayload) -> BulkIngestAccepted:
    job_id = f"batch-{payload.batch_id}"
    redis = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        job = await redis.enqueue_job(
            "process_bulk_prices",
            [record.model_dump(mode="json") for record in payload.records],
            _job_id=job_id,
        )
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion queue is unavailable",
        ) from exc
    finally:
        await redis.aclose()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A batch with this ID has already been submitted",
        )
    return BulkIngestAccepted(job_id=job_id)
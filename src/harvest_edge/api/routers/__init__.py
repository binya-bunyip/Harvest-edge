import os
from fastapi import APIRouter, Depends, HTTPException, status
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])

async def get_arq_redis() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379")))

class PriceItem(BaseModel):
    location_id: str
    commodity: str
    price_per_tonne: float
    effective_date: str

class BulkIngestPayload(BaseModel):
    batch_id: str
    prices: list[PriceItem] = Field(..., max_items=1000)

@router.post("/prices", status_code=status.HTTP_202_ACCEPTED)
async def bulk_upload_prices(payload: BulkIngestPayload, redis: ArqRedis = Depends(get_arq_redis)):
    """Accepts bulk pricing sheets and enqueues them for background processing via Arq."""
    job = await redis.enqueue_job(
        "process_bulk_prices",
        [item.model_dump() for item in payload.prices],
        _job_id=f"batch-{payload.batch_id}"
    )
    if not job:
        raise HTTPException(status_code=409, detail="Duplicate batch ingestion job detected.")
    
    return {"status": "accepted", "job_id": job.job_id, "record_count": len(payload.prices)}
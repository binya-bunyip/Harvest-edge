from uuid import uuid4

from arq import create_pool
from arq.connections import RedisSettings
from httpx import AsyncClient

from harvest_edge.config import get_settings


async def test_bulk_upload_enqueues_job(client: AsyncClient) -> None:
    batch_id = uuid4()
    response = await client.post(
        "/api/v1/prices/bulk-upload",
        json={
            "batch_id": str(batch_id),
            "records": [
                {
                    "location_id": str(uuid4()),
                    "commodity": "Wheat",
                    "price_per_tonne": "350.50",
                    "effective_date": "2026-11-02T00:00:00Z",
                }
            ],
        },
    )

    assert response.status_code == 202
    assert response.json() == {"job_id": f"batch-{batch_id}", "status": "accepted"}

    redis = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        assert await redis.exists(f"arq:job:batch-{batch_id}")
    finally:
        await redis.zrem("arq:queue", f"batch-{batch_id}")
        await redis.delete(f"arq:job:batch-{batch_id}", f"arq:result:batch-{batch_id}")
        await redis.aclose()


async def test_bulk_upload_rejects_duplicate_batch_id(client: AsyncClient) -> None:
    batch_id = uuid4()
    payload = {
        "batch_id": str(batch_id),
        "records": [
            {
                "location_id": str(uuid4()),
                "commodity": "Wheat",
                "price_per_tonne": "350.50",
                "effective_date": "2026-11-02T00:00:00Z",
            }
        ],
    }

    first_response = await client.post("/api/v1/prices/bulk-upload", json=payload)
    duplicate_response = await client.post("/api/v1/prices/bulk-upload", json=payload)

    assert first_response.status_code == 202
    assert duplicate_response.status_code == 409

    redis = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        await redis.zrem("arq:queue", f"batch-{batch_id}")
        await redis.delete(f"arq:job:batch-{batch_id}", f"arq:result:batch-{batch_id}")
    finally:
        await redis.aclose()
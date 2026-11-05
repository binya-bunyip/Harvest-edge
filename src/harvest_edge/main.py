from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from harvest_edge.api.admin import router as admin_router
from harvest_edge.api.bids import router as bids_router
from harvest_edge.api.buyers import router as buyers_router
from harvest_edge.api.locations import router as locations_router
from harvest_edge.api.netback import router as netback_router
from harvest_edge.api.prices import router as prices_router
from harvest_edge.api.routers.ingest import router as ingest_router
from harvest_edge.database import SessionFactory, engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


app = FastAPI(title="Harvest Edge API", version="0.1.0", lifespan=lifespan)
app.include_router(bids_router)
app.include_router(admin_router)
app.include_router(buyers_router)
app.include_router(locations_router)
app.include_router(prices_router)
app.include_router(ingest_router)
app.include_router(netback_router)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {
        "service": "Harvest Edge API",
        "docs": "/docs",
        "health": "/health",
        "readiness": "/ready",
    }


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ready"}

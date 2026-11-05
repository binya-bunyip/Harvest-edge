from typing import Any

from arq.connections import RedisSettings

from harvest_edge.config import get_settings
from harvest_edge.database import async_session_maker
from harvest_edge.models import Price
from harvest_edge.schemas.price import PriceCreate


async def process_bulk_prices(ctx: dict[str, Any], records: list[dict[str, Any]]) -> int:
    prices = [Price(**PriceCreate.model_validate(record).model_dump()) for record in records]
    async with async_session_maker.begin() as session:
        session.add_all(prices)
    return len(prices)


class WorkerSettings:
    functions = [process_bulk_prices]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
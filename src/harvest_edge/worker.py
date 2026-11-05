from arq.connections import RedisSettings
from harvest_edge.config import get_settings
from harvest_edge.services.price import process_bulk_prices


async def startup(ctx: dict) -> None:
    """Run startup tasks (e.g., initializing connection pools or logging)."""
    settings = get_settings()
    ctx["settings"] = settings


async def shutdown(ctx: dict) -> None:
    """Run shutdown tasks (e.g., closing connections)."""
    pass


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    functions = [process_bulk_prices]
    startup = startup
    shutdown = shutdown
    poll_delay = 0.5
    job_timeout = 300

from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HARVEST_EDGE_", env_file=".env", extra="ignore")

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://harvest_edge:harvest_edge@localhost:5432/harvest_edge"
    )
    database_echo: bool = False
    http_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    scraper_min_interval_seconds: float = Field(default=1.0, ge=0, le=300)


@lru_cache
def get_settings() -> Settings:
    return Settings()

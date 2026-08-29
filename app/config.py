from datetime import time
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, overridable via environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Appointment Scheduler API"
    environment: str = "development"

    # Host mapping is 5433:5432 in docker-compose.yml.
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/appointment_scheduler"
    )

    # Booking grid granularity in minutes (assumption A3: fixed 60-minute grid).
    slot_minutes: int = 60

    # Global business hours: identical for every dealership and every day of the
    # week (assumption A5: same hours all days, in the dealership's IANA tz).
    business_open_time: time = time(8, 0)
    business_close_time: time = time(17, 30)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

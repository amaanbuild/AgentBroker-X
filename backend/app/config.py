"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values are read from environment variables (and a local `.env` file in
    development). On Railway, `DATABASE_URL` is injected automatically when a
    PostgreSQL plugin is attached.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AgentBroker X"
    app_env: str = Field(default="development")
    api_prefix: str = ""

    # Railway provides DATABASE_URL. Fall back to a local SQLite file so the
    # project runs out of the box with zero infrastructure for the demo.
    database_url: str = Field(
        default="sqlite:///./agentbroker.db",
        validation_alias="DATABASE_URL",
    )

    # Supervisor thresholds (seconds).
    task_timeout_seconds: int = 120
    heartbeat_grace_seconds: int = 45

    # Economy defaults.
    platform_fee_bps: int = 250  # 2.5% taken from released escrow.
    default_starting_balance: float = 1000.0

    cors_origins: str = "*"

    def normalized_database_url(self) -> str:
        """SQLAlchemy 2.x wants `postgresql+psycopg`, Railway gives `postgres://`."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

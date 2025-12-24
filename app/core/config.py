"""Application configuration."""

from functools import lru_cache
from typing import Optional

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # API Settings
    PROJECT_NAME: str = "Async Job Scheduler"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[PostgresDsn] = None

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        values = info.data
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
                host=values.get("POSTGRES_SERVER"),
                port=values.get("POSTGRES_PORT"),
                path=f"{values.get('POSTGRES_DB') or ''}",
            )
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[RedisDsn] = None

    @field_validator("REDIS_URL", mode="before")
    def assemble_redis_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        values = info.data
        return str(
            RedisDsn.build(
                scheme="redis",
                host=values.get("REDIS_HOST"),
                port=values.get("REDIS_PORT"),
                path=f"/{values.get('REDIS_DB') or 0}",
            )
        )

    # Job Queue Configuration
    JOB_QUEUE_NAME: str = "jobs:queue"
    JOB_PROCESSING_NAME: str = "jobs:processing"
    JOB_DLQ_NAME: str = "jobs:dlq"  # Dead Letter Queue
    JOB_RESULT_TTL: int = 3600  # 1 hour

    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5  # seconds

    # Worker Configuration
    WORKER_CONCURRENCY: int = 20  # Increase from 10
    WORKER_POLL_INTERVAL: int = 1  # seconds

    # CORS Settings
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

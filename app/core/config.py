from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://scheduler:scheduler@localhost:5432/job_scheduler"
    )
    redis_url: str = "redis://localhost:6379/0"

    job_queue: str = "jobs:queue"
    job_dlq: str = "jobs:dlq"

    max_retries: int = 3
    retry_base_delay: int = 5  # seconds — doubles each attempt
    worker_count: int = 5

    model_config = {"env_file": ".env"}


settings = Settings()

from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.models.base import BaseModel


class JobStatus(str, enum.Enum):
    """Job status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(str, enum.Enum):
    """Job type enumeration."""

    EMAIL = "email"
    DATA_PROCESSING = "data_processing"
    REPORT_GENERATION = "report_generation"
    IMAGE_PROCESSING = "image_processing"
    WEBHOOK = "webhook"


class Job(BaseModel):
    """Job model for tracking async jobs."""

    __tablename__ = "jobs"

    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType), nullable=False, index=True
    )

    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True
    )

    # Job metadata
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retry logic
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Priority (1 = highest, 10 = lowest)
    priority: Mapped[int] = mapped_column(Integer, default=5, index=True)

    def __repr__(self) -> str:
        return f"<Job {self.id} [{self.job_type.value}] - {self.status.value}>"

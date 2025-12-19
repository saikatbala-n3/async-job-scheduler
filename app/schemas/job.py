from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.job import JobStatus, JobType


class JobBase(BaseModel):
    """Base job schema."""

    job_type: JobType
    payload: dict = Field(..., description="Job payload data")
    priority: int = Field(5, ge=1, le=10, description="Job priority (1=highest)")
    scheduled_at: Optional[datetime] = Field(None, description="When to run the job")


class JobCreate(JobBase):
    """Job creation schema."""

    pass


class JobUpdate(BaseModel):
    """Job update schema."""

    status: Optional[JobStatus] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class JobResponse(JobBase):
    """Job response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: JobStatus
    result: Optional[dict] = None
    error: Optional[str] = None
    retry_count: int
    max_retries: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class JobStats(BaseModel):
    """Job statistics schema."""

    total_jobs: int
    pending: int
    queued: int
    processing: int
    completed: int
    failed: int
    queue_depth: int
    success_rate: float

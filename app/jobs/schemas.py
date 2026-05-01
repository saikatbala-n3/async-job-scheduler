from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.jobs.models import JobStatus, JobType


class JobCreate(BaseModel):
    job_type: JobType
    payload: dict = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: UUID
    job_type: JobType
    status: JobStatus
    payload: dict
    result: str | None
    error: str | None
    retry_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class JobStats(BaseModel):
    total: int
    queued: int
    processing: int
    completed: int
    retrying: int
    failed: int
    queue_depth: int
    success_rate: float

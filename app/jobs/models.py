import uuid

from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.core.database import Base


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(str, Enum):
    WORK = "work"  # simulates variable-duration work, always succeeds
    UNRELIABLE = "unreliable"  # fails 50% of the time — demonstrates retry and DLQ


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType), nullable=False, index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Job {self.id} [{self.job_type.value}] - {self.status.value}>"

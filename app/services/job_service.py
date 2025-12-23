import json
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.job import Job, JobStatus, JobType
from app.schemas.job import JobCreate, JobUpdate, JobStats
from app.core.redis_client import RedisClient
from app.core.config import settings
from app.core.metrics import (
    job_created_counter,
    job_completed_counter,
    queue_depth_gauge,
)


class JobService:
    """Service for managing jobs."""

    @staticmethod
    async def create_job(db: AsyncSession, redis: RedisClient, job_in: JobCreate):
        """
        Create and enqueue a new job.

        Args:
            db: Database session
            redis: Redis client
            job_in: Job creation data

        Returns:
            Created job
        """
        job = Job(
            job_type=job_in.job_type,
            status=JobStatus.QUEUED,
            payload=job_in.payload,
            priority=job_in.priority,
            scheduled_at=job_in.scheduled_at,
            max_retries=settings.MAX_RETRIES,
        )

        db.add(job)
        await db.flush()
        await db.refresh(job)
        job_created_counter.labels(job_type=job_in.job_type.value).inc()

        # Enqueue job in Redis
        job_data = {
            "id": job.id,
            "job_type": job.job_type.value,
            "payload": job_in.payload,
            "priority": job.priority,
            "retry_count": 0,
        }

        await redis.enqueue(settings.JOB_QUEUE_NAME, job_data)

        return job

    @staticmethod
    async def get_job(db: AsyncSession, job_id: str):
        """Get job by ID."""

        result = await db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """
        List jobs with optional filters.

        Args:
            db: Database session
            status: Filter by status
            job_type: Filter by type
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of jobs
        """
        query = select(Job)

        if status:
            query = query.where(Job.status == status)
        if job_type:
            query = query.where(Job.job_type == job_type)

        query = query.order_by(Job.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_job(db: AsyncSession, job_id: str, job_update: JobUpdate):
        """Update job status and result."""

        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            return None

        update_job = job_update.model_dump(exclude_unset=True)
        for field, value in update_job.items():
            if field == "result" and value:
                setattr(job, field, json.dumps(value))
            else:
                setattr(job, field, value)

        if job_update.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.completed_at = datetime.utcnow()
            job_completed_counter.labels(
                job_type=job.job_type.value, status=job_update.status.value
            ).inc()
        elif job_update.status == JobStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.utcnow()

        await db.flush()
        await db.refresh(job)

        return job

    @staticmethod
    async def get_stats(db: AsyncSession, redis: RedisClient):
        """
        Get job statistics.

        Returns:
            Job statistics
        """
        # Count by status
        status_counts = {}
        for status in JobStatus:
            result = await db.execute(
                select(func.count(Job.id)).where(Job.status == status)
            )
            status_counts[status.value] = result.scalar() or 0

        total = sum(status_counts.values())
        completed = status_counts.get(JobStatus.COMPLETED.value, 0)
        failed = status_counts.get(JobStatus.FAILED.value, 0)

        total_finished = completed + failed
        success_rate = (completed / total_finished * 100) if total_finished > 0 else 0.0

        queue_depth = await redis.queue_length(settings.JOB_QUEUE_NAME)

        return JobStats(
            total_jobs=total,
            pending=status_counts.get(JobStatus.PENDING.value, 0),
            queued=status_counts.get(JobStatus.QUEUED.value, 0),
            processing=status_counts.get(JobStatus.PROCESSING.value, 0),
            completed=completed,
            failed=failed,
            queue_depth=queue_depth,
            success_rate=round(success_rate, 2),
        )

    @staticmethod
    async def retry_job(db: AsyncSession, redis: RedisClient, job_id: str):
        """
        Retry a failed job.

        Args:
            db: Database session
            redis: Redis client
            job_id: Job ID

        Returns:
            Updated job or None
        """
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job or job.status != JobStatus.FAILED:
            return None

        if job.retry_count >= job.max_retries:
            return None

        # Update job status
        job.status = JobStatus.QUEUED
        job.retry_count += 1
        job.error = None

        await db.flush()
        await db.refresh(job)

        # Re-enqueue
        job_data = {
            "id": job.id,
            "job_type": job.job_type.value,
            "payload": job.payload,
            "priority": job.priority,
            "retry_count": job.retry_count,
        }

        await redis.enqueue(settings.JOB_QUEUE_NAME, job_data)

        return job

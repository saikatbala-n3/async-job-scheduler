from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import queue
from app.core.config import settings
from app.metrics import jobs_created, queue_depth
from app.jobs.schemas import JobCreate, JobStats
from app.jobs.models import Job, JobStatus, JobType


async def create_job(db: AsyncSession, job_in: JobCreate):
    """Create a job, persist to DB, and enqueue to Redis."""
    job = Job(job_type=job_in.job_type, payload=job_in.payload)

    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()

    await queue.enqueue(
        settings.job_queue,
        {
            "id": str(job.id),
            "job_type": job.job_type.value,
            "payload": job.payload,
            "retry_count": 0,
        },
    )

    jobs_created.labels(job_type=job_in.job_type.value).inc()
    queue_depth.set(await queue.queue_length(settings.job_queue))
    return job


async def get_job(db: AsyncSession, job_id: str):
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    status: JobStatus | None = None,
    job_type: JobType | None = None,
    limit: int = 50,
):
    """List jobs with optional filters."""
    query = select(Job).order_by(Job.created_at.desc()).limit(limit)

    if status:
        query = query.where(Job.status == status)
    if job_type:
        query = query.where(Job.job_type == job_type)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_stats(db: AsyncSession):
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
    success_rate = completed / total_finished * 100 if total_finished else 0.0

    return JobStats(
        total=total,
        retrying=status_counts.get(JobStatus.RETRYING.value, 0),
        queued=status_counts.get(JobStatus.QUEUED.value, 0),
        processing=status_counts.get(JobStatus.PROCESSING.value, 0),
        completed=completed,
        failed=failed,
        queue_depth=await queue.queue_length(settings.job_queue),
        success_rate=round(success_rate, 2),
    )


async def retry_job(db: AsyncSession, job_id: str):
    """Manually re-enqueue a FAILED job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job or job.status != JobStatus.FAILED:
        return None
    job.status = JobStatus.QUEUED
    job.retry_count = 0
    job.error = None

    await db.commit()
    await queue.enqueue(
        settings.job_queue,
        {
            "id": str(job.id),
            "job_type": job.job_type.value,
            "payload": job.payload,
            "retry_count": job.retry_count,
        },
    )
    return job

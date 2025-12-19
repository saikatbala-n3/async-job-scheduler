from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis, RedisClient
from app.schemas.job import JobCreate, JobResponse, JobStats
from app.services.job_service import JobService
from app.models.job import JobStatus, JobType

router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
        Create and enqueue a new job.

        Example payload for DATA_PROCESSING:
    ```json
        {
            "job_type": "data_processing",
            "payload": {
                "file_url": "https://example.com/data.csv",
                "operation": "aggregate"
            },
            "priority": 5
        }
    ```
    """
    job = await JobService.create_job(db, redis, job_in)
    return job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """get job by id."""
    job = await JobService.get_job(db, job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return job


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    type_filter: Optional[JobType] = Query(None, alias="type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List jobs with optional filters.

    Query parameters:
    - status: Filter by job status
    - type: Filter by job type
    - skip: Pagination offset
    - limit: Max results per page
    """
    jobs = await JobService.list_jobs(
        db, status=status_filter, job_type=type_filter, skip=skip, limit=limit
    )
    return jobs


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Retry a failed job.

    Conditions:
    - Job must be in FAILED status
    - Job must not have exceeded max retries
    """
    job = await JobService.retry_job(db, redis, job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be retried (not failed or max retries exceeded)",
        )

    return job


@router.get("/stats/summary", response_model=JobStats)
async def get_job_stats(
    db: AsyncSession = Depends(get_db), redis: RedisClient = Depends(get_redis)
):
    """
    Get job statistics and metrics.

    Returns:
    - Total jobs
    - Jobs by status
    - Current queue depth
    - Success rate
    """
    stats = await JobService.get_stats(db, redis)
    return stats

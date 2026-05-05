import json
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import queue
from app.core.config import settings
from app.core.database import get_db
from app.jobs.models import JobStatus, JobType
from app.jobs.schemas import JobCreate, JobResponse, JobStats
from app.jobs.service import create_job, retry_job, list_jobs, get_job, get_stats

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(job_in: JobCreate, db: AsyncSession = Depends(get_db)):
    return await create_job(db, job_in)


@router.get("/", response_model=list[JobResponse])
async def list_all_jobs(
    type: JobType | None = Query(None),
    status: JobStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await list_jobs(db, status=status, job_type=type, limit=limit)


@router.get("/stats", response_model=JobStats)
async def get_job_stats(db: AsyncSession = Depends(get_db)):
    return await get_stats(db)


@router.get("/dlq", response_model=list[dict])
async def inspect_dlq(limit: int = Query(20, ge=1, le=100)):
    r = queue.client()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Redis unavailable"
        )
    items = await r.lrange(settings.job_dlq, 0, limit - 1)
    return [json.loads(item) for item in items]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, str(job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_failed_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await retry_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not FAILED or not found",
        )
    return job

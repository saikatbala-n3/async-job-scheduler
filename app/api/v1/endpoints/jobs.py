"""Job management endpoints."""
from fastapi import APIRouter, HTTPException, status
from rq.job import Job as RQJob

from app.core.redis import get_queue, get_redis_connection
from app.models.job import JobStatus, JobType
from app.schemas.job import (
    DataProcessingJobCreate,
    EmailJobCreate,
    JobCreateResponse,
    JobListResponse,
    JobResponse,
    ReportJobCreate,
)
from app.worker.tasks import (
    generate_report_task,
    process_data_task,
    send_email_task,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/email", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_job(payload: EmailJobCreate):
    """
    Create email sending job.

    Args:
        payload: Email job details

    Returns:
        Job creation response
    """
    queue = get_queue("default")

    job = queue.enqueue(
        send_email_task,
        to=payload.to,
        subject=payload.subject,
        body=payload.body,
        job_timeout=300,
        result_ttl=3600,
    )

    return JobCreateResponse(
        job_id=job.id,
        status=JobStatus.QUEUED,
        message="Email job created successfully"
    )


@router.post("/process-data", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_data_processing_job(payload: DataProcessingJobCreate):
    """
    Create data processing job.

    Args:
        payload: Data processing job details

    Returns:
        Job creation response
    """
    queue = get_queue("default")

    job = queue.enqueue(
        process_data_task,
        data_id=payload.data_id,
        options=payload.options,
        job_timeout=600,
        result_ttl=3600,
    )

    return JobCreateResponse(
        job_id=job.id,
        status=JobStatus.QUEUED,
        message="Data processing job created successfully"
    )


@router.post("/generate-report", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_report_job(payload: ReportJobCreate):
    """
    Create report generation job.

    Args:
        payload: Report job details

    Returns:
        Job creation response
    """
    queue = get_queue("default")

    job = queue.enqueue(
        generate_report_task,
        report_type=payload.report_type,
        parameters=payload.parameters,
        job_timeout=900,
        result_ttl=7200,
    )

    return JobCreateResponse(
        job_id=job.id,
        status=JobStatus.QUEUED,
        message="Report generation job created successfully"
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get job status.

    Args:
        job_id: Job ID

    Returns:
        Job details

    Raises:
        HTTPException: If job not found
    """
    redis_conn = get_redis_connection()

    try:
        job = RQJob.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Map RQ job status to our JobStatus
    status_mapping = {
        "queued": JobStatus.QUEUED,
        "started": JobStatus.STARTED,
        "finished": JobStatus.FINISHED,
        "failed": JobStatus.FAILED,
        "canceled": JobStatus.CANCELED,
    }

    job_status = status_mapping.get(job.get_status(), JobStatus.QUEUED)

    return JobResponse(
        job_id=job.id,
        job_type=JobType.EMAIL,  # TODO: Store job type in metadata
        status=job_status,
        created_at=job.created_at,
        started_at=job.started_at,
        ended_at=job.ended_at,
        result=job.result,
        error=job.exc_info if job.is_failed else None,
        meta=job.meta,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(job_id: str):
    """
    Cancel a job.

    Args:
        job_id: Job ID

    Raises:
        HTTPException: If job not found
    """
    redis_conn = get_redis_connection()

    try:
        job = RQJob.fetch(job_id, connection=redis_conn)
        job.cancel()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )


@router.get("/", response_model=JobListResponse)
async def list_jobs(limit: int = 50, offset: int = 0):
    """
    List all jobs.

    Args:
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip

    Returns:
        List of jobs
    """
    queue = get_queue("default")
    registry = queue.get_job_ids()

    # Get jobs with pagination
    job_ids = registry[offset:offset + limit]

    redis_conn = get_redis_connection()
    jobs = []

    for job_id in job_ids:
        try:
            rq_job = RQJob.fetch(job_id, connection=redis_conn)

            status_mapping = {
                "queued": JobStatus.QUEUED,
                "started": JobStatus.STARTED,
                "finished": JobStatus.FINISHED,
                "failed": JobStatus.FAILED,
                "canceled": JobStatus.CANCELED,
            }

            jobs.append(JobResponse(
                job_id=rq_job.id,
                job_type=JobType.EMAIL,  # TODO: Store in metadata
                status=status_mapping.get(rq_job.get_status(), JobStatus.QUEUED),
                created_at=rq_job.created_at,
                started_at=rq_job.started_at,
                finished_at=rq_job.ended_at,
                result=rq_job.result,
                error=rq_job.exc_info if rq_job.is_failed else None,
                meta=rq_job.meta,
            ))
        except Exception:
            continue  # Skip jobs that can't be fetched

    return JobListResponse(
        jobs=jobs,
        total=len(registry)
    )

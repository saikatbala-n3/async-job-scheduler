import time
import json
import asyncio
import logging

from sqlalchemy import select
from datetime import datetime, timezone

from app.core import queue
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.jobs.models import Job, JobStatus
from app.workers.task_handlers import get_handler
from app.metrics import active_workers, job_duration, jobs_processed, queue_depth

logger = logging.getLogger(__name__)


async def _update_status(job_id: str, status: JobStatus, **kwargs):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
        job.status = status
        for k, v in kwargs.items():
            setattr(job, k, v)
        await session.commit()


class AsyncWorker:
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.running = False

    async def start(self):
        self.running = True
        active_workers.inc()
        logger.info(f"Worker {self.worker_id} started")
        while self.running:
            try:
                job_data = await queue.dequeue(settings.job_queue)
                if job_data:
                    await self._process_job(job_data)
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)

        active_workers.dec()
        logger.info(f"Worker {self.worker_id} stopped")

    def stop(self):
        self.running = False
        # active_workers.dec()

    async def _process_job(self, job_data: dict):
        job_id = job_data.get("id")
        job_type = job_data.get("job_type")
        payload = job_data.get("payload")
        retry_count = job_data.get("retry_count", 0)
        lock_name = f"job:{job_id}"

        if not await queue.acquire_lock(lock_name):
            logger.info(f"Worker {self.worker_id} unable to aquire lock for {job_id})")
            return

        try:
            await _update_status(
                job_id, JobStatus.PROCESSING, started_at=datetime.now(timezone.utc)
            )
            handler = get_handler(job_type)
            if not handler:
                raise ValueError(f"No handler for job type: {job_type}")

            start_time = time.perf_counter()
            result = await handler(payload)
            duration = time.perf_counter() - start_time

            job_duration.labels(job_type=job_type).observe(duration)
            jobs_processed.labels(status="completed").inc()

            await _update_status(
                job_id,
                JobStatus.COMPLETED,
                result=json.dumps(result),
                completed_at=datetime.now(timezone.utc),
            )
            logger.info(
                f"Worker {self.worker_id} completed job {job_id} in {duration:.2f}"
            )

        except Exception as job_error:
            logger.error(f"Worker {self.worker_id}: Job {job_id} failed - {job_error}")
            if retry_count < settings.max_retries:
                await self._retry_job(job_data, str(job_error))
            else:
                await self._move_to_dlq(job_data, str(job_error))

        finally:
            await queue.release_lock(lock_name)
            queue_depth.set(await queue.queue_length(settings.job_queue))

    async def _retry_job(self, job_data: dict, error: str):
        retry_count = job_data.get("retry_count", 0) + 1
        delay = settings.retry_base_delay * (2 ** (retry_count - 1))

        logger.info(
            f"Retrying job {job_data['id']} "
            f"(attempt {retry_count}/{settings.max_retries}) "
            f"after {delay}s delay"
        )
        await _update_status(
            job_data["id"], JobStatus.RETRYING, retry_count=retry_count, error=error
        )
        await asyncio.sleep(delay)

        job_data["retry_count"] = retry_count
        await queue.enqueue(settings.job_queue, job_data)
        jobs_processed.labels(status="retrying").inc()

    async def _move_to_dlq(self, job_data: dict, error: str):
        logger.warning(f"Moving job {job_data['id']} to DLQ: {error}")
        await queue.enqueue(settings.job_dlq, {**job_data, "error": error})
        await _update_status(
            job_data["id"],
            JobStatus.FAILED,
            error=error,
            completed_at=datetime.now(timezone.utc),
        )
        jobs_processed.labels(status="failed").inc()


class WorkerPool:
    def __init__(self):
        self.workers = [AsyncWorker(i) for i in range(settings.worker_count)]
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        self.workers = [asyncio.create_task(w.start()) for w in self.workers]
        logger.info(f"Starting worker pool with {settings.worker_count} workers")

    async def stop(self):
        for worker in self.workers:
            worker.stop()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("Worker pool stopped")

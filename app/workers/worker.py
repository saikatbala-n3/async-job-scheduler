import asyncio
import logging
from datetime import datetime

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis_client import RedisClient
from app.models.job import JobStatus
from app.services.job_service import JobService
from app.schemas.job import JobUpdate
from app.workers.task_handlers import TaskHandlers

logger = logging.getLogger(__name__)


class AsyncWorker:
    """Async worker for processing tasks from Redis queue."""

    def __init__(self, worker_id: int, redis_client: RedisClient, concurrency: int = 1):
        """
        Initialize worker.

        Args:
            worker_id: Unique worker identifier
            redis_client: Redis client instance
            concurrency: Number of concurrent jobs this worker can handle
        """
        self.worker_id = worker_id
        self.redis = redis_client
        self.concurrency = concurrency
        self.running = False
        self.active_tasks = set()

    async def start(self):
        """Start the worker."""
        self.running = True
        logger.info(
            f"Worker {self.worker_id} started with concurrency={self.concurrency}"
        )
        while self.running:
            try:
                # Check if we have capacity
                if len(self.active_tasks) >= self.concurrency:
                    await asyncio.sleep(0.1)

                # Try to get job from queue
                job_data = await self.redis.dequeue(
                    settings.JOB_QUEUE_NAME, timeout=settings.WORKER_POLL_INTERVAL
                )

                if job_data:
                    # Create task for processing
                    task = asyncio.create_task(self._process_job(job_data))
                    self.active_tasks.add(task)
                    task.add_done_callback(self.active_tasks.discard)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop worker gracefully"""
        logger.info(f"Worker {self.worker_id} stopping...")
        self.running = False

        # Wait for active task to complete
        if self.active_tasks:
            logger.info(
                f"Waiting for {len(self.active_tasks)} active tasks to complete"
            )
            await asyncio.gather(*self.active_tasks, return_exceptions=True)

        logger.info(f"Worker {self.worker_id} stopped")

    async def _process_job(self, job_data: dict):
        """
        Process a single job.

        Args:
            job_data: Job data from queue
        """
        job_id = job_data.get("id")
        job_type = job_data.get("job_type")
        payload = job_data.get("payload")
        retry_count = job_data.get("retry_count", 0)

        logger.info(f"Worker {self.worker_id} processing job {job_id} ({job_type})")

        # Get database session
        async with AsyncSessionLocal() as db:
            try:
                # Aquire distributed lock to prevent duplicate processing
                lock_name = f"job:{job_id}"
                lock_acquired = await self.redis.acquire_lock(lock_name, timeout=300)

                if not lock_acquired:
                    logger.warning(f"Could not acquire locak for jon {job_id}")
                    return

                try:
                    # Update job status to PROCESSING
                    await JobService.update_job(
                        db, job_id, JobUpdate(status=JobStatus.PROCESSING)
                    )
                    await db.commit()

                    # Get handler for job type
                    handler = TaskHandlers.get_handler(job_type)

                    if not handler:
                        raise ValueError(f"No handler for job type: {job_type}")

                    # Execute job
                    result = await handler(payload)

                    # Update job status to COPLETED
                    await JobService.update_job(
                        db, job_id, JobUpdate(status=JobStatus.COMPLETED, result=result)
                    )
                    await db.commit()

                    logger.info(f"Worker {self.worker_id} completed job {job_id}")

                except Exception as job_error:
                    logger.error(f"Job {job_id} failed: {job_error}")

                    # Check if we should retry
                    if retry_count < settings.MAX_RETRIES:
                        # Re-enqueue for retry
                        await self._retry_job(job_data, str(job_error))
                        await JobService.update_job(
                            db,
                            job_id,
                            JobUpdate(status=JobStatus.RETRYING, error=str(job_error)),
                        )

                    else:
                        # Max retries exceeded, mark as failed
                        await JobService.update_job(
                            db,
                            job_id,
                            JobUpdate(status=JobStatus.FAILED, error=str(job_error)),
                        )

                        # Move to daed letter queue
                        await self._move_to_dlq(job_data, str(job_error))

                    await db.commit()

                finally:
                    # Release lock
                    await self.redis.release_lock(lock_name)

            except Exception as e:
                logger.error(f"Critical error processing job {job_id}: {e}")

    async def _retry_job(self, job_data: dict, error: str):
        """
        Re-enqueue job for retry with exponential backoff.

        Args:
            job_data: Original job data
            error: Error message
        """
        retry_count = job_data.get("retry_count", 0) + 1
        delay = settings.RETRY_DELAY * (2 ** (retry_count - 1))  # Exponential backoff

        logger.info(
            f"Retrying job {job_data['id']} "
            f"(attempt {retry_count}/{settings.MAX_RETRIES}) "
            f"after {delay}s delay"
        )

        # Wait for backoff period
        await asyncio.sleep(delay)

        # Re-enqueue
        job_data["retry_count"] = retry_count
        await self.redis.enqueue(settings.JOB_QUEUE_NAME, job_data)

    async def _move_to_dlq(self, job_data: dict, error: str):
        """
        Move failed job to dead letter queue.

        Args:
            job_data: Job data
            error: Error message
        """
        logger.warning(f"Moving job {job_data['id']} to DLQ: {error}")
        dlq_data = {
            **job_data,
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
        }

        await self.redis.enqueue(settings.JOB_DLQ_NAME, dlq_data)


class WorkerPool:
    """Pool of async workers."""

    def __init__(self, redis_client: RedisClient, num_workers: int = 5):
        """
        Initialize worker pool.

        Args:
            redis_client: Redis client instance
            num_workers: Number of workers in the pool
        """
        self.redis = redis_client
        self.num_workers = num_workers
        self.workers = []
        self.worker_tasks = []

    async def start(self):
        """Start all workers."""
        logger.info(f"Starting worker pool with {self.num_workers} workers")

        for i in range(self.num_workers):
            worker = AsyncWorker(
                worker_id=i,
                redis_client=self.redis,
                concurrency=settings.WORKER_CONCURRENCY // self.num_workers,
            )
            self.workers.append(worker)

            task = asyncio.create_task(worker.start())
            self.worker_tasks.append(task)

        logger.info("Worker pool started")

    async def stop(self):
        """Stop all workers gracefully."""
        logger.info("Stopping worker pool...")

        # Signal all workers to stop
        for worker in self.workers:
            await worker.stop()

        # Wait for all worker tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        logger.info("Worker pool stopped")

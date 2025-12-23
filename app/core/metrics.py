from prometheus_client import Counter, Histogram, Gauge, Summary
import time
from functools import wraps
from typing import Callable

# Job metrics
job_created_counter = Counter(
    "jobs_created_total", "Total number of jobs created", ["job_type"]
)

job_completed_counter = Counter(
    "jobs_completed_total", "Total number of jobs completed", ["job_type", "status"]
)

job_duration_histogram = Histogram(
    "job_duration_seconds",
    "Job processing duration in seconds",
    ["job_type"],
    buckets=(1, 2, 5, 10, 30, 60, 120, 300, 600, 1800),
)

job_retry_counter = Counter(
    "jobs_retried_total", "Total number of job retries", ["job_type"]
)

# Queue metrics
queue_depth_gauge = Gauge("queue_depth", "Current depth of job queue")

# Worker metrics
active_workers_gauge = Gauge("active_workers", "Number of active workers")

worker_jobs_processed = Counter(
    "worker_jobs_processed_total",
    "Total jobs processed by workers",
    ["worker_id", "status"],
)

# API metrics
api_requests_counter = Counter(
    "api_requests_total", "Total API requests", ["method", "endpoint", "status_code"]
)

api_request_duration = Summary(
    "api_request_duration_seconds", "API request duration", ["method", "endpoint"]
)


def track_job_duration(job_type: str):
    """
    Decorator to track job execution duration.

    Usage:
        @track_job_duration("email")
        async def process_email(payload):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                job_duration_histogram.labels(job_type=job_type).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                job_duration_histogram.labels(job_type=job_type).observe(duration)
                raise e

            return wrapper

        return decorator


def track_api_call(endpoint: Callable):
    """
    Decorator to track API call metrics.

    Usage:
        @track_api_call("/jobs")
        async def create_job(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                api_request_duration.labels(method="POST", endpoint=endpoint).observe(
                    duration
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                api_request_duration.labels(method="POST", endpoint=endpoint).observe(
                    duration
                )
                raise e

        return wrapper

    return decorator

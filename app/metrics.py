from prometheus_client import Counter, Gauge, Histogram

jobs_created = Counter(
    "jobs_created_total", "Jobs submitted to the scheduler", ["job_type"]
)
jobs_processed = Counter(
    "jobs_processed_total", "Jobs completed by workers", ["status"]
)
job_duration = Histogram(
    "job_duration_seconds",
    "Job processing time",
    ["job_type"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)
active_workers = Gauge("active_workers_total", "Number of running workers")
queue_depth = Gauge("queue_depth_total", "Jobs waiting in queue")

# Async Job Scheduler

Async job processing system with Redis queues, a worker pool, distributed locking, exponential backoff retry, and Prometheus/Grafana observability.

**Stack:** FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL 15 · Redis 7 · Prometheus · Grafana

---

## Features

- Redis list as job queue — `RPUSH` to enqueue, `BLPOP` to dequeue
- Worker pool (5 workers) processing jobs concurrently
- Distributed locking via Redis — prevents duplicate processing
- Exponential backoff retry: 5s → 10s → 20s, then dead letter queue
- Dead letter queue (`jobs:dlq`) for jobs that exhaust retries
- Prometheus metrics — queue depth, active workers, job duration, processed counts
- Tables created on startup via `create_all` — no migration tool needed

---

## Job Types

| Type | Behaviour |
|------|-----------|
| `work` | Simulates variable-duration work, always succeeds |
| `unreliable` | Fails 50% of the time — demonstrates retry and DLQ flow |

---

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Worker metrics | http://localhost:8001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

Swagger UI: http://localhost:8000/docs

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/jobs/` | Submit a new job |
| GET | `/jobs/{job_id}` | Get job by ID |
| GET | `/jobs/` | List jobs (filter by `status`, `type`) |
| POST | `/jobs/{job_id}/retry` | Manually retry a FAILED job |
| GET | `/jobs/stats` | Queue stats by status |
| GET | `/jobs/dlq` | Inspect dead letter queue (non-destructive) |

### Submit a job

```bash
# Always-succeeding job
curl -X POST http://localhost:8000/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"job_type": "work", "payload": {"duration": 2}}'

# Unreliable job — triggers retry/DLQ flow
curl -X POST http://localhost:8000/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"job_type": "unreliable", "payload": {}}'
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | — | Redis URL (`redis://...`) |
| `MAX_RETRIES` | `3` | Max automatic retries before DLQ |
| `RETRY_BASE_DELAY` | `5` | Base delay in seconds (doubles each attempt) |
| `WORKER_COUNT` | `5` | Number of concurrent workers |

---

## Project Structure

```
app/
├── jobs/           # Job CRUD — models, schemas, routes, service
├── workers/        # Worker pool, task handlers
├── core/           # Config, database session, Redis queue client
├── metrics.py      # Prometheus counters, gauges, histograms
└── worker_main.py  # Worker entry point
monitoring/
├── prometheus/     # prometheus.yml scrape config
└── grafana/        # Dashboard JSON
tests/
├── test_jobs.py
├── test_workers.py
└── load_test.py
```
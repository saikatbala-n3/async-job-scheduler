# Async Job Scheduler

A distributed async job scheduler with Redis queues, worker pools, distributed locking, and Prometheus/Grafana observability.

## Features

✨ **Job Management**
- REST API for job submission and monitoring
- Support for multiple job types (email, data processing, reports, etc.)
- Priority-based job scheduling
- Job status tracking and history

⚡ **Async Processing**
- Async worker pool with configurable concurrency
- Redis-based job queue
- Distributed locking (RedLock pattern)
- Exponential backoff retry mechanism
- Dead letter queue for failed jobs

📊 **Observability**
- Prometheus metrics collection
- Grafana dashboards with real-time metrics
- Job duration histograms (p50, p95, p99)
- Success rate tracking
- Queue depth monitoring

🔒 **Reliability**
- Distributed locks prevent duplicate processing
- Automatic retry with exponential backoff
- Dead letter queue for max retry failures
- Graceful worker shutdown

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────┐
│     FastAPI Job API             │
└──────────┬──────────────────────┘
           │
    ┌──────↓─────┐
    │ PostgreSQL │ (Job metadata)
    └────────────┘
           │
    ┌──────↓─────┐
    │   Redis    │ (Job queue + Locks)
    └──────┬─────┘
           │
    ┌──────↓──────────────┐
    │  Worker Pool (5)    │
    │  ┌────┬────┬────┐   │
    │  │ W1 │ W2 │... │   │
    │  └────┴────┴────┘   │
    └─────────────────────┘
           │
    ┌──────↓─────┐
    │ Prometheus │ → Grafana
    └────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15
- Redis 7

### Installation

1. **Clone repository**
```bash
git clone https://github.com/saikatbala/async-job-scheduler.git
cd async-job-scheduler
```

2. **Setup environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Option A: Docker (Recommended)

3. **Start all services** (API, Workers, PostgreSQL, Redis, Prometheus, Grafana)
```bash
docker compose up -d
```

All services will start automatically, including database migrations.

- API: http://localhost:8000
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

### Option B: Local Development

3. **Install dependencies**
```bash
# Using pip
pip install -e .

# Or using poetry
poetry install
```

4. **Update .env for local development**
```bash
# Change these values in .env:
POSTGRES_SERVER=localhost  # (currently set to 'db' for Docker)
REDIS_HOST=localhost       # (currently set to 'redis' for Docker)
```

5. **Start PostgreSQL and Redis**
```bash
docker compose up -d db redis
```

6. **Run migrations**
```bash
alembic upgrade head
```

7. **Start API**
```bash
uvicorn app.main:app --reload
```

8. **Start workers** (separate terminal)
```bash
python -m app.worker_main
```

Visit http://localhost:8000/docs for API documentation.

## API Usage

### Create Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "data_processing",
    "payload": {
      "file_url": "https://example.com/data.csv",
      "operation": "aggregate"
    },
    "priority": 5
  }'
```

### Get Job Status
```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### List Jobs
```bash
# All jobs
curl http://localhost:8000/api/v1/jobs/

# Filter by status
curl http://localhost:8000/api/v1/jobs/?status=completed

# Filter by type
curl http://localhost:8000/api/v1/jobs/?type=email
```

### Get Statistics
```bash
curl http://localhost:8000/api/v1/jobs/stats/summary
```

### Retry Failed Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/retry
```

## Job Types

### Email
```json
{
  "job_type": "email",
  "payload": {
    "to": "user@example.com",
    "subject": "Hello",
    "body": "Test email"
  }
}
```

### Data Processing
```json
{
  "job_type": "data_processing",
  "payload": {
    "file_url": "https://example.com/data.csv",
    "operation": "aggregate"
  }
}
```

### Report Generation
```json
{
  "job_type": "report_generation",
  "payload": {
    "report_type": "monthly_sales",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

### Image Processing
```json
{
  "job_type": "image_processing",
  "payload": {
    "image_url": "https://example.com/image.jpg",
    "filters": ["resize", "grayscale"]
  }
}
```

### Webhook
```json
{
  "job_type": "webhook",
  "payload": {
    "url": "https://example.com/webhook",
    "method": "POST",
    "data": {"event": "user_signup"}
  }
}
```

## Monitoring

### Prometheus Metrics

Access Prometheus: http://localhost:9090

**Available Metrics:**
- `jobs_created_total` - Total jobs created
- `jobs_completed_total` - Total jobs completed
- `job_duration_seconds` - Job processing duration
- `queue_depth` - Current queue depth
- `active_workers` - Number of active workers
- `jobs_retried_total` - Total job retries

### Grafana Dashboards

Access Grafana: http://localhost:3000 (admin/admin)

**Dashboard Panels:**
- Jobs Created Rate
- Job Success Rate
- Queue Depth (real-time)
- Job Duration Percentiles (p50, p95, p99)
- Active Workers
- Jobs by Type

## Configuration

Edit `.env` file:

```bash
# Database
# For Docker: use 'db' (service name)
# For local: use 'localhost'
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=job_scheduler

# Redis
# For Docker: use 'redis' (service name)
# For local: use 'localhost'
REDIS_HOST=redis
REDIS_PORT=6379

# Job Configuration
MAX_RETRIES=3
RETRY_DELAY=5

# Worker Configuration
WORKER_CONCURRENCY=10
WORKER_POLL_INTERVAL=1
```

**Note**: The `.env` file is currently configured for Docker deployment. For local development, change `POSTGRES_SERVER=db` to `localhost` and `REDIS_HOST=redis` to `localhost`.

## Performance

- **Throughput**: 10,000+ jobs/hour
- **Scheduling Latency**: <50ms
- **Job Duration**: Depends on job type (1-10s typical)
- **Success Rate**: 95%+ (with retries)
- **Worker Pool**: 5 workers, 10 concurrent jobs each

## Development

### Running Tests
```bash
pytest --cov=app
```

### Code Formatting
```bash
./scripts/format.sh
```

### Linting
```bash
./scripts/lint.sh
```

## Project Structure

```
async-job-scheduler/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Configuration & clients
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── workers/          # Async workers
│   └── main.py           # FastAPI app
├── monitoring/
│   ├── grafana/          # Dashboards
│   └── prometheus/       # Config
├── tests/                # Test suite
└── docker-compose.yml    # Services orchestration
```

## Deployment

### Docker
```bash
docker-compose up -d
```

### Production Considerations
- Use persistent volumes for PostgreSQL and Redis
- Configure worker pool size based on CPU cores
- Set up log aggregation (ELK stack)
- Enable authentication for Grafana
- Use secrets management for credentials
- Set up alerts in Grafana

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests
4. Submit pull request

## License

MIT License

## Author

**Saikat Bala**
- GitHub: [@saikatbala](https://github.com/saikatbala)
- LinkedIn: [saikat-bala](https://www.linkedin.com/in/saikat-bala-6b827299/)

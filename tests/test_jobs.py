import pytest
from httpx import AsyncClient
# from app.models.job import JobStatus, JobType


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient):
    """Test job creation."""
    response = await client.post(
        "/api/v1/jobs/",
        json={
            "job_type": "email",
            "payload": {"to": "test@example.com", "subject": "Test"},
            "priority": 5,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "email"
    assert data["status"] == "queued"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_job(client: AsyncClient):
    """Test getting job by ID."""
    # Create job
    create_response = await client.post(
        "/api/v1/jobs/",
        json={
            "job_type": "data_processing",
            "payload": {"file": "test.csv"},
            "priority": 3,
        },
    )
    job_id = create_response.json()["id"]

    # Get job
    response = await client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["job_type"] == "data_processing"


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient):
    """Test listing jobs."""
    # Create multiple jobs
    for i in range(3):
        await client.post(
            "/api/v1/jobs/",
            json={
                "job_type": "email",
                "payload": {"to": f"test{i}@example.com"},
                "priority": 5,
            },
        )

    # List jobs
    response = await client.get("/api/v1/jobs/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_job_stats(client: AsyncClient):
    """Test job statistics."""
    response = await client.get("/api/v1/jobs/stats/summary")

    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "queue_depth" in data
    assert "success_rate" in data


@pytest.mark.asyncio
async def test_filter_jobs_by_status(client: AsyncClient):
    """Test filtering jobs by status."""
    response = await client.get("/api/v1/jobs/?status=queued")

    assert response.status_code == 200
    data = response.json()
    for job in data:
        assert job["status"] == "queued"

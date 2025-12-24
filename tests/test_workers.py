import pytest

# import asyncio
# from app.workers.worker import AsyncWorker
from app.workers.task_handlers import TaskHandlers
from app.core.redis_client import RedisClient


@pytest.mark.asyncio
async def test_email_handler():
    """Test email task handler."""
    payload = {"to": "test@example.com", "subject": "Test Email"}

    result = await TaskHandlers.handle_email(payload)

    assert result["status"] == "sent"
    assert result["to"] == "test@example.com"


@pytest.mark.asyncio
async def test_data_processing_handler():
    """Test data processing handler."""
    payload = {"file_url": "https://example.com/data.csv", "operation": "aggregate"}

    result = await TaskHandlers.handle_data_processing(payload)

    assert result["status"] == "processed"
    assert result["file_url"] == payload["file_url"]
    assert "rows_processed" in result


@pytest.mark.asyncio
async def test_worker_processing(redis_client: RedisClient):
    """Test worker job processing."""
    # This is an integration test
    # In real scenario, you'd use fakeredis for unit testing

    job_data = {
        "id": "test-job-1",
        "job_type": "email",
        "payload": {"to": "test@example.com", "subject": "Test"},
        "priority": 5,
        "retry_count": 0,
    }

    # Enqueue job
    await redis_client.enqueue("test:queue", job_data)

    # Verify job is in queue
    queue_length = await redis_client.queue_length("test:queue")
    assert queue_length == 1

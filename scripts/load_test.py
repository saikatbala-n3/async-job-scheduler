import asyncio
import aiohttp
import time
from datetime import datetime


async def create_job(session, job_type, job_num):
    """Create a single job."""
    payload = {
        "job_type": job_type,
        "payload": {"task_id": job_num, "timestamp": datetime.utcnow().isoformat()},
        "priority": 5,
    }

    async with session.post(
        "http://localhost:8000/api/v1/jobs/", json=payload
    ) as response:
        return await response.json()


async def load_test(num_jobs=1000, concurrency=50):
    """
    Run load test.

    Args:
        num_jobs: Total number of jobs to create
        concurrency: Number of concurrent requests
    """
    print(f"Starting load test: {num_jobs} jobs with concurrency={concurrency}")

    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = []

        for i in range(num_jobs):
            job_type = ["email", "data_processing", "webhook"][i % 3]
            task = create_job(session, job_type, i)
            tasks.append(task)

            # Limit concurrency
            if len(tasks) >= concurrency:
                await asyncio.gather(*tasks)
                tasks = []

        # Process remaining tasks
        if tasks:
            await asyncio.gather(*tasks)

    duration = time.time() - start_time
    rate = num_jobs / duration

    print("\n=== Load Test Results ===")
    print(f"Total Jobs: {num_jobs}")
    print(f"Duration: {duration:.2f}s")
    print(f"Rate: {rate:.2f} jobs/second")
    print(f"Average Latency: {(duration / num_jobs) * 1000:.2f}ms")


if __name__ == "__main__":
    asyncio.run(load_test(num_jobs=1000, concurrency=50))

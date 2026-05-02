import asyncio
import logging
import signal

from prometheus_client import start_http_server

from app.core import queue
from app.core.database import Base, engine
from app.jobs.models import Job
from app.workers.worker import WorkerPool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    start_http_server(8001)  # exposes worker metrics for Prometheus scraping
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await queue.connect()

    pool = WorkerPool()
    await pool.start()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(pool)))

    await asyncio.Event().wait()


async def shutdown(pool: WorkerPool):
    logger.info("Shutdown signal received")
    await pool.stop()
    await queue.disconnect()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

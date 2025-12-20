import asyncio
import logging
import signal
from app.core.redis_client import redis_client
from app.workers.worker import WorkerPool

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global worker pool and shutdown flag
worker_pool = None
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_requested = True


async def main():
    """Main worker entry point."""
    global worker_pool

    try:
        # Connect to Redis
        logger.info("Connecting to Redis...")
        await redis_client.connect()

        # Create and start worker pool
        worker_pool = WorkerPool(redis_client, num_workers=5)
        await worker_pool.start()

        # Keep running until shutdown signal or interrupt
        logger.info("Worker pool running. Press Ctrl+C to stop.")
        while not shutdown_requested:
            await asyncio.sleep(0.5)
        logger.info("Shutdown signal received, stopping workers...")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        # Cleanup
        if worker_pool:
            await worker_pool.stop()
        await redis_client.disconnect()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run main loop
    asyncio.run(main())

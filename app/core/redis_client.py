import asyncio
import json
from typing import Optional, Any
from redis.asyncio import Redis, ConnectionPool

from app.core.config import settings


class RedisClient:
    """Redis client wrapper for job queue operations."""

    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[Redis] = None

    async def connect(self):
        """Create Redis connection pool."""
        self.pool = ConnectionPool.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True,
            max_connections=100,  # Increase from 50
        )
        self.redis = Redis(connection_pool=self.pool)

        # Test connection
        await self.redis.ping()
        print("✓ Redis connected")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
        print("✓ Redis disconnected")

    # Queue Operations
    async def enqueue(self, queue_name: str, job_data: dict) -> int:
        """
        Add job to queue (right push).

        Args:
            queue_name: Queue name
            job_data: Job data dictionary

        Returns:
            Queue length after enqueue
        """
        job_json = json.dumps(job_data)
        return await self.redis.rpush(queue_name, job_json)

    async def dequeue(self, queue_name: str, timeout: int = 1) -> Optional[dict]:
        """
        Remove and return job from queue (blocking left pop).

        Args:
            queue_name: Queue name
            timeout: Block timeout in seconds

        Returns:
            Job data or None
        """
        result = await self.redis.blpop(queue_name, timeout=timeout)
        if result:
            _, job_json = result
            return json.loads(job_json)
        return None

    async def queue_length(self, queue_name: str) -> int:
        """Get queue length."""
        return await self.redis.llen(queue_name)

    # Key-Value Operations
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set key-value with optional expiration.

        Args:
            key: Redis key
            value: Value (will be JSON serialized)
            expire: Expiration in seconds

        Returns:
            True if successful
        """
        value_json = json.dumps(value)
        if expire:
            return await self.redis.setex(key, expire, value_json)
        return await self.redis.set(key, value_json)

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def delete(self, key: str) -> int:
        """Delete key."""
        return await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.redis.exists(key) > 0

    # Lock Operations (for distributed locking)
    async def acquire_lock(
        self, lock_name: str, timeout: int = 10, blocking_timeout: Optional[int] = None
    ) -> bool:
        """
        Acquire distributed lock.

        Args:
            lock_name: Lock identifier
            timeout: Lock expiration in seconds
            blocking_timeout: How long to wait for lock

        Returns:
            True if lock acquired
        """
        lock_key = f"lock:{lock_name}"

        if blocking_timeout:
            # Blocking acquire
            import time

            end_time = time.time() + blocking_timeout
            while time.time() < end_time:
                if await self.redis.set(lock_key, "1", nx=True, ex=timeout):
                    return True
                await asyncio.sleep(0.1)
            return False
        else:
            # Non-blocking acquire
            return await self.redis.set(lock_key, "1", nx=True, ex=timeout)

    async def release_lock(self, lock_name: str):
        """Release distributed lock."""
        lock_key = f"lock:{lock_name}"
        await self.redis.delete(lock_key)


# Global instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client."""
    return redis_client

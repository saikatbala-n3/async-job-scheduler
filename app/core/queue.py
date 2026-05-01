import json

from redis.asyncio import Redis

from app.core.config import settings

_redis: Redis | None = None


async def connect():
    global _redis
    _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()


async def disconnect():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


def client():
    return _redis


async def enqueue(queue_name: str, job_data: dict) -> int:
    return await _redis.rpush(queue_name, json.dumps(job_data, default=str))


async def dequeue(queue_name: str, timeout: int = 1):
    """Blocking pop — waits up to `timeout` seconds for a job."""
    result = await _redis.blpop(queue_name, timeout=timeout)
    if result:
        _, job_json = result
        return json.loads(job_json)
    return None


async def queue_length(queue_name: str) -> int:
    return await _redis.llen(queue_name)


async def acquire_lock(lock_name: str, timeout: int = 30) -> bool:
    """Atomic SET NX — returns True only if lock was acquired."""
    return await _redis.set(f"lock:{lock_name}", "1", nx=True, ex=timeout)


async def release_lock(lock_name: str):
    await _redis.delete(f"lock:{lock_name}")

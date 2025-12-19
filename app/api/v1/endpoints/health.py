from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.redis_client import get_redis, RedisClient


router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db), redis: RedisClient = Depends(get_redis)
):
    """
    Health check endpoint.

    Returns service health status.
    """
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        if redis.redis:
            await redis.redis.ping()
            redis_status = "healthy"
        else:
            redis_status = "not connected"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    return {"status": "ok", "database": db_status, "redis": redis_status}

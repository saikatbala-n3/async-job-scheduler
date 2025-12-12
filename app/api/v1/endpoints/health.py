"""Health check endpoints."""
from fastapi import APIRouter, status

from app.core.redis import get_redis_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    # Check Redis connection
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok",
        "redis": redis_status,
    }

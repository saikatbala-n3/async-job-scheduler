from fastapi import APIRouter

from app.api.v1.endpoints import jobs, health


api_router = APIRouter()

# Include routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

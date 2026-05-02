import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core import queue
from app.core.database import Base, engine
from app.jobs.models import Job  # registers model before create_all
from app.jobs.routes import router as jobs_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await queue.connect()
    yield
    await queue.disconnect()
    await engine.dispose()


app = FastAPI(
    title="Async Job Scheduler",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(jobs_router)
app.mount("/metrics", make_asgi_app())


@app.get("/health")
async def health():
    return {"status": "healthy"}

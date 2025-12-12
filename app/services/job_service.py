import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobType
from app.schemas.job import JobCreate, JobUpdate, JobStats
from app.core.redis import RedisClient
from app.core.config import settings

class JobService
import asyncio
import random

from collections.abc import Callable


async def handle_work(payload: dict):
    duration = max(0.1, float(payload.get("duration", 1)))
    await asyncio.sleep(duration)
    return {"status": "done", "duration": duration}


async def handle_unreliable(payload: dict):
    """Fail 50% of the time."""
    if random.random() < 0.5:
        raise RuntimeError("Job failed - triggering retry and dlq")
    return {"status": "done"}


DISPATCH: dict[str, Callable] = {
    "work": handle_work,
    "unreliable": handle_unreliable,
}


def get_handler(job_type: str):
    return DISPATCH.get(job_type)

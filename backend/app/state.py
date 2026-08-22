"""In-memory job store shared across API routers. Fine for a single-process
MVP; swap for Redis/DB before running more than one worker.
"""

from fastapi import HTTPException

from app.models.schemas import Job

jobs: dict[str, Job] = {}


def get_ready_job(job_id: str) -> Job:
    """A job that exists and has a transcript attached (background/render/export all need this)."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.result is None:
        raise HTTPException(status_code=409, detail="job has no transcript yet")
    return job

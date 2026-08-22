"""In-memory job store shared across API routers. Fine for a single-process
MVP; swap for Redis/DB before running more than one worker.
"""

from app.models.schemas import Job

jobs: dict[str, Job] = {}

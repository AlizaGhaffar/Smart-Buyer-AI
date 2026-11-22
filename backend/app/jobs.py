"""In-memory background jobs for searches (one search takes ~1-3 minutes)."""

from __future__ import annotations

import copy
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 3600
MAX_JOBS = 50


class JobStore:
    def __init__(self, workers: int = 2):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="search-job")

    def submit(self, fn, *, describe: dict) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._expire()
            self._jobs[job_id] = {
                "job_id": job_id, "status": "queued", "stage": "queued",
                "progress": {"done": 0, "total": 0, "message": "Waiting to start"},
                "request": describe, "result": None, "error": None, "created": time.time(),
            }

        def progress(stage, done, total, message=""):
            self._update(job_id, status="running", stage=stage,
                         progress={"done": done, "total": total, "message": message})

        def run():
            self._update(job_id, status="running", stage="starting")
            try:
                result = fn(progress)
                self._update(job_id, status="done", stage="done", result=result,
                             progress={"done": 1, "total": 1, "message": "Finished"})
            except Exception as error:  # reported to the client, never swallowed
                logger.exception("Search job %s failed", job_id)
                message = str(error) if isinstance(error, (RuntimeError, FileNotFoundError, ValueError)) \
                    else "The search failed unexpectedly. Please try again."
                self._update(job_id, status="failed", stage="failed", error=message)

        self._pool.submit(run)
        return job_id

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return copy.deepcopy({k: v for k, v in job.items() if k != "created"}) if job else None

    def _update(self, job_id: str, **changes) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(changes)

    def _expire(self) -> None:
        now = time.time()
        for jid in [j for j, v in self._jobs.items() if now - v["created"] > JOB_TTL_SECONDS]:
            del self._jobs[jid]
        while len(self._jobs) >= MAX_JOBS:
            del self._jobs[min(self._jobs, key=lambda j: self._jobs[j]["created"])]

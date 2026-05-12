"""In-process ingestion job queue with persistent status tracking.

This module provides a thread-safe in-process job queue for ingestion runs.
Jobs are executed synchronously in the calling thread (no background threads),
which is appropriate for the current single-process deployment.

For production deployments, replace ``InProcessIngestionQueue`` with a
Celery/ARQ/Redis-backed implementation that uses the same interface.

Usage::

    from app.workers.ingestion_queue import get_ingestion_queue

    queue = get_ingestion_queue()
    job_id = queue.enqueue("federal_court_canada")
    status = queue.get_status(job_id)
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionJobRecord:
    """Tracks the state of a single ingestion job."""

    job_id: str
    source_key: str
    state: JobState = JobState.PENDING
    enqueued_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    run_id: int | None = None
    records_fetched: int = 0
    review_items: int = 0
    created_records: int = 0
    raw_snapshot_preserved: bool = False
    error: str | None = None
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_key": self.source_key,
            "state": self.state.value,
            "enqueued_at": self.enqueued_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "run_id": self.run_id,
            "records_fetched": self.records_fetched,
            "review_items": self.review_items,
            "created_records": self.created_records,
            "raw_snapshot_preserved": self.raw_snapshot_preserved,
            "error": self.error,
        }


class InProcessIngestionQueue:
    """Thread-safe in-process ingestion job queue.

    Jobs are executed synchronously when ``run_next()`` is called.
    The queue maintains a history of all job records for status queries.

    In production, replace this with a Celery/ARQ task queue that calls
    ``run_ingestion_job()`` from ``app.workers.jobs.ingestion_run``.
    """

    def __init__(self, max_history: int = 500) -> None:
        self._lock = threading.Lock()
        self._pending: list[str] = []  # ordered list of job_ids
        self._records: dict[str, IngestionJobRecord] = {}
        self._max_history = max_history

    def enqueue(self, source_key: str) -> str:
        """Add a source ingestion job to the queue.

        Returns the job_id for status tracking.
        """
        job_id = str(uuid.uuid4())
        record = IngestionJobRecord(job_id=job_id, source_key=source_key)
        with self._lock:
            self._records[job_id] = record
            self._pending.append(job_id)
        logger.info("Enqueued ingestion job %s for source %s", job_id, source_key)
        return job_id

    def run_next(self) -> IngestionJobRecord | None:
        """Execute the next pending job synchronously.

        Returns the completed job record, or None if the queue is empty.
        """
        from app.workers.jobs.ingestion_run import run_ingestion_job

        with self._lock:
            if not self._pending:
                return None
            job_id = self._pending.pop(0)
            record = self._records[job_id]
            record.state = JobState.RUNNING
            record.started_at = time.time()

        logger.info("Starting ingestion job %s for source %s", job_id, record.source_key)

        try:
            result = run_ingestion_job({"source_key": record.source_key})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingestion job %s failed with exception", job_id)
            with self._lock:
                record.state = JobState.FAILED
                record.finished_at = time.time()
                record.error = str(exc)
            return record

        with self._lock:
            record.finished_at = time.time()
            record.result = result
            if result.get("ok"):
                record.state = JobState.COMPLETED
                record.run_id = result.get("run_id")
                record.records_fetched = result.get("records_fetched", 0)
                record.review_items = result.get("review_items", 0)
                record.created_records = result.get("created_records", 0)
                record.raw_snapshot_preserved = result.get("raw_snapshot_preserved", False)
            else:
                record.state = JobState.FAILED
                record.error = result.get("message", "Unknown error")

        logger.info(
            "Ingestion job %s finished: state=%s records=%d",
            job_id, record.state.value, record.records_fetched,
        )
        self._evict_old_records()
        return record

    def run_job(self, job_id: str) -> IngestionJobRecord | None:
        """Execute a specific job by ID (must be in PENDING state).

        Returns the completed record, or None if job_id not found.
        """
        with self._lock:
            record = self._records.get(job_id)
            if record is None or record.state != JobState.PENDING:
                return record
            # Move to front of pending queue
            if job_id in self._pending:
                self._pending.remove(job_id)
                self._pending.insert(0, job_id)

        return self.run_next()

    def get_status(self, job_id: str) -> IngestionJobRecord | None:
        """Return the job record for job_id, or None if not found."""
        with self._lock:
            return self._records.get(job_id)

    def list_jobs(self, state: JobState | None = None) -> list[IngestionJobRecord]:
        """Return all job records, optionally filtered by state."""
        with self._lock:
            records = list(self._records.values())
        if state is not None:
            records = [r for r in records if r.state == state]
        return sorted(records, key=lambda r: r.enqueued_at, reverse=True)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def _evict_old_records(self) -> None:
        """Remove oldest completed/failed records when history is full."""
        with self._lock:
            finished = [
                r for r in self._records.values()
                if r.state in (JobState.COMPLETED, JobState.FAILED)
            ]
            if len(finished) > self._max_history:
                # Sort by finished_at, remove oldest
                finished.sort(key=lambda r: r.finished_at or 0)
                to_remove = finished[: len(finished) - self._max_history]
                for r in to_remove:
                    del self._records[r.job_id]


# Module-level singleton queue
_QUEUE: InProcessIngestionQueue | None = None
_QUEUE_LOCK = threading.Lock()


def get_ingestion_queue() -> InProcessIngestionQueue:
    """Return the process-wide ingestion queue singleton."""
    global _QUEUE
    if _QUEUE is None:
        with _QUEUE_LOCK:
            if _QUEUE is None:
                _QUEUE = InProcessIngestionQueue()
    return _QUEUE

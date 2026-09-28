from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from packages.persistence.repositories.job import JobRepository


class FakeResult:
    def __init__(self, rows): self._rows = rows
    def scalars(self): return self
    def all(self): return self._rows
    def scalar_one_or_none(self): return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(self, job):
        self.job = job
        self.flushed = False
    async def execute(self, _stmt): return FakeResult([self.job])
    async def flush(self): self.flushed = True


@pytest.mark.asyncio
async def test_mark_error_requeues_with_backoff_until_max_attempts():
    job = type("Job", (), {"id": uuid4(), "attempts": 1, "max_attempts": 3,
                            "locked_at": datetime.now(UTC), "locked_by": "w",
                            "status": "running", "error": None,
                            "available_at": datetime.now(UTC)})()
    repo = JobRepository(FakeSession(job))
    await repo.mark_error(job.id, "boom")
    assert job.status == "queued"
    assert job.error == "boom"
    assert job.available_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_stale_job_reaches_failed_after_last_attempt():
    job = type("Job", (), {"id": uuid4(), "attempts": 3, "max_attempts": 3,
                            "locked_at": datetime.now(UTC) - timedelta(seconds=600),
                            "locked_by": "w", "status": "running"})()
    repo = JobRepository(FakeSession(job))
    assert await repo.requeue_stale(300) == 1
    assert job.status == "failed"


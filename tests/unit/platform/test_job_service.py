from datetime import UTC, datetime
from uuid import uuid4

import pytest
from packages.platform.job_service import JobService


class Repo:
    async def create(self, *args):
        return type("Job", (), {
            "id": uuid4(), "job_type": args[2], "payload": args[3],
            "idempotency_key": args[4], "created_at": datetime.now(UTC), "attempts": 0,
        })()

    async def commit(self):
        return None


class Queue:
    def __init__(self):
        self.jobs = []

    async def enqueue(self, job):
        self.jobs.append(job)
        return "1-0"


@pytest.mark.asyncio
async def test_service_persists_then_enqueues():
    queue = Queue()
    service = JobService(Repo(), queue)
    job = await service.enqueue(uuid4(), uuid4(), "demo", {"x": 1}, "key")
    assert job.job_type == "demo"
    assert queue.jobs[0].job_id == job.job_id

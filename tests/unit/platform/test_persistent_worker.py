from datetime import UTC, datetime
from uuid import uuid4

import pytest
from packages.platform.jobs import JobEnvelope
from packages.platform.persistent_worker import PersistentJobWorker


class FakeRepo:
    def __init__(self, job):
        self.job, self.completed, self.failed = job, [], []
        self.commits = 0

    async def claim(self, consumer):
        return self.job

    async def complete(self, job_id, result=None):
        self.completed.append((job_id, result))

    async def mark_error(self, job_id, error):
        self.failed.append((job_id, error))

    async def commit(self):
        self.commits += 1


def model_stub():
    return type("Job", (), {
        "id": uuid4(), "job_type": "demo", "payload": {"x": 1},
        "idempotency_key": "k", "created_at": datetime.now(UTC), "attempts": 1,
    })()


@pytest.mark.asyncio
async def test_worker_completes_successful_job():
    repo = FakeRepo(model_stub())
    seen = []

    async def handler(envelope: JobEnvelope):
        seen.append(envelope)
        return True

    worker = PersistentJobWorker(repo, "worker-1", handler)
    assert await worker.process_once() is True
    assert seen[0].job_id == repo.job.id
    assert repo.completed and not repo.failed and repo.commits == 1


@pytest.mark.asyncio
async def test_worker_records_handler_failure():
    repo = FakeRepo(model_stub())

    async def handler(_envelope: JobEnvelope):
        return False

    worker = PersistentJobWorker(repo, "worker-1", handler)
    assert await worker.process_once() is False
    assert repo.failed and repo.commits == 1

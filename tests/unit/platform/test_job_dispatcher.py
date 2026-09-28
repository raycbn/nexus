from uuid import uuid4

import pytest
from packages.platform.job_dispatcher import JobDispatcher
from packages.platform.job_types import DISCOVERY_SCHEDULE_JOB
from packages.platform.jobs import JobEnvelope


@pytest.mark.asyncio
async def test_dispatches_scheduled_discovery():
    envelope = JobEnvelope.create(DISCOVERY_SCHEDULE_JOB, {"schedule_id": str(uuid4())}, "k")
    calls: list[str] = []

    async def discovery(job):
        calls.append(job.job_type)
        return True

    async def remediation(job):
        calls.append("wrong")
        return True

    assert await JobDispatcher(discovery, remediation)(envelope) is True
    assert calls == [DISCOVERY_SCHEDULE_JOB]


@pytest.mark.asyncio
async def test_dispatches_autonomous_remediation():
    envelope = JobEnvelope.create("remediation.autonomous", {}, "k")
    calls: list[str] = []

    async def discovery(job):
        calls.append("wrong")
        return True

    async def remediation(job):
        calls.append(job.job_type)
        return True

    assert await JobDispatcher(discovery, remediation)(envelope) is True
    assert calls == ["remediation.autonomous"]


@pytest.mark.asyncio
async def test_rejects_unknown_job_type():
    envelope = JobEnvelope.create("unknown", {}, "k")

    async def handler(job):
        return True

    assert await JobDispatcher(handler, handler)(envelope) is False

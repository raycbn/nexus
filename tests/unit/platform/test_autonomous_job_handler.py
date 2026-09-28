from uuid import uuid4

import pytest
from packages.platform.autonomous_job_handler import AutonomousJobHandler
from packages.platform.job_types import AUTONOMOUS_REMEDIATION, AutonomousRemediationJob
from packages.platform.jobs import JobEnvelope


@pytest.mark.asyncio
async def test_handler_dispatches_valid_autonomous_job():
    job = AutonomousRemediationJob(uuid4(), uuid4(), None, uuid4(), uuid4(), uuid4())
    seen = []

    async def execute(value):
        seen.append(value)
        return True

    envelope = JobEnvelope.create(AUTONOMOUS_REMEDIATION, job.to_payload(), "k")
    assert await AutonomousJobHandler(execute)(envelope) is True
    assert seen == [job]


@pytest.mark.asyncio
async def test_handler_rejects_unknown_job_type():
    async def execute(_value):
        return True

    envelope = JobEnvelope.create("unknown", {}, "k")
    assert await AutonomousJobHandler(execute)(envelope) is False

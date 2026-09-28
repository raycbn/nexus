from uuid import uuid4

import pytest
from packages.platform.job_types import AUTONOMOUS_REMEDIATION, AutonomousRemediationJob


def test_autonomous_job_round_trips_payload():
    job = AutonomousRemediationJob(uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4())
    restored = AutonomousRemediationJob.from_payload(job.to_payload())
    assert restored == job
    assert AUTONOMOUS_REMEDIATION == "remediation.autonomous"


def test_autonomous_job_rejects_incomplete_payload():
    with pytest.raises(ValueError, match="incomplete"):
        AutonomousRemediationJob.from_payload({"action_id": str(uuid4())})

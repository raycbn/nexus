from datetime import UTC
from uuid import UUID

import pytest
from packages.platform.jobs import JobEnvelope


def test_create_job_has_uuid_and_utc_timestamp():
    job = JobEnvelope.create("remediation.execute", {"action_id": "a"}, "key-1")
    assert isinstance(job.job_id, UUID)
    assert job.created_at.tzinfo == UTC
    assert job.attempt == 0


def test_job_round_trip():
    job = JobEnvelope.create("remediation.execute", {"x": 1}, "key-2")
    assert JobEnvelope.from_dict(job.to_dict()) == job


@pytest.mark.parametrize("job_type,key", [("", "x"), ("x", "")])
def test_create_rejects_empty_identity(job_type, key):
    with pytest.raises(ValueError):
        JobEnvelope.create(job_type, {}, key)

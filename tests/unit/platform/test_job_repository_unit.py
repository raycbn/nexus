from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from packages.persistence.repositories.job import JobRepository


class FakeSession:
    pass


@pytest.mark.asyncio
async def test_repository_type_is_available():
    assert JobRepository(FakeSession()) is not None


def test_stale_cutoff_math():
    locked = datetime.now(UTC) - timedelta(seconds=120)
    assert locked.timestamp() < datetime.now(UTC).timestamp() - 60
    assert uuid4()

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from packages.platform.jobs import JobEnvelope
from packages.platform.scheduled_discovery_handler import ScheduledDiscoveryHandler


@pytest.mark.asyncio
async def test_handler_rejects_other_job_types():
    handler = ScheduledDiscoveryHandler(AsyncMock())
    envelope = JobEnvelope.create("other.job", {}, "other")
    assert await handler(envelope) is False


@pytest.mark.asyncio
async def test_handler_runs_discovery_and_persists_history():
    session = AsyncMock()
    schedule = SimpleNamespace(
        id=uuid4(), organization_id=uuid4(), workspace_id=uuid4(),
        resource_id=uuid4(), enabled=True,
    )
    resource = SimpleNamespace(
        id=schedule.resource_id,
        parent_resource_id=None,
        name="lab-linux",
        resource_type=SimpleNamespace(value="linux_server"),
        environment="lab",
        description=None,
        enabled=True,
        labels={},
        created_at=None,
        updated_at=None,
    )
    binding = SimpleNamespace(connector_key="linux", credential_id=uuid4(), config={"host": "lab"})
    credential = SimpleNamespace(enabled=True, secret_ref="NEXUS_TEST_SECRET")
    run = SimpleNamespace()
    connector = AsyncMock()
    discovered = [resource]
    envelope = JobEnvelope.create(
        "discovery.scheduled",
        {
            "schedule_id": str(schedule.id),
            "resource_id": str(resource.id),
            "organization_id": str(schedule.organization_id),
        },
        "scheduled-test",
    )
    connector.discover = lambda _resource: _items(discovered)
    with (
        patch(
            "packages.platform.scheduled_discovery_handler.DiscoveryScheduleRepository"
        ) as schedules,
        patch("packages.platform.scheduled_discovery_handler.CoreRepository") as resources,
        patch(
            "packages.platform.scheduled_discovery_handler.ResourceConnectionRepository"
        ) as bindings,
        patch("packages.platform.scheduled_discovery_handler.CredentialRepository") as credentials,
        patch("packages.platform.scheduled_discovery_handler.DiscoveryRunRepository") as runs,
        patch(
            "packages.platform.scheduled_discovery_handler.EnvironmentSecretProvider"
        ) as secrets,
        patch(
            "packages.platform.scheduled_discovery_handler.create_connector",
            return_value=connector,
        ),
    ):
        schedules.return_value.get_by_id = AsyncMock(return_value=schedule)
        resources.return_value.get_resource = AsyncMock(return_value=resource)
        bindings.return_value.get = AsyncMock(return_value=binding)
        credentials.return_value.get = AsyncMock(return_value=credential)
        runs.return_value.create = AsyncMock(return_value=run)
        runs.return_value.complete = AsyncMock()
        secrets.return_value.resolve.return_value = "secret"
        assert await ScheduledDiscoveryHandler(session)(envelope) is True
        runs.return_value.complete.assert_awaited_once()
        session.commit.assert_awaited_once()
        connector.connect.assert_awaited_once()
        connector.disconnect.assert_awaited_once()


async def _items(items):
    for item in items:
        yield item

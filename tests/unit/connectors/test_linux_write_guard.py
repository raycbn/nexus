from uuid import uuid4

import pytest
from packages.connectors.base.models import WriteAction
from packages.connectors.providers.linux import LinuxConnector
from packages.connectors.write_runner import RecordingWriteRunner
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


def resource(environment="lab"):
    return Resource(
        id=uuid4(), organization_id=uuid4(), name="lab-linux",
        resource_type=ResourceType.LINUX_SERVER, environment=environment,
    )


def test_write_capability_is_disabled_by_default(monkeypatch):
    monkeypatch.setenv("REMEDIATION_WRITES_ENABLED", "false")
    connector = LinuxConnector(resource(), "localhost", "nexus", "key")
    assert connector.capabilities.write is False


@pytest.mark.asyncio
async def test_write_runner_is_structured(monkeypatch):
    monkeypatch.setenv("REMEDIATION_WRITES_ENABLED", "true")
    monkeypatch.setenv("REMEDIATION_KILL_SWITCH", "false")
    runner = RecordingWriteRunner([])
    r = resource()
    connector = LinuxConnector(r, "localhost", "nexus", "key", write_runner=runner)
    result = await connector.execute_write(r, WriteAction(
        action_type="restart_service", parameters={"service": "nginx"}
    ))
    assert result.success is True
    assert runner.calls == [("restart_service", {"service": "nginx"})]


def test_non_lab_write_capability_is_disabled(monkeypatch):
    monkeypatch.setenv("REMEDIATION_WRITES_ENABLED", "true")
    connector = LinuxConnector(resource("production"), "localhost", "nexus", "key")
    assert connector.capabilities.write is False

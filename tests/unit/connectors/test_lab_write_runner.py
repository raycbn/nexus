from types import SimpleNamespace
from uuid import uuid4

import pytest
from packages.connectors.base.models import WriteAction
from packages.connectors.write_runner import LabWriteRunner
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


class FakeCommandRunner:
    def __init__(self):
        self.calls = []

    async def run_restart_service(self, service):
        self.calls.append(service)
        return SimpleNamespace(success=True, error=None, metadata={"service": service})


def resource(environment="lab"):
    return Resource(
        id=uuid4(),
        organization_id=uuid4(),
        name="lab-linux",
        resource_type=ResourceType.LINUX_SERVER,
        environment=environment,
    )


@pytest.mark.asyncio
async def test_lab_runner_is_structured_and_allowlisted():
    runner = FakeCommandRunner()
    result = await LabWriteRunner(runner).run(
        resource(), WriteAction(action_type="restart_service", parameters={"service": "nginx"})
    )
    assert result.success is True
    assert runner.calls == ["nginx"]


@pytest.mark.asyncio
async def test_lab_runner_rejects_non_lab():
    runner = FakeCommandRunner()
    result = await LabWriteRunner(runner).run(
        resource("production"),
        WriteAction(action_type="restart_service", parameters={"service": "nginx"}),
    )
    assert result.success is False
    assert runner.calls == []


@pytest.mark.asyncio
async def test_lab_runner_rejects_shell_syntax():
    runner = FakeCommandRunner()
    result = await LabWriteRunner(runner).run(
        resource(), WriteAction(action_type="restart_service", parameters={"service": "nginx;id"})
    )
    assert result.success is False
    assert runner.calls == []

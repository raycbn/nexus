from uuid import uuid4

import pytest
from packages.connectors.base.models import WriteAction
from packages.connectors.write_runner import ConnectedSSHCommandRunner, LabWriteRunner
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


class FakeTransport:
    def __init__(self, results=None):
        self.commands = []
        self.results = list(
            results or [{"success": True, "data": "", "error": None, "exit_code": 0}]
        )

    async def run(self, command, timeout):
        self.commands.append((command, timeout))
        return self.results.pop(0)


def lab_resource():
    return Resource(
        id=uuid4(),
        organization_id=uuid4(),
        name="lab",
        resource_type=ResourceType.LINUX_SERVER,
        environment="lab",
    )


@pytest.mark.asyncio
async def test_connected_transport_uses_structured_sudo_restart_command():
    transport = FakeTransport()
    result = await ConnectedSSHCommandRunner(transport.run).run_restart_service("nginx")
    assert result.success is True
    assert transport.commands == [("sudo systemctl restart -- nginx", 30.0)]


@pytest.mark.asyncio
async def test_connected_transport_falls_back_to_sudo_service_command():
    transport = FakeTransport(
        [
            {"success": False, "data": "", "error": "bus", "exit_code": 1},
            {"success": True, "data": "", "error": None, "exit_code": 0},
        ]
    )
    result = await ConnectedSSHCommandRunner(transport.run).run_restart_service("nginx")
    assert result.success is True
    assert result.metadata["transport"] == "sudo-service"


@pytest.mark.asyncio
async def test_connected_transport_falls_back_to_sudo_nginx_binary():
    transport = FakeTransport(
        [
            {"success": False, "data": "", "error": "bus", "exit_code": 1},
            {"success": False, "data": "", "error": "service", "exit_code": 1},
            {"success": True, "data": "", "error": None, "exit_code": 0},
        ]
    )
    result = await ConnectedSSHCommandRunner(transport.run).run_restart_service("nginx")
    assert result.success is True
    assert result.metadata["transport"] == "sudo-nginx-start"
    assert transport.commands[-1] == ("sudo nginx", 30.0)


@pytest.mark.asyncio
async def test_lab_runner_never_accepts_shell_syntax():
    transport = FakeTransport()
    result = await LabWriteRunner(ConnectedSSHCommandRunner(transport.run)).run(
        lab_resource(),
        WriteAction(action_type="restart_service", parameters={"service": "nginx;id"}),
    )
    assert result.success is False
    assert transport.commands == []

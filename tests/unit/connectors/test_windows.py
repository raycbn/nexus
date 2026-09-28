from uuid import uuid4

import pytest
from packages.connectors.providers.windows import WindowsConnector
from packages.domain.models.enums import ResourceType
from packages.domain.models.resource import Resource


class FakeResult:
    def __init__(self, stdout: str = "Windows Server|10.0", exit_status: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.exit_status = exit_status


class FakeConnection:
    async def run(self, command: str, **_: object) -> FakeResult:
        return FakeResult()

    def close(self) -> None:
        pass

    async def wait_closed(self) -> None:
        pass


@pytest.fixture
def resource() -> Resource:
    return Resource(
        id=uuid4(), organization_id=uuid4(), workspace_id=uuid4(),
        name="windows-lab", resource_type=ResourceType.WINDOWS_SERVER,
        environment="lab", labels={},
    )


@pytest.mark.asyncio
async def test_windows_password_auth_uses_password(
    monkeypatch: pytest.MonkeyPatch, resource: Resource
) -> None:
    captured: dict[str, object] = {}

    async def fake_connect(**kwargs: object) -> FakeConnection:
        captured.update(kwargs)
        return FakeConnection()

    monkeypatch.setattr("packages.connectors.providers.windows.asyncssh.connect", fake_connect)
    connector = WindowsConnector(resource, "localhost", "Administrator", "plain-secret")
    await connector.connect(resource)
    assert captured["password"] == "plain-secret"
    assert captured["client_keys"] is None


@pytest.mark.asyncio
async def test_windows_connector_is_read_only(resource: Resource) -> None:
    connector = WindowsConnector(resource, "localhost", "Administrator", "key")
    assert connector.capabilities.read is True
    assert connector.capabilities.discover is True
    assert connector.capabilities.write is False


@pytest.mark.asyncio
async def test_windows_discovery_returns_os_metadata(resource: Resource) -> None:
    connector = WindowsConnector(resource, "localhost", "Administrator", "key")
    connector._connection = FakeConnection()
    discovered = [item async for item in connector.discover(resource)]
    assert discovered[0].description == "Windows Server 10.0"


@pytest.mark.asyncio
async def test_windows_read_executes_through_powershell(resource: Resource) -> None:
    connector = WindowsConnector(resource, "localhost", "Administrator", "key")
    connector._connection = FakeConnection()
    result = await connector.execute_read(resource, "Get-Service")
    assert result.success is True
    assert result.data == "Windows Server|10.0"

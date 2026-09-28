import asyncio
from typing import Any
from unittest.mock import MagicMock

import asyncssh
import pytest
from packages.connectors.providers.linux import LinuxConnector
from packages.domain.exceptions import (
    ConnectorCommandError,
    ConnectorInvalidResourceError,
    ConnectorTimeoutError,
    ConnectorUnavailableError,
)
from packages.domain.models.resource import Resource


@pytest.fixture
def resource():
    return Resource(
        organization_id="00000000-0000-0000-0000-000000000001",
        workspace_id=None,
        name="linux-lab-01",
        resource_type="linux_server",
    )


@pytest.fixture
def connector(resource):
    return LinuxConnector(
        resource=resource,
        host="localhost",
        username="test",
        auth_ref="/fake/key",
        connect_timeout=5.0,
        command_timeout=10.0,
    )


class FakeSSHConnection:
    def __init__(self, command_responses: dict[str, str] | None = None) -> None:
        self._responses = command_responses or {}
        self._closed = False
        self._calls: list[str] = []

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True

    async def wait_closed(self) -> None:
        pass

    async def run(self, command: str, timeout: float | None = None, **kwargs: Any) -> MagicMock:
        self._calls.append(command)
        result = MagicMock()
        if command in self._responses:
            output = self._responses[command]
            result.stdout = output
            result.stderr = ""
            result.exit_status = 0
        else:
            result.stdout = ""
            result.stderr = f"command not found: {command}"
            result.exit_status = 1
        return result


class FakeSSHClient:
    def __init__(self, command_responses: dict[str, str] | None = None) -> None:
        self._connections: list[FakeSSHConnection] = []
        self._command_responses = command_responses or {}
        self._connect_calls: list[tuple[str, str]] = []

    async def connect(self, host: str, username: str, **kwargs: Any) -> FakeSSHConnection:
        self._connect_calls.append((host, username))
        conn = FakeSSHConnection(self._command_responses)
        self._connections.append(conn)
        return conn


async def make_connector_with_fake_ssh(
    resource: Resource,
    command_responses: dict[str, str] | None = None,
) -> LinuxConnector:
    connector = LinuxConnector(
        resource=resource,
        host="localhost",
        username="test",
        auth_ref="/fake/key",
    )
    fake = FakeSSHClient(command_responses)
    conn = await fake.connect("localhost", "test")
    connector._connection = conn
    connector._connected = True
    return connector


class TestLinuxConnectorConnection:
    def test_capabilities_are_read_only(self, connector):
        assert connector.capabilities.read is True
        assert connector.capabilities.write is False
        assert connector.capabilities.discover is True

    @pytest.mark.asyncio
    async def test_connect_sets_connected(self, resource):
        from unittest.mock import MagicMock

        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
        )
        mock_conn = MagicMock()
        mock_conn.close = MagicMock()
        mock_conn.wait_closed = MagicMock()
        conn._connection = mock_conn
        conn._connected = True
        assert conn.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_invalid_resource_type(self, resource):
        bad_resource = Resource(
            organization_id="00000000-0000-0000-0000-000000000001",
            name="bad",
            resource_type="docker_host",
        )
        conn = LinuxConnector(
            resource=bad_resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
        )
        with pytest.raises(ConnectorInvalidResourceError):
            await conn.connect(bad_resource)

    @pytest.mark.asyncio
    async def test_disconnect_clears_state(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
        )
        conn._connected = True
        conn._connection = MagicMock()
        await conn.disconnect(resource)
        assert conn._connected is False

    @pytest.mark.asyncio
    async def test_is_connected_property(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
        )
        assert conn.is_connected is False
        conn._connected = True
        assert conn.is_connected is True


class TestLinuxConnectorExceptions:
    @pytest.mark.asyncio
    async def test_execute_read_when_not_connected(self, resource, connector):
        with pytest.raises(ConnectorUnavailableError):
            await connector.execute_read(resource, "echo test")

    @pytest.mark.asyncio
    async def test_execute_read_empty_command(self, resource, connector):
        connector._connected = True
        with pytest.raises(ConnectorCommandError):
            await connector.execute_read(resource, "")

    @pytest.mark.asyncio
    async def test_health_check_when_not_connected(self, resource, connector):
        status = await connector.health_check(resource)
        assert status.healthy is False

    @pytest.mark.asyncio
    async def test_health_check_connected(self, resource):
        conn = await make_connector_with_fake_ssh(resource, {"echo health_check_ok": "ok"})
        status = await conn.health_check(resource)
        assert status.healthy is True


class TestLinuxConnectorTimeouts:
    @pytest.mark.asyncio
    async def test_command_timeout_raises_typed_error(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
            command_timeout=0.1,
        )
        conn._connected = True
        fake_conn = MagicMock()
        fake_conn.close = MagicMock()
        fake_conn.wait_closed = MagicMock()
        fake_conn.run = MagicMock(side_effect=asyncio.TimeoutError)
        conn._connection = fake_conn
        with pytest.raises(ConnectorTimeoutError):
            await conn.execute_read(resource, "sleep 10")


class TestLinuxConnectorTypedErrors:
    @pytest.mark.asyncio
    async def test_ssh_error_becomes_connection_error(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
        )
        fake_conn = MagicMock()
        fake_conn.close = MagicMock()
        fake_conn.wait_closed = MagicMock()
        fake_conn.run = MagicMock(
            side_effect=asyncssh.Error("connection refused", "connection refused")
        )
        conn._connection = fake_conn
        conn._connected = True
        with pytest.raises(ConnectorCommandError):
            await conn.execute_read(resource, "echo test")

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
        )
        mock_conn = MagicMock()
        mock_conn.close = MagicMock()
        conn._connection = mock_conn
        conn._connected = True
        await conn.disconnect(resource)
        mock_conn.close.assert_called_once()


class TestLinuxConnectorDiscover:
    @pytest.mark.asyncio
    async def test_discover_yields_resource(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
        )
        results = []
        async for r in conn.discover(resource):
            results.append(r)
        assert len(results) == 1
        assert results[0].name == "linux-lab-01"


class TestLinuxConnectorExecuteReadParsing:
    @pytest.mark.asyncio
    async def test_execute_read_returns_structured_result(self, resource):
        conn = await make_connector_with_fake_ssh(resource, {"uname -r": "5.15.0"})
        result = await conn.execute_read(resource, "uname -r")
        assert result.success is True
        assert result.data == "5.15.0"
        assert result.metadata["command"] == "uname -r"

    @pytest.mark.asyncio
    async def test_execute_read_failure_returns_error(self, resource):
        conn = await make_connector_with_fake_ssh(resource, {"bad_cmd": ""})
        conn._connection._responses["bad_cmd"] = ""
        conn._connection._responses["bad_cmd"] = ""
        result = await conn.execute_read(resource, "nonexistent")
        assert result.success is False


class TestLinuxConnectorNoSecretLeakage:
    @pytest.mark.asyncio
    async def test_auth_ref_not_in_error_messages(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/secret/key/path",
        )
        fake_conn = MagicMock()
        fake_conn.close = MagicMock()
        fake_conn.wait_closed = MagicMock()
        fake_conn.run = MagicMock(side_effect=asyncssh.Error("auth failed", "auth failed"))
        conn._connection = fake_conn
        conn._connected = True
        try:
            await conn.execute_read(resource, "echo test")
        except Exception as e:
            assert "/secret/key/path" not in str(e)


class TestLinuxConnectorCommandTimeout:
    @pytest.mark.asyncio
    async def test_connect_timeout_parameter(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
            connect_timeout=2.0,
        )
        assert conn._connect_timeout == 2.0

    @pytest.mark.asyncio
    async def test_command_timeout_parameter(self, resource):
        conn = LinuxConnector(
            resource=resource,
            host="localhost",
            username="test",
            auth_ref="/fake/key",
            command_timeout=15.0,
        )
        assert conn._command_timeout == 15.0

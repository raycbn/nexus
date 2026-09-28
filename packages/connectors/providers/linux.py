from typing import Any

import asyncssh

from packages.connectors.base import Connector
from packages.connectors.base.models import (
    ConnectorCapabilities,
    HealthStatus,
    ReadResult,
    WriteAction,
    WriteResult,
)
from packages.domain.exceptions import (
    ConnectorAuthenticationError,
    ConnectorCommandError,
    ConnectorConnectionError,
    ConnectorInvalidResourceError,
    ConnectorTimeoutError,
    ConnectorUnavailableError,
)
from packages.domain.models.resource import Resource


class LinuxConnector(Connector):
    DEFAULT_CONNECT_TIMEOUT: float = 10.0
    DEFAULT_COMMAND_TIMEOUT: float = 30.0

    def __init__(
        self,
        resource: Resource,
        host: str,
        username: str,
        auth_ref: str,
        port: int = 22,
        connect_timeout: float | None = None,
        command_timeout: float | None = None,
        key_passphrase: str | None = None,
        write_runner=None,
    ) -> None:
        self._resource = resource
        self._host = host
        self._port = port
        self._username = username
        self._auth_ref = auth_ref
        self._key_passphrase = key_passphrase
        self._connect_timeout = connect_timeout or self.DEFAULT_CONNECT_TIMEOUT
        self._command_timeout = command_timeout or self.DEFAULT_COMMAND_TIMEOUT
        self._connection: asyncssh.SSHClientConnection | None = None
        self._connected: bool = False
        from packages.connectors.write_runner import BlockedWriteRunner
        self._write_runner = write_runner or BlockedWriteRunner()

    @property
    def capabilities(self) -> ConnectorCapabilities:
        from packages.domain.config import NexusSettings

        settings = NexusSettings()
        write_enabled = settings.remediation_writes_enabled
        if settings.remediation_lab_only and self._resource.environment != "lab":
            write_enabled = False
        return ConnectorCapabilities(read=True, write=write_enabled, discover=True)

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, resource: Resource) -> None:
        if self._connected:
            return
        if resource.resource_type.value != "linux_server":
            raise ConnectorInvalidResourceError(
                f"Resource type not supported: {resource.resource_type}"
            )
        try:
            connect_kwargs: dict[str, Any] = {
                "host": self._host,
                "port": self._port,
                "username": self._username,
                "client_keys": [self._auth_ref],
                "connect_timeout": self._connect_timeout,
                "known_hosts": None,
            }
            if self._key_passphrase is not None:
                connect_kwargs["client_keys"] = [(self._auth_ref, self._key_passphrase)]
            self._connection = await asyncssh.connect(**connect_kwargs)
            self._connected = True
        except asyncssh.Error as e:
            if "authentication" in str(e).lower() or "auth" in str(e).lower():
                raise ConnectorAuthenticationError(str(e)) from e
            raise ConnectorConnectionError(str(e)) from e

    async def disconnect(self, resource: Resource) -> None:
        if self._connection is not None:
            self._connection.close()
            import contextlib

            with contextlib.suppress(Exception):
                await self._connection.wait_closed()
            self._connection = None
        self._connected = False

    async def health_check(self, resource: Resource) -> HealthStatus:
        if not self._connected:
            return HealthStatus(healthy=False, message="not connected")
        try:
            result = await self._run_command("echo health_check_ok", 5.0)
            if result["success"]:
                return HealthStatus(healthy=True, message="connected")
            return HealthStatus(healthy=False, message=result.get("error", "unknown"))
        except Exception as e:
            return HealthStatus(healthy=False, message=str(e))

    async def discover(self, resource: Resource) -> Any:
        yield resource

    async def execute_write(self, resource: Resource, action: WriteAction) -> WriteResult:
        from packages.domain.config import NexusSettings

        settings = NexusSettings()
        if not settings.remediation_writes_enabled:
            return WriteResult(success=False, error="Remediation writes are disabled")
        if settings.remediation_lab_only and resource.environment != "lab":
            return WriteResult(
                success=False, error="Real remediation is restricted to lab resources"
            )
        if action.action_type != "restart_service":
            return WriteResult(success=False, error="Unsupported write action")
        service = action.parameters.get("service", "")
        if not service or not service.replace("-", "").replace("_", "").isalnum():
            return WriteResult(success=False, error="Unsafe service name")
        return await self._write_runner.run(resource, action)

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if not self._connected:
            raise ConnectorUnavailableError("Connector is not connected")
        if not command:
            raise ConnectorCommandError("Empty command not allowed")
        result = await self._run_command(command, self._command_timeout)
        if result["success"]:
            return ReadResult(
                success=True,
                data=result["data"],
                metadata={"command": command, "exit_code": result["exit_code"]},
            )
        return ReadResult(
            success=False,
            error=result.get("error"),
            metadata={"command": command, "exit_code": result["exit_code"]},
        )

    async def _run_command(self, command: str, timeout: float) -> dict[str, Any]:
        if self._connection is None:
            raise ConnectorUnavailableError("No active connection")
        try:
            result = await self._connection.run(
                command,
                timeout=timeout,
                encoding="utf-8",
            )
            return {
                "success": result.exit_status == 0,
                "data": result.stdout,
                "error": result.stderr if result.exit_status != 0 else None,
                "exit_code": result.exit_status,
            }
        except TimeoutError as e:
            raise ConnectorTimeoutError(f"Command timed out after {timeout}s: {command}") from e
        except asyncssh.Error as e:
            raise ConnectorCommandError(str(e), command=command) from e

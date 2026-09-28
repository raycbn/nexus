from pathlib import Path
from typing import Any

import asyncssh

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import (
    ConnectorAuthenticationError,
    ConnectorCommandError,
    ConnectorConnectionError,
    ConnectorInvalidResourceError,
    ConnectorTimeoutError,
    ConnectorUnavailableError,
)
from packages.domain.models.resource import Resource


class WindowsConnector(Connector):
    """Read-only Windows Server connector using the native OpenSSH server."""

    def __init__(self, resource: Resource, host: str, username: str, auth_ref: str,
                 port: int = 22, connect_timeout: float = 10.0,
                 command_timeout: float = 30.0) -> None:
        self._resource = resource
        self._host = host
        self._port = port
        self._username = username
        self._auth_ref = auth_ref
        self._connect_timeout = connect_timeout
        self._command_timeout = command_timeout
        self._connection: asyncssh.SSHClientConnection | None = None

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        if resource.resource_type.value != "windows_server":
            raise ConnectorInvalidResourceError(
                f"Resource type not supported: {resource.resource_type}"
            )
        try:
            auth_kwargs = {
                "client_keys": [self._auth_ref]
                if Path(self._auth_ref).expanduser().is_file()
                else None,
                "password": self._auth_ref
                if not Path(self._auth_ref).expanduser().is_file()
                else None,
            }
            self._connection = await asyncssh.connect(
                host=self._host,
                port=self._port,
                username=self._username,
                connect_timeout=self._connect_timeout,
                known_hosts=None,
                **auth_kwargs,
            )
        except asyncssh.Error as exc:
            if "auth" in str(exc).lower():
                raise ConnectorAuthenticationError(str(exc)) from exc
            raise ConnectorConnectionError(str(exc)) from exc

    async def disconnect(self, resource: Resource) -> None:
        if self._connection is not None:
            self._connection.close()
            import contextlib
            with contextlib.suppress(Exception):
                await self._connection.wait_closed()
            self._connection = None

    async def health_check(self, resource: Resource) -> HealthStatus:
        if self._connection is None:
            return HealthStatus(healthy=False, message="not connected")
        try:
            result = await self._run_command("Write-Output NEXUS_HEALTH_OK", 5.0)
            message = "connected" if result["success"] else result["error"]
            return HealthStatus(healthy=result["success"], message=message)
        except Exception as exc:
            return HealthStatus(healthy=False, message=str(exc))

    async def discover(self, resource: Resource) -> Any:
        if self._connection is None:
            raise ConnectorUnavailableError("Connector is not connected")
        result = await self._run_command(
            "$o=Get-CimInstance Win32_OperatingSystem; "
            "Write-Output ($o.Caption + '|' + $o.Version)",
            self._command_timeout,
        )
        if not result["success"]:
            return
        parts = result["data"].strip().split("|", 1)
        description = f"{parts[0]} {parts[1]}" if len(parts) == 2 else result["data"].strip()
        yield resource.model_copy(update={"description": description})

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if self._connection is None:
            raise ConnectorUnavailableError("Connector is not connected")
        if not command:
            raise ConnectorCommandError("Empty command not allowed")
        result = await self._run_command(command, self._command_timeout)
        return ReadResult(
            success=result["success"],
            data=result["data"] if result["success"] else None,
            error=result["error"] if not result["success"] else None,
            metadata={"command": command, "exit_code": result["exit_code"]},
        )

    async def _run_command(self, command: str, timeout: float) -> dict[str, Any]:
        if self._connection is None:
            raise ConnectorUnavailableError("No active connection")
        try:
            result = await self._connection.run(
                f"powershell.exe -NoProfile -NonInteractive -Command \"{command}\"",
                timeout=timeout,
                encoding="utf-8",
            )
            return {
                "success": result.exit_status == 0,
                "data": result.stdout,
                "error": result.stderr if result.exit_status != 0 else None,
                "exit_code": result.exit_status,
            }
        except TimeoutError as exc:
            raise ConnectorTimeoutError(f"Command timed out after {timeout}s") from exc
        except asyncssh.Error as exc:
            raise ConnectorCommandError(str(exc), command=command) from exc

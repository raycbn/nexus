from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from packages.connectors.base.models import WriteAction, WriteResult
from packages.domain.models.resource import Resource


class WriteCommandRunner:
    async def run(self, resource: Resource, action: WriteAction) -> WriteResult: ...


@dataclass(frozen=True)
class BlockedWriteRunner:
    reason: str = "No real write runner is enabled"

    async def run(self, resource: Resource, action: WriteAction) -> WriteResult:
        return WriteResult(success=False, error=self.reason)


@dataclass
class RecordingWriteRunner:
    calls: list[tuple[str, dict[str, str]]]

    async def run(self, resource: Resource, action: WriteAction) -> WriteResult:
        self.calls.append((action.action_type, dict(action.parameters)))
        return WriteResult(success=True, data="simulated-write", metadata={"simulated": True})


class LabWriteRunner:
    """Lab-only structured runner; no free-form shell input."""

    def __init__(self, command_runner: Any):
        self._command_runner = command_runner

    async def run(self, resource: Resource, action: WriteAction) -> WriteResult:
        if resource.environment != "lab":
            return WriteResult(success=False, error="Lab resources only")
        if action.action_type != "restart_service":
            return WriteResult(success=False, error="Unsupported lab action")
        service = action.parameters.get("service", "")
        if not service or not service.replace("-", "").replace("_", "").isalnum():
            return WriteResult(success=False, error="Unsafe service name")
        return await self._command_runner.run_restart_service(service)


class ConnectedSSHCommandRunner:
    """Structured SSH transport used only behind LabWriteRunner."""

    def __init__(
        self, run_command: Callable[[str, float], Awaitable[dict[str, Any]]], timeout: float = 30.0
    ):
        self._run_command = run_command
        self._timeout = timeout

    async def run_restart_service(self, service: str) -> WriteResult:
        primary = await self._run_command(
            f"sudo systemctl restart -- {service}", self._timeout
        )
        if primary["success"]:
            return WriteResult(
                success=True,
                data=primary.get("data"),
                metadata={
                    "service": service,
                    "exit_code": primary.get("exit_code"),
                    "transport": "sudo-systemctl",
                },
            )
        fallback = await self._run_command(
            f"sudo service {service} restart", self._timeout
        )
        if fallback["success"]:
            return WriteResult(
                success=True,
                data=fallback.get("data"),
                metadata={
                    "service": service,
                    "exit_code": fallback.get("exit_code"),
                    "transport": "sudo-service",
                },
            )
        if service == "nginx":
            start = await self._run_command("sudo nginx", self._timeout)
            return WriteResult(
                success=start["success"],
                data=start.get("data"),
                error=start.get("error"),
                metadata={
                    "service": service,
                    "exit_code": start.get("exit_code"),
                    "transport": "sudo-nginx-start",
                },
            )
        return WriteResult(
            success=False,
            data=fallback.get("data"),
            error=fallback.get("error") or primary.get("error"),
            metadata={
                "service": service,
                "exit_code": fallback.get("exit_code"),
                "transport": "sudo-systemctl+sudo-service",
            },
        )

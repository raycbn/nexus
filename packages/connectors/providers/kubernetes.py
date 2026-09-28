import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import ConnectorCommandError, ConnectorConnectionError
from packages.domain.models.resource import Resource
from packages.secrets import EnvironmentSecretProvider


class KubernetesConnector(Connector):
    """Read-only Kubernetes connector backed by the local kubectl client."""

    def __init__(
        self,
        resource: Resource,
        server: str,
        kubeconfig_ref: str,
        context: str | None = None,
        command_timeout: float = 30.0,
    ) -> None:
        self._resource = resource
        self._server = server
        self._kubeconfig_ref = kubeconfig_ref
        self._context = context
        self._command_timeout = command_timeout
        self._secret_provider = EnvironmentSecretProvider()
        self._kubeconfig_path: str | None = None
        self._connected = False

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        kubeconfig = self._secret_provider.resolve(self._kubeconfig_ref)
        fd, path = tempfile.mkstemp(prefix="nexus-kubeconfig-", suffix=".yaml")
        os.close(fd)
        Path(path).write_text(kubeconfig, encoding="utf-8")
        self._kubeconfig_path = path
        result = await self._run(["cluster-info"])
        if result[0] != 0:
            await self.disconnect(resource)
            raise ConnectorConnectionError(result[2] or result[1])
        self._connected = True

    async def disconnect(self, resource: Resource) -> None:
        self._connected = False
        if self._kubeconfig_path:
            Path(self._kubeconfig_path).unlink(missing_ok=True)
            self._kubeconfig_path = None

    async def health_check(self, resource: Resource) -> HealthStatus:
        if not self._connected:
            return HealthStatus(healthy=False, message="not connected")
        code, stdout, stderr = await self._run(["get", "--raw=/version"])
        return HealthStatus(
            healthy=code == 0,
            message="connected" if code == 0 else stderr or stdout,
        )

    async def discover(self, resource: Resource) -> AsyncIterator[Resource]:
        code, stdout, stderr = await self._run(
            [
                "get", "nodes", "-o",
                ("jsonpath={range .items[*]}{.metadata.name}|"
                 "{.status.nodeInfo.kubeletVersion}{'\\n'}{end}"),
            ]
        )
        if code != 0:
            raise ConnectorCommandError(stderr or stdout, command="kubectl get nodes")
        for line in stdout.splitlines():
            if not line.strip():
                continue
            name, _, version = line.partition("|")
            yield resource.model_copy(
                update={
                    "id": uuid4(),
                    "parent_resource_id": resource.id,
                    "name": f"{resource.name}/{name}",
                    "description": f"Kubernetes node {version}",
                }
            )

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if not self._connected:
            raise ConnectorConnectionError("Connector is not connected")
        if not command.strip():
            raise ConnectorCommandError("Empty kubectl command not allowed")
        args = command.split()
        code, stdout, stderr = await self._run(args)
        return ReadResult(
            success=code == 0,
            data=stdout if code == 0 else None,
            error=stderr if code != 0 else None,
            metadata={"command": "kubectl " + command, "exit_code": code},
        )

    async def _run(self, args: list[str]) -> tuple[int, str, str]:
        if not self._kubeconfig_path:
            raise ConnectorConnectionError("No kubeconfig configured")
        command = ["kubectl", "--kubeconfig", self._kubeconfig_path]
        if self._context:
            command.extend(["--context", self._context])
        command.extend(args)
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._command_timeout
            )
            return process.returncode or 0, stdout.decode(), stderr.decode()
        except FileNotFoundError as exc:
            raise ConnectorCommandError("kubectl executable not found") from exc
        except TimeoutError as exc:
            process.kill()
            raise ConnectorCommandError("kubectl command timed out") from exc

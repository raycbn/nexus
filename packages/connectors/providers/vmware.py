import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import ConnectorAuthenticationError, ConnectorConnectionError
from packages.domain.models.resource import Resource


class VMwareConnector(Connector):
    """Read-only VMware/vCenter connector for health and VM discovery."""

    _OPERATION_TIMEOUT_SECONDS = 30.0

    def __init__(self, resource: Resource, host: str, username: str, password: str,
                 port: int = 443, verify_ssl: bool = False) -> None:
        self._resource = resource
        self._host, self._username, self._password = host, username, password
        self._port, self._verify_ssl = port, verify_ssl
        self._service_instance: Any = None

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        try:
            import ssl

            from pyVim.connect import SmartConnect
            ssl_context = None if self._verify_ssl else ssl._create_unverified_context()
            self._service_instance = await asyncio.wait_for(
                asyncio.to_thread(
                    SmartConnect,
                    host=self._host,
                    user=self._username,
                    pwd=self._password,
                    port=self._port,
                    sslContext=ssl_context,
                ),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("vCenter connection timed out") from exc
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            if any(
                marker in lowered
                for marker in ("password", "login", "not authenticated", "authentication failed")
            ):
                raise ConnectorAuthenticationError("vCenter authentication failed") from exc
            raise ConnectorConnectionError(message) from exc

    async def disconnect(self, resource: Resource) -> None:
        if self._service_instance is not None:
            from pyVim.connect import Disconnect
            await asyncio.to_thread(Disconnect, self._service_instance)
            self._service_instance = None

    async def health_check(self, resource: Resource) -> HealthStatus:
        if self._service_instance is None:
            return HealthStatus(healthy=False, message="not connected")
        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(self._service_instance.RetrieveContent),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("vCenter content retrieval timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        return HealthStatus(
            healthy=True,
            message="connected",
            details={"api_version": content.about.apiVersion, "full_name": content.about.fullName},
        )

    async def discover(self, resource: Resource) -> AsyncIterator[Resource]:
        if self._service_instance is None:
            raise ConnectorConnectionError("VMware connector is not connected")
        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(self._service_instance.RetrieveContent),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("vCenter content retrieval timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        try:
            view = await asyncio.wait_for(
                asyncio.to_thread(
                    content.viewManager.CreateContainerView,
                    content.rootFolder,
                    [self._vm_type()],
                    True,
                ),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("vCenter inventory view creation timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        try:
            for vm in view.view:
                yield resource.model_copy(update={
                    "id": uuid4(), "parent_resource_id": resource.id,
                    "name": f"{resource.name}/{vm.name}",
                    "description": f"VMware virtual machine ({vm.runtime.powerState})",
                    "labels": {**resource.labels, "vm_name": vm.name,
                               "power_state": str(vm.runtime.powerState),
                               "guest_os": str(vm.config.guestFullName or "")}})
        finally:
            await asyncio.to_thread(view.Destroy)

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if self._service_instance is None:
            raise ConnectorConnectionError("VMware connector is not connected")
        if command.strip() != "inventory":
            return ReadResult(
                success=False,
                error="Only the structured 'inventory' read is supported",
            )
        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(self._service_instance.RetrieveContent),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("vCenter content retrieval timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        try:
            view = await asyncio.wait_for(
                asyncio.to_thread(
                    content.viewManager.CreateContainerView,
                    content.rootFolder,
                    [self._vm_type()],
                    True,
                ),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("vCenter inventory view creation timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        try:
            return ReadResult(success=True, data=[
                {"name": vm.name, "power_state": str(vm.runtime.powerState)} for vm in view.view])
        finally:
            await asyncio.to_thread(view.Destroy)

    @staticmethod
    def _vm_type() -> type:
        from pyVmomi import vim
        return vim.VirtualMachine

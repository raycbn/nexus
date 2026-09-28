import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import ConnectorAuthenticationError, ConnectorConnectionError
from packages.domain.models.resource import Resource
from packages.secrets import EnvironmentSecretProvider


class AzureConnector(Connector):
    """Read-only Azure Resource Manager connector."""

    _OPERATION_TIMEOUT_SECONDS = 30.0

    def __init__(self, resource: Resource, subscription_id: str, credential_ref: str) -> None:
        self._resource = resource
        self._subscription_id = subscription_id
        self._credential_ref = credential_ref
        self._secret_provider = EnvironmentSecretProvider()
        self._client = None

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        try:
            from azure.identity import ClientSecretCredential
            from azure.mgmt.resource.resources import ResourceManagementClient

            payload = json.loads(self._secret_provider.resolve(self._credential_ref))
            credential = ClientSecretCredential(
                payload["tenant_id"], payload["client_id"], payload["client_secret"]
            )
            self._client = ResourceManagementClient(credential, self._subscription_id)
            await self.health_check(resource)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise ConnectorAuthenticationError("Invalid Azure credential payload") from exc
        except TimeoutError as exc:
            raise ConnectorConnectionError("Azure connection timed out") from exc
        except Exception as exc:
            if any(
                marker in str(exc).lower()
                for marker in ("credential", "unauthorized", "authentication")
            ):
                raise ConnectorAuthenticationError("Azure authentication failed") from exc
            raise ConnectorConnectionError(str(exc)) from exc

    async def disconnect(self, resource: Resource) -> None:
        self._client = None

    async def health_check(self, resource: Resource) -> HealthStatus:
        if self._client is None:
            return HealthStatus(healthy=False, message="not connected")
        try:
            await asyncio.wait_for(
                asyncio.to_thread(lambda: next(iter(self._client.resources.list(top=1)), None)),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
            return HealthStatus(
                healthy=True,
                message="connected",
                details={"subscription_id": self._subscription_id},
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("Azure health check timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc

    async def discover(self, resource: Resource) -> AsyncIterator[Resource]:
        if self._client is None:
            raise ConnectorConnectionError("Azure connector is not connected")
        try:
            items = await asyncio.wait_for(
                asyncio.to_thread(lambda: list(self._client.resources.list())),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("Azure discovery timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        for item in items:
            name = str(getattr(item, "name", "unknown"))
            resource_id = str(getattr(item, "id", ""))
            yield resource.model_copy(
                update={
                    "id": uuid4(),
                    "parent_resource_id": resource.id,
                    "name": f"{resource.name}/{name}",
                    "description": f"Azure resource ({getattr(item, 'type', '')})",
                    "labels": {
                        **resource.labels,
                        "resource_id": resource_id,
                        "resource_type": str(getattr(item, "type", "")),
                        "location": str(getattr(item, "location", "")),
                    },
                }
            )

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if self._client is None:
            raise ConnectorConnectionError("Azure connector is not connected")
        if command.strip() != "inventory":
            return ReadResult(
                success=False, error="Only the structured 'inventory' read is supported"
            )
        try:
            items = await asyncio.wait_for(
                asyncio.to_thread(lambda: list(self._client.resources.list())),
                timeout=self._OPERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise ConnectorConnectionError("Azure inventory read timed out") from exc
        except Exception as exc:
            raise ConnectorConnectionError(str(exc)) from exc
        return ReadResult(
            success=True,
            data=[
                {
                    "name": str(getattr(item, "name", "")),
                    "id": str(getattr(item, "id", "")),
                    "type": str(getattr(item, "type", "")),
                }
                for item in items
            ],
            metadata={"subscription_id": self._subscription_id},
        )
